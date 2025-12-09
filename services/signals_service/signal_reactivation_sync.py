# services/signals_service/signal_reactivation_sync.py

import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_reactivation_monitor(app_layer, interval_seconds: int = 60):
    """
    Monitor automático que intenta reactivar señales pendientes cada X segundos.
    """
    logger.info(f"♻️   Monitor de reactivación automática iniciado (intervalo={interval_seconds}s).")

    while True:
        try:
            await _process_pending_signals(app_layer)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}", exc_info=True)
        await asyncio.sleep(interval_seconds)


async def _process_pending_signals(app_layer):
    """
    Lógica de reactivación con acceso a SignalCoordinator.
    """
    signal_coord = app_layer.signal_coordinator  # ← NOMBRE CORRECTO

    pending = await signal_coord.get_pending_signals()
    if not pending:
        return

    for sig in pending:
        try:
            await signal_coord.try_reactivate_signal(sig)
        except Exception as e:
            logger.error(f"❌ Error reactivando señal {sig.id}: {e}")
