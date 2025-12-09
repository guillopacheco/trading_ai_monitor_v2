import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_reactivation_monitor(app_layer, interval: int = 60):
    """
    Inicia el loop de reactivación automática.
    app_layer: instancia de ApplicationLayer
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
    signal_service = app_layer.signal_service       # ✔ Fuente original de datos
    signal_coord = app_layer.signal_coordinator     # ✔ Para lógica avanzada

    # 1️⃣ obtener señales pendientes desde la BD (SignalService)
    pending = await signal_service.get_pending_signals()
    if not pending:
        return

    logger.info(f"♻️   Se encontraron {len(pending)} señales pendientes para evaluar...")

    # 2️⃣ Procesar cada señal
    for sig in pending:
        try:
            result = await signal_coord.evaluate_for_reactivation(sig)
        except Exception as e:
            logger.error(f"❌ Error al evaluar reactivación de {sig['symbol']}: {e}", exc_info=True)
            continue

        # 3️⃣ Si el coordinador decide reactivar…
        if result.reactivate:
            logger.info(f"🔁 Señal {sig['symbol']} reactivada automáticamente")
            await signal_service.mark_as_reactivated(sig["id"])

        # 4️⃣ Si decide mantener como pendiente…
        else:
            logger.info(f"⏳ Señal {sig['symbol']} permanece pendiente")
