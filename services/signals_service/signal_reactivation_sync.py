# services/signals_service/signal_reactivation_sync.py
import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_signal_reactivation_loop(app_layer, interval_sec: int = 300):
    logger.info("♻️  Monitor automático de reactivación iniciado")
    while True:
        try:
            await app_layer.signal.auto_reactivate(limit=10)  # ✅ B2
        except Exception as e:
            logger.exception(f"❌ Error en loop de reactivación: {e}")
        await asyncio.sleep(interval_sec)
