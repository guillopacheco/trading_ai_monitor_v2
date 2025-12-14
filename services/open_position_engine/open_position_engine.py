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

    async def evaluate_open_positions(self):
        """
        Evalúa posiciones abiertas en Bybit y decide acciones.
        Importante: NO debe reventar nunca.
        """
        positions_raw = get_open_positions()
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
            price_change_pct, roi_pct = self._calculate_roi(p)

            logger.info(
                f"🔎 {p['symbol']} {p['side']} "
                f"Δprice={price_change_pct:.2f}% "
                f"ROI={roi_pct:.2f}% "
                f"lev={p['leverage']}x"
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
