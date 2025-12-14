# services/open_position_engine/position_monitor.py
import asyncio
import logging

logger = logging.getLogger("position_monitor")


async def start_open_position_monitor(app_layer, interval_sec: int = 60):
    """
    Loop estable para revisar posiciones abiertas.
    """
    logger.info("📌 Monitor de posiciones abiertas iniciado")

    engine = app_layer.open_position_engine

    while True:
        try:
            await engine.evaluate_open_positions()
        except Exception as e:
            logger.exception(f"❌ Error en monitor de posiciones: {e}")
        await asyncio.sleep(interval_sec)
