from services.telegram_sender import safe_send
from core.signal_engine import analyze_open_position
from services.db_service import get_open_positions
import logging

logger = logging.getLogger("positions_controller")


async def check_positions():
    positions = get_open_positions()

    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for p in positions:
        logger.info(f"🔍 Analizando posición: {p['symbol']} ({p['side']})")
        result = await analyze_open_position(p)
        await safe_send(result)
