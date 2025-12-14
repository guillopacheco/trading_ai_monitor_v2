# services/open_position_engine/position_monitor.py
import asyncio
import logging

logger = logging.getLogger("position_monitor")


async def start_open_position_monitor(app_layer, interval_sec: int = 120):
    logger.info("📌 Monitor de posiciones abiertas iniciado")

    while True:
        try:
            # si el engine tiene método, lo llama; si no, no rompe
            engine = getattr(app_layer, "open_position_engine", None)
            if engine and hasattr(engine, "evaluate_open_positions"):
                await engine.evaluate_open_positions()
            else:
                logger.warning(
                    "⚠️ open_position_engine.evaluate_open_positions() no existe aún."
                )
        except Exception as e:
            logger.exception(f"❌ Error en monitor de posiciones: {e}")

        await asyncio.sleep(interval_sec)
