import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_signal_reactivation_loop(app_layer, interval_sec=300):
    """
    Loop de reactivación:
    delega TODA la lógica al SignalCoordinator
    """

    logger.info("♻️ Monitor automático de reactivación iniciado")

    while True:
        try:
            # 🔁 delegación limpia
            await app_layer.signal.auto_reactivate()

        except Exception as e:
            logger.exception(f"❌ Error en loop de reactivación: {e}")

        await asyncio.sleep(interval_sec)
