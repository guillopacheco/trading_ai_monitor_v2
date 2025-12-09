import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_reactivation_monitor(app_layer, interval: int = 60):
    """
    Inicia el loop de reactivación automática.
    """
    logger.info(f"♻️   Monitor de reactivación automática iniciado (intervalo={interval}s).")

    while True:
        try:
            await _process_pending_signals(app_layer)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}", exc_info=True)

        await asyncio.sleep(interval)


async def _process_pending_signals(app_layer):
    """
    Procesa todas las señales pendientes desde SignalService.
    """
    signal_service = app_layer.signal_service
    signal_coord = app_layer.signal_coordinator

    # ❌ ERROR antes: pending = await signal_service.get_pending_signals()
    # ✔ CORRECTO:
    pending = signal_service.get_pending_signals()

    if not pending:
        return

    logger.info(f"🔎 {len(pending)} señal(es) pendiente(s) para reactivación.")

    for sig in pending:
        try:
            # Coordinator sí puede ser async
            result = await signal_coord.evaluate_for_reactivation(sig)
        except Exception as e:
            logger.error(f"❌ Error evaluando reactivación de {sig['symbol']}: {e}", exc_info=True)
            continue

        if result.reactivate:
            logger.info(f"🔁 Señal {sig['symbol']} REACTIVADA automáticamente.")
            signal_service.mark_as_reactivated(sig["id"])
        else:
            logger.info(f"⏳ Señal {sig['symbol']} permanece pendiente.")
