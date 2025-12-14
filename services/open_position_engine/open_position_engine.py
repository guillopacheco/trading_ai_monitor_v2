# services/open_position_engine/open_position_engine.py
import logging
from services.bybit_service.bybit_client import get_open_positions

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier, analysis_service):
        self.notifier = notifier
        self.analysis_service = analysis_service

    async def evaluate_open_positions(self):
        """
        Evalúa posiciones abiertas en Bybit y decide acciones (placeholder).
        Importante: NO debe reventar nunca.
        """
        positions = await get_open_positions()

        if not positions:
            logger.info("📭 No hay posiciones abiertas actualmente.")
            return

        logger.info(f"📌 Posiciones abiertas detectadas: {len(positions)}")

        # Aquí luego metes tu lógica (pérdida >=30/50%, reversión, etc.)
        # Por ahora solo loguea:
        for p in positions[:20]:
            sym = p.get("symbol") or p.get("symbolName") or "UNKNOWN"
            size = p.get("size")
            pnl = p.get("unrealisedPnl") or p.get("unrealizedPnl")
            logger.info(f"🔎 {sym} size={size} pnl={pnl}")
