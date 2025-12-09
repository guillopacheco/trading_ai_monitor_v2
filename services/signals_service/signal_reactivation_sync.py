# ============================================================
# signal_reactivation_sync.py — versión final (Opción B)
# Reactivación automática delegada al SignalCoordinator
# ============================================================

import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_reactivation_monitor(app_layer, interval: int = 60):
    """
    Lanza un proceso asíncrono que cada X segundos ejecuta:
    app_layer.signal_coord.auto_reactivate_all()
    """
    logger.info(f"♻️  Monitor de reactivación automática iniciado (intervalo={interval}s).")

    while True:
        try:
            await app_layer.signal_coord.auto_reactivate_all()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}", exc_info=True)

        await asyncio.sleep(interval)
