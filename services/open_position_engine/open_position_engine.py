"""
OpenPositionEngine
------------------
Motor encargado de evaluar posiciones abiertas en Bybit.
Refactor estructural mínimo:
- NO cambia reglas de trading
- NO cambia lógica B
- SOLO ordena y estabiliza el archivo
"""

import time
import logging
from typing import Dict, Any, List

from services.bybit_service.bybit_client import get_open_positions

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier=None):
        self.notifier = notifier
        self.last_position_count = 0  # ← estado inicial seguro
        self.position_risk_state = {}

    def classify_risk(self, pnl: float) -> str:
        if pnl <= -0.50:
            return "CRITICAL"
        elif pnl <= -0.30:
            return "RISK"
        elif pnl <= -0.10:
            return "WATCH"
        else:
            return "SAFE"

    prev_risk = self.position_risk_state.get(symbol)

    if prev_risk != risk:
        if prev_risk is not None:
            logger.info(f"🔄 RISK CHANGE {symbol}: {prev_risk} → {risk}")
        self.position_risk_state[symbol] = risk

    # ==============================================================
    # 🚀 ENTRY POINT
    # ==============================================================
    async def evaluate_open_positions(self):
        try:
            positions = get_open_positions()  # o await, según tu wrapper

            self.last_position_count = len(positions)

            logger.info(
                f"📌 Posiciones abiertas detectadas: {self.last_position_count}"
            )

            if not positions:
                return

            for p in positions:
                symbol = p.get("symbol") or p.get("symbolName") or "UNKNOWN"
                size = p.get("size", 0)

                pnl = p.get("unrealisedPnl") or p.get("unrealizedPnl") or 0

                try:
                    pnl = float(pnl)
                except Exception:
                    pnl = 0.0

                risk = self.classify_risk(pnl)

                logger.info(f"📊 {symbol} | size={size} | pnl={pnl:.2f} | risk={risk}")

        except Exception as e:
            logger.exception("❌ Error evaluando posiciones abiertas")

    # ==============================================================
    # 🧩 NORMALIZACIÓN
    # ==============================================================
    def _normalize_position(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "symbol": raw.get("symbol") or raw.get("symbolName"),
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
    # 📊 CÁLCULO ROI (20x incluido)
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
    # 🔍 EJECUCIÓN DE ACCIÓN
    # ==============================================================
    async def _run_action(self, position: Dict[str, Any], roi_pct: float, action: str):
        symbol = position["symbol"]
        logger.info(f"🔎 {symbol} ROI={roi_pct}% action={action}")

        # Placeholder técnico (B5.x)
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
        key = f"{symbol}:{action}"
        self._alert_cooldown[key] = time.time()
