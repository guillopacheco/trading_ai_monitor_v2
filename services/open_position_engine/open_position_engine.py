# services/open_position_engine/open_position_engine.py

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.bybit_service.bybit_client import get_open_positions

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    """
    Motor para monitorear posiciones abiertas y recomendar acciones.

    C4.x (base):
    - Seguimiento por ROI real (apalancamiento incluido).
    - Confirmación por motor técnico (analysis_service) para decidir cerrar / mantener / reversión controlada.

    B5.4.2:
    - Deduplicación por cooldown: no repetir alertas iguales en 5 min.
    - Además dedupe por "última acción" por símbolo.
    """

    # ============================
    # Config (umbral por ROI %)
    # ============================
    ROI_WARN = -30.0
    ROI_CRITICAL = -50.0
    ROI_FORCE_CLOSE = -80.0  # “hard stop”: NO sugerir reversión aquí

    COOLDOWN_SEC = 300  # 5 minutos

    def __init__(self, notifier=None, analysis_service=None, **kwargs):
        # kwargs extra para evitar que Kernel rompa si pasa args nuevos
        self.notifier = notifier
        self.analysis_service = analysis_service

        # dedupe
        self._last_action_by_symbol: Dict[str, str] = {}
        self._alert_cooldown: Dict[str, float] = {}

        # opcional: guardar último conteo si quieres /estado
        self.last_position_count: int = 0

        logger.info("✅ OpenPositionEngine inicializado.")

    # =========================================================
    # Loop principal (llamado por position_monitor)
    # =========================================================
    async def evaluate_open_positions(self) -> None:
        """
        Evalúa posiciones abiertas y emite recomendaciones.
        Importante: NO debe reventar nunca.
        """
        try:
            positions_raw = get_open_positions()  # tu bybit_client ya lo deja OK (sync)
        except Exception as e:
            logger.exception(f"❌ Error obteniendo posiciones abiertas: {e}")
            return

        if not positions_raw:
            self.last_position_count = 0
            logger.info("📭 No hay posiciones abiertas actualmente.")
            return

        normalized: List[Dict[str, Any]] = []
        for raw in positions_raw:
            p = self._normalize_position(raw)
            if p:
                normalized.append(p)

        self.last_position_count = len(normalized)
        logger.info(f"📌 Posiciones abiertas detectadas: {len(normalized)}")

        for p in normalized[:50]:
            try:
                symbol = p["symbol"]
                direction = p["direction"]  # "long" | "short"
                leverage = p["leverage"]

                price_change_pct, roi_pct = self._calc_price_and_roi(
                    entry=p["entry_price"],
                    mark=p["mark_price"],
                    direction=direction,
                    leverage=leverage,
                )

                # 1) Acción base por ROI
                base_action = self._decide_action_by_roi(roi_pct)

                # 2) Confirmación técnica (si aplica) para C4.3/C4.4
                tech = None
                if (
                    base_action in ("warning", "critical", "force_close")
                    and self.analysis_service
                ):
                    tech = await self._safe_analyze(symbol, direction)

                final_action, reason, risk = self._final_decision(
                    symbol=symbol,
                    direction=direction,
                    roi_pct=roi_pct,
                    price_change_pct=price_change_pct,
                    leverage=leverage,
                    base_action=base_action,
                    tech=tech,
                )

                logger.info(
                    f"📊 {symbol} | dir={direction} | price={price_change_pct:.2f}% | "
                    f"roi={roi_pct:.2f}% (x{leverage}) | risk={risk} | action={final_action}"
                )

                # 3) Deduplicación (por símbolo + acción) y por cooldown
                if not self._should_emit(symbol, final_action):
                    continue

                # 4) Notificar
                await self._safe_notify(
                    symbol=symbol,
                    direction=direction,
                    roi_pct=roi_pct,
                    price_change_pct=price_change_pct,
                    leverage=leverage,
                    risk=risk,
                    action=final_action,
                    reason=reason,
                    tech=tech,
                )

                self._register_emit(symbol, final_action)

            except Exception as e:
                logger.exception(f"❌ Error evaluando posición {p}: {e}")

    # =========================================================
    # Normalización
    # =========================================================
    def _normalize_position(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convierte payload Bybit a formato interno estable.
        """
        try:
            symbol = raw.get("symbol") or raw.get("symbolName")
            if not symbol:
                return None

            # size puede venir 0 para posiciones cerradas
            size = float(raw.get("size", 0) or 0)
            if size == 0:
                return None

            side = (raw.get("side") or raw.get("positionSide") or "").lower()
            # bybit suele usar "Buy"/"Sell" en algunos endpoints
            if side in ("buy", "long"):
                direction = "long"
            elif side in ("sell", "short"):
                direction = "short"
            else:
                # fallback por signo si llega raro
                direction = "long" if size > 0 else "short"

            entry_price = float(raw.get("entryPrice") or raw.get("avgPrice") or 0)
            mark_price = float(raw.get("markPrice") or raw.get("lastPrice") or 0)
            if entry_price <= 0 or mark_price <= 0:
                return None

            lev = raw.get("leverage")
            leverage = self._normalize_leverage(lev)

            unrealized_pnl = raw.get("unrealisedPnl") or raw.get("unrealizedPnl") or 0
            try:
                unrealized_pnl = float(unrealized_pnl)
            except Exception:
                unrealized_pnl = 0.0

            return {
                "symbol": symbol,
                "direction": direction,
                "side_raw": side,
                "size": abs(size),
                "entry_price": entry_price,
                "mark_price": mark_price,
                "leverage": leverage,
                "unrealized_pnl": unrealized_pnl,
            }
        except Exception as e:
            logger.exception(f"❌ Error normalizando posición: {e}")
            return None

    def _normalize_leverage(self, lev: Any) -> float:
        """
        Fallback explícito x20 si no viene.
        """
        try:
            v = float(lev)
            if v <= 0:
                return 20.0
            # clamp suave por seguridad
            if v > 125:
                return 125.0
            return v
        except Exception:
            return 20.0

    # =========================================================
    # ROI / Price change (x20)
    # =========================================================
    def _calc_price_and_roi(
        self, entry: float, mark: float, direction: str, leverage: float
    ) -> Tuple[float, float]:
        """
        price_change_pct: sin apalancamiento
        roi_pct: con apalancamiento (ROI aproximado por variación * leverage)
        """
        price_change = (mark - entry) / entry  # ej: -0.05 => -5%
        if direction == "short":
            price_change *= -1

        price_change_pct = price_change * 100.0
        roi_pct = price_change * leverage * 100.0
        return price_change_pct, roi_pct

    # =========================================================
    # Reglas base por ROI
    # =========================================================
    def _decide_action_by_roi(self, roi_pct: float) -> str:
        if roi_pct <= self.ROI_FORCE_CLOSE:
            return "force_close"
        if roi_pct <= self.ROI_CRITICAL:
            return "critical"
        if roi_pct <= self.ROI_WARN:
            return "warning"
        return "hold"

    def _risk_label(self, roi_pct: float) -> str:
        if roi_pct <= self.ROI_FORCE_CLOSE:
            return "FORCE_CLOSE"
        if roi_pct <= self.ROI_CRITICAL:
            return "CRITICAL"
        if roi_pct <= self.ROI_WARN:
            return "WARNING"
        return "SAFE"

    # =========================================================
    # Análisis técnico seguro
    # =========================================================
    async def _safe_analyze(
        self, symbol: str, direction: str
    ) -> Optional[Dict[str, Any]]:
        """
        analysis_service.analyze_symbol(...) tolerante a firmas distintas.
        """
        try:
            fn = getattr(self.analysis_service, "analyze_symbol", None)
            if not fn:
                return None

            # firma más común en tu app: analyze_symbol(symbol, direction, context=...)
            try:
                return await fn(symbol, direction, context="open_position")
            except TypeError:
                # firma alternativa: analyze_symbol(symbol=<>, direction=<>, context=<>)
                return await fn(
                    symbol=symbol, direction=direction, context="open_position"
                )
        except Exception as e:
            logger.warning(f"⚠️ Error análisis técnico {symbol}: {e}")
            return None

    # =========================================================
    # C4.3 + C4.4: decisión final
    # =========================================================
    def _final_decision(
        self,
        symbol: str,
        direction: str,
        roi_pct: float,
        price_change_pct: float,
        leverage: float,
        base_action: str,
        tech: Optional[Dict[str, Any]],
    ) -> Tuple[str, str, str]:
        """
        Devuelve (final_action, reason, risk_label).

        final_action:
        - hold
        - warn
        - close
        - reverse_controlled
        - force_close
        """
        risk = self._risk_label(roi_pct)

        # 0) Operación sana
        if base_action == "hold":
            return "hold", "Operación saludable.", risk

        # 1) Force close: no se discute (evita “reversión suicida”)
        if base_action == "force_close":
            return "force_close", "ROI extremo (≤ -80%) → cierre obligatorio.", risk

        # 2) Warning (-30 a -50): por defecto avisar; si TA dice “ya cambió fuerte en contra”, sugerir close
        if base_action == "warning":
            if self._tech_confirms_against_position(direction, tech, strong=True):
                return (
                    "close",
                    "C4.3: ROI en warning + indicadores confirman cambio fuerte en contra → cerrar.",
                    risk,
                )
            return "warn", "ROI en zona warning → vigilar / evaluar.", risk

        # 3) Critical (≤ -50): aquí entra C4.4 reversión controlada
        if base_action == "critical":
            # si TA confirma fuerte en contra -> reverse_controlled
            if self._tech_confirms_against_position(direction, tech, strong=True):
                return (
                    "reverse_controlled",
                    "C4.4: ROI crítico + tendencia confirmada contraria (EMA/RSI/MACD) → reversión controlada sugerida.",
                    risk,
                )

            # si TA no confirma (mixto / datos insuficientes) -> cerrar para cortar daño
            return (
                "close",
                "ROI crítico (≤ -50%) sin confirmación técnica sólida para revertir → cerrar recomendado.",
                risk,
            )

        # fallback
        return "warn", "Evaluación incompleta → alerta conservadora.", risk

    def _tech_confirms_against_position(
        self, direction: str, tech: Optional[Dict[str, Any]], strong: bool = True
    ) -> bool:
        """
        Detecta si el motor técnico está indicando tendencia contraria a la posición.

        Espera estructuras típicas de tu engine:
        - major_trend: {trend_code: bull/bear/sideways, trend_score: ...}
        - technical_score, match_ratio, grade, confidence
        - divergences, smart_entry...
        """
        if not tech or not isinstance(tech, dict):
            return False

        major = tech.get("major_trend") or {}
        trend_code = (major.get("trend_code") or "").lower()

        # cuál sería "tendencia contraria"
        # si estoy LONG y trend_code == bear => en contra
        # si estoy SHORT y trend_code == bull => en contra
        against = (direction == "long" and trend_code == "bear") or (
            direction == "short" and trend_code == "bull"
        )
        if not against:
            return False

        # fuerza mínima
        confidence = float(tech.get("confidence") or 0)
        technical_score = float(tech.get("technical_score") or 0)
        match_ratio = float(tech.get("match_ratio") or 0)
        grade = (tech.get("grade") or "").upper()

        if not strong:
            return confidence >= 0.55 or technical_score >= 60

        # “fuerte” para permitir reversión controlada:
        # - confianza decente
        # - score alto o match razonable
        # - grade aceptable
        grade_ok = grade in ("A", "B")
        return (
            (confidence >= 0.60)
            and grade_ok
            and (technical_score >= 65 or match_ratio >= 70)
        )

    # =========================================================
    # Dedupe / cooldown
    # =========================================================
    def _should_emit(self, symbol: str, action: str) -> bool:
        # no spamear la misma acción repetida por símbolo
        prev = self._last_action_by_symbol.get(symbol)
        if prev == action:
            return False

        # cooldown por símbolo+acción
        key = f"{symbol}:{action}"
        now = time.time()
        last = self._alert_cooldown.get(key)
        if last and (now - last) < self.COOLDOWN_SEC:
            return False

        return True

    def _register_emit(self, symbol: str, action: str) -> None:
        self._last_action_by_symbol[symbol] = action
        self._alert_cooldown[f"{symbol}:{action}"] = time.time()

    # =========================================================
    # Notifier tolerante
    # =========================================================
    async def _safe_notify(
        self,
        symbol: str,
        direction: str,
        roi_pct: float,
        price_change_pct: float,
        leverage: float,
        risk: str,
        action: str,
        reason: str,
        tech: Optional[Dict[str, Any]],
    ) -> None:
        if not self.notifier:
            return

        # mini-resumen técnico (si existe)
        tech_line = ""
        if isinstance(tech, dict):
            major = tech.get("major_trend") or {}
            tech_line = (
                f"\n🧠 TA: grade={tech.get('grade')} score={tech.get('technical_score')} "
                f"match={tech.get('match_ratio')} trend={major.get('trend_code')}"
            )

        msg = (
            f"📌 *Open Position Alert*\n"
            f"• Symbol: *{symbol}*\n"
            f"• Dir: *{direction.upper()}* | Lev: x{leverage}\n"
            f"• Price: {price_change_pct:.2f}% | ROI: *{roi_pct:.2f}%*\n"
            f"• Risk: *{risk}*\n"
            f"• Action: `{action}`\n"
            f"• Reason: {reason}"
            f"{tech_line}"
        )

        # soporta notifier.safe_send (async), send_message (async), send (sync)
        try:
            if hasattr(self.notifier, "safe_send"):
                await self.notifier.safe_send(msg)
                return
        except Exception:
            pass

        try:
            if hasattr(self.notifier, "send_message"):
                await self.notifier.send_message(msg)
                return
        except Exception:
            pass

        try:
            if hasattr(self.notifier, "send"):
                self.notifier.send(msg)
                return
        except Exception:
            pass


class ReactivationEngine:
    def __init__(self, analysis_service, signal_service, notifier):
        self.analysis_service = analysis_service
        self.signal_service = signal_service
        self.notifier = notifier
        self.cooldowns = {}

    async def evaluate_signal(self, signal):
        symbol = signal["symbol"]
        direction = signal["direction"]

        analysis = await self.analysis_service.analyze_symbol(
            symbol=symbol, direction=direction, context="reactivation"
        )

        if not analysis or analysis.get("error"):
            return "wait"

        if self._advanced_reactivation(analysis):
            return "reactivate"

        return "wait"


def _advanced_reactivation(self, analysis: dict) -> bool:
    direction = analysis["direction"]
    trend = analysis["major_trend"]["trend_code"]

    if direction == "short" and trend != "bear":
        return False

    ind = analysis.get("indicators", {})

    rsi_ok = ind["rsi"]["5m"]["value"] < 50 or ind["rsi"]["5m"]["slope"] == "down"

    macd_ok = (
        ind["macd"]["5m"]["histogram"] < 0 and ind["macd"]["5m"]["slope"] == "down"
    )

    ema_ok = (
        ind["ema"]["5m"]["ema10"] < ind["ema"]["5m"]["ema30"]
        and not ind["ema"]["5m"]["price_above_ema30"]
    )

    return rsi_ok and macd_ok and ema_ok
