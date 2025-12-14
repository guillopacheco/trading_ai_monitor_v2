# services/signals_service/signal_reactivation_sync.py
import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_signal_reactivation_loop(app_layer, interval_sec=300):
    logger.info("♻️  Monitor automático de reactivación iniciado")

    while True:
        try:
            await app_layer.signal.auto_reactivate()
        except asyncio.CancelledError:
            logger.info("🛑 Loop reactivación cancelado")
            return
        except Exception as e:
            logger.exception(f"❌ Error en loop de reactivación: {e}")

        await asyncio.sleep(interval_sec)
