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
            logger.info(
                f"🔎 {p['symbol']} "
                f"{p['side']} "
                f"size={p['size']} "
                f"pnl={p['unrealized_pnl']}"
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
