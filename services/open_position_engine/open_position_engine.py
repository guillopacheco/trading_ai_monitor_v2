"""
OpenPositionEngine
------------------
Motor encargado de evaluar posiciones abiertas en Bybit.

Refactor estructural mínimo:
- NO cambia reglas de trading
- NO cambia lógica B
- SOLO ordena, encapsula y estabiliza el archivo
"""

import time
import logging
from typing import Dict, Any

from services.bybit_service.bybit_client import get_open_positions

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier=None, analysis_service=None):
        self.notifier = notifier
        self.analysis_service = analysis_service

        # Estado interno
        self.last_position_count = 0
        self.position_risk_state: Dict[str, str] = {}
        self._alert_cooldown: Dict[str, float] = {}

    # ==============================================================
    # 🧠 CLASIFICACIÓN DE RIESGO (B4)
    # ==============================================================
    def classify_risk(self, pnl: float) -> str:
        if pnl <= -0.50:
            return "CRITICAL"
        elif pnl <= -0.30:
            return "RISK"
        elif pnl <= -0.10:
            return "WATCH"
        else:
            return "SAFE"

    # ==============================================================
    # 🚀 ENTRY POINT (NO DEBE REVENTAR NUNCA)
    # ==============================================================
    async def evaluate_open_positions(self):
        try:
            positions = get_open_positions()  # wrapper síncrono

            if not positions:
                logger.info("📭 No hay posiciones abiertas.")
                self.last_position_count = 0
                return

            self.last_position_count = len(positions)
            logger.info(
                f"📌 Posiciones abiertas detectadas: {self.last_position_count}"
            )

            for raw in positions:
                p = self._normalize_position(raw)
                symbol = p["symbol"]

                pnl = p["unrealized_pnl"]
                risk = self.classify_risk(pnl)

                prev_risk = self.position_risk_state.get(symbol)

                logger.info(
                    f"📊 {symbol} | size={p['size']} | pnl={pnl:.2f} | risk={risk}"
                )

                # Detectar cambio de riesgo
                if prev_risk != risk:
                    if prev_risk is not None:
                        logger.info(f"🔄 RISK CHANGE {symbol}: {prev_risk} → {risk}")
                    self.position_risk_state[symbol] = risk

                # Decisión B5
                roi = self._calculate_roi(p)
                action = self._decide_action(roi)

                if action and self._can_send_alert(symbol, action):
                    await self._run_action(p, roi, action)
                    self._register_alert(symbol, action)

        except Exception:
            logger.exception("❌ Error evaluando posiciones abiertas")

    # ==============================================================
    # 🧩 NORMALIZACIÓN
    # ==============================================================
    def _normalize_position(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "symbol": raw.get("symbol") or raw.get("symbolName") or "UNKNOWN",
            "side": (raw.get("side") or raw.get("positionSide") or "").lower(),
            "size": float(raw.get("size", 0)),
            "entry_price": float(raw.get("entryPrice", 0)),
            "mark_price": float(raw.get("markPrice", 0)),
            "unrealized_pnl": float(
                raw.get("unrealisedPnl") or raw.get("unrealizedPnl") or 0
            ),
            "leverage": float(raw.get("leverage") or 20),
        }

    # ==============================================================
    # 📊 ROI (20x incluido)
    # ==============================================================
    def _calculate_roi(self, p: Dict[str, Any]) -> float:
        if not p["entry_price"]:
            return 0.0

        price_change_pct = (
            (p["mark_price"] - p["entry_price"]) / p["entry_price"]
        ) * 100

        if p["side"] == "short":
            price_change_pct *= -1

        roi_pct = price_change_pct * p["leverage"]
        return round(roi_pct, 2)

    # ==============================================================
    # 🧠 DECISIÓN BASE (B5)
    # ==============================================================
    def _decide_action(self, roi_pct: float) -> str | None:
        if roi_pct <= -80:
            return "force_close"
        if roi_pct <= -50:
            return "critical"
        if roi_pct <= -30:
            return "warning"
        return None

    # ==============================================================
    # 🔍 EJECUCIÓN (placeholder técnico)
    # ==============================================================
    async def _run_action(self, position: Dict[str, Any], roi_pct: float, action: str):
        symbol = position["symbol"]
        logger.info(f"⚠️ {symbol} | ROI={roi_pct}% | action={action}")

        if self.analysis_service and action in ("warning", "critical"):
            try:
                await self.analysis_service.analyze_symbol(
                    symbol=symbol,
                    direction=position["side"],
                    context="open_position",
                )
            except Exception as e:
                logger.warning(f"⚠️ Error análisis técnico {symbol}: {e}")

        if self.notifier:
            try:
                self.notifier.send(f"⚠️ {symbol} | ROI {roi_pct}% | Acción: {action}")
            except Exception:
                pass

    # ==============================================================
    # ⏱️ COOLDOWN (B5.4.2)
    # ==============================================================
    def _can_send_alert(
        self, symbol: str, action: str, cooldown_sec: int = 300
    ) -> bool:
        key = f"{symbol}:{action}"
        now = time.time()
        last = self._alert_cooldown.get(key)
        if last and now - last < cooldown_sec:
            return False
        return True

    def _register_alert(self, symbol: str, action: str):
        self._alert_cooldown[f"{symbol}:{action}"] = time.time()
