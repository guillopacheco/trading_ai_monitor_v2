# services/open_position_engine/open_position_engine.py

import logging
from services.bybit_service.bybit_client import get_open_positions
from helpers import (
    calculate_price_change,
    calculate_roi,
    normalize_leverage,
)

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier, analysis_service):
        self.notifier = notifier
        self.analysis_service = analysis_service
        self.last_position_states = {}

    async def evaluate_open_positions(self):
        """
        Evalúa posiciones abiertas en Bybit y decide acciones.
        NO debe reventar nunca.
        """
        try:
            positions_raw = get_open_positions()
        except Exception as e:
            logger.exception(f"❌ Error obteniendo posiciones abiertas: {e}")
            return

        positions = []

        for raw in positions_raw:
            p = self._normalize_position(raw)
            if p:
                positions.append(p)

        logger.info(f"📌 Posiciones abiertas detectadas: {len(positions)}")

        if not positions:
            logger.info("📭 No hay posiciones abiertas.")
            return

        for p in positions:
            symbol = p["symbol"]

            price_change_pct, roi_pct = self._calculate_roi(p)
            action = self._decide_action(roi_pct)

            prev_action = self.last_position_states.get(symbol)

            # ⛔ Evitar repetir la misma alerta
            if prev_action == action:
                continue

            self.last_position_states[symbol] = action

            logger.info(
                f"🔎 {symbol} {p['side']} " f"ROI={roi_pct:.2f}% " f"action={action}"
            )

            if action == "warning":
                logger.warning(f"⚠️ WARNING {symbol} → ROI {roi_pct:.2f}%")

            elif action == "critical_evaluate":
                logger.error(
                    f"🔴 CRITICAL {symbol} → ROI {roi_pct:.2f}% "
                    f"(evaluar cierre/reversión)"
                )

            elif action == "force_close":
                logger.critical(
                    f"☠️ HARD STOP {symbol} → ROI {roi_pct:.2f}% "
                    f"(cierre obligatorio)"
                )

    def _normalize_position(self, raw: dict) -> dict | None:
        try:
            symbol = raw.get("symbol") or raw.get("symbolName")
            size = float(raw.get("size", 0))
            if not symbol or size == 0:
                return None

            side = raw.get("side")
            if not side:
                side = "long" if size > 0 else "short"

            entry_price = float(raw.get("entryPrice") or raw.get("avgPrice") or 0)
            mark_price = float(raw.get("markPrice") or raw.get("lastPrice") or 0)

            leverage = int(raw.get("leverage") or 20)  # default explícito

            unrealized_pnl = float(
                raw.get("unrealisedPnl") or raw.get("unrealizedPnl") or 0
            )

            return {
                "symbol": symbol,
                "side": side.lower(),
                "size": abs(size),
                "entry_price": entry_price,
                "mark_price": mark_price,
                "leverage": leverage,
                "unrealized_pnl": unrealized_pnl,
            }

        except Exception as e:
            logger.exception(f"❌ Error normalizando posición: {e}")
            return None

    def _calculate_roi(self, p: dict) -> tuple[float, float]:
        """
        Retorna:
        - price_change_pct (sin leverage)
        - roi_pct (con leverage)
        """
        entry = p["entry_price"]
        price = p["mark_price"]
        leverage = p["leverage"]
        side = p["side"]

        if entry <= 0 or price <= 0:
            return 0.0, 0.0

        if side == "long":
            price_change_pct = (price - entry) / entry
        else:  # short
            price_change_pct = (entry - price) / entry

        roi_pct = price_change_pct * leverage * 100

        return price_change_pct * 100, roi_pct

    def _decide_action(self, roi_pct: float) -> str:
        """
        Decide acción basada en ROI (con leverage).
        """
        if roi_pct <= -80:
            return "force_close"

        if roi_pct <= -50:
            return "critical_evaluate"

        if roi_pct <= -30:
            return "warning"

        return "ok"

    async def _run_technical_evaluation(self, position, roi_pct):
        symbol = position["symbol"]
        side = position["side"]  # long / short

        try:
            from services.technical_engine.technical_engine import analyze

            logger.info(f"🧠 B5 → Análisis técnico para {symbol} ({side})")

            result = analyze(symbol=symbol, direction=side, context="open_position")

        except Exception as e:
            logger.exception(f"❌ Error técnico analizando {symbol}: {e}")
            return

        decision = result.get("decision")
        grade = result.get("grade")
        confidence = result.get("confidence", 0)
        match = result.get("match_ratio", 0)

        # ===============================
        # 🎯 DECISIÓN FINAL (reglas duras)
        # ===============================

        if decision in ("skip", "block"):
            final_action = "close_recommended"

        elif decision == "allow" and confidence >= 0.6:
            final_action = "hold_recovery"

        elif decision == "reverse" and confidence >= 0.65:
            final_action = "reverse_recommended"

        else:
            final_action = "close_recommended"

        # ===============================
        # 📣 NOTIFICACIÓN
        # ===============================

        msg = (
            f"🔴 *B5 – Evaluación Crítica*\n"
            f"📌 {symbol} ({side.upper()})\n"
            f"📉 ROI: {roi_pct:.2f}%\n\n"
            f"🧠 Decisión técnica: *{decision}*\n"
            f"🎓 Grade: {grade}\n"
            f"📊 Match: {match}%\n"
            f"🎯 Confianza: {confidence:.2f}\n\n"
            f"📌 Acción sugerida: *{final_action.replace('_', ' ').upper()}*"
        )

        self.notifier.send(msg)

        logger.warning(f"📌 B5 {symbol}: {final_action}")
