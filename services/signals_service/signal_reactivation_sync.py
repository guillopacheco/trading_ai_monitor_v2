#================================================
#FILE: services/signals_service/signal_reactivation_sync.py
#================================================
import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


# ============================================================
# 🔄 TAREA PRINCIPAL DE REACTIVACIÓN AUTOMÁTICA
# ============================================================
async def start_reactivation_monitor(app_layer, interval_seconds: int = 60):
    """
    Inicia un ciclo infinito que revisa señales pendientes cada X segundos.
    Usa exclusivamente:
        - app_layer.signal_service
        - app_layer.signal (SignalCoordinator)  # ← ¡CORRECCIÓN!
    """
    logger.info(f"♻️   Monitor de reactivación automática iniciado (intervalo={interval_seconds}s).")

    while True:
        try:
            await _process_pending_signals(app_layer)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}", exc_info=True)

        await asyncio.sleep(interval_seconds)


# ============================================================
# 🔎 PROCESA SEÑALES PENDIENTES
# ============================================================
async def _process_pending_signals(app_layer):
    signal_service = app_layer.signal_service
    signal_coord = app_layer.signal  # ← SignalCoordinator (TIENE auto_reactivate)

    # 1) Obtener señales pendientes desde SignalService
    pending = signal_service.get_pending_signals()

    logger.info(f"🔎 {len(pending)} señal(es) pendiente(s) para reactivación.")

    if not pending:
        return

    # 2) Usar el SignalCoordinator para procesar reactivaciones
    # ¡El SignalCoordinator YA TIENE la lógica de auto_reactivate!
    await signal_coord.auto_reactivate()


# ============================================================
# ⚙️ EVALÚA LA REACTIVACIÓN DE UNA SEÑAL (NO NECESARIO AHORA)
# ============================================================
# ¡ELIMINADO! Esta lógica ya está en SignalCoordinator._evaluate_reactivation()