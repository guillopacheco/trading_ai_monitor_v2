# services/signals_service/signal_reactivation_sync.py

import asyncio
import logging

from application_layer import ApplicationLayer

logger = logging.getLogger("signal_reactivation_sync")


async def start_reactivation_monitor(app_layer: ApplicationLayer, interval: int = 60):
    """
    Monitor periódico que pide al SignalCoordinator que revise
    las señales pendientes de reactivación.

    Se llama desde main.py una sola vez, y se queda en bucle:
    cada `interval` segundos ejecuta:

        await app_layer.signal.auto_reactivate()
    """
    logger.info("♻️ Monitor de reactivación iniciado.")

    while True:
        try:
            if not hasattr(app_layer, "signal") or app_layer.signal is None:
                logger.error(
                    "❌ ApplicationLayer no tiene SignalCoordinator configurado."
                )
            else:
                await app_layer.signal.auto_reactivate()
        except Exception as e:
            logger.exception(f"❌ Error en monitor de reactivación: {e}")

        await asyncio.sleep(interval)
