#================================================
#FILE: services/signals_service/signal_reactivation_sync.py
#================================================
import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")

def _normalize_direction_from_row(row: dict) -> str:
    """
    Normaliza la dirección de una señal usando los campos disponibles.
    Prioridad:
      1) direction
      2) side
      3) direction_hint
      4) Si todo falla → 'long'
    """
    raw = (
        (row.get("direction") or "")
        or (row.get("side") or "")
        or (row.get("direction_hint") or "")
    ).lower()

    if "short" in raw:
        return "short"
    if "long" in raw:
        return "long"
    # fallback seguro
    return "long"

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


async def _evaluate_single_signal(app_layer, sig: dict) -> None:
    """
    Evalúa una sola señal pendiente de reactivación usando el motor técnico
    y marca en base de datos si debe reactivarse o no.
    """
    from services.coordinators.signal_coordinator import SignalCoordinator
    from database import mark_signal_reactivated

    signal_coord: SignalCoordinator = app_layer.signal_coordinator

    symbol = sig.get("symbol") or sig.get("pair") or "UNKNOWN"
    direction = _normalize_direction_from_row(sig)

    logger.info(f"♻️ Evaluando reactivación de {symbol} ({direction})")

    # pedimos al coordinador que haga el análisis de reactivación
    result = await signal_coord.evaluate_for_reactivation(sig, direction_hint=direction)

    decision_obj = getattr(result, "decision", {}) or {}
    decision = decision_obj.get("decision", "")
    primary_reason = decision_obj.get("primary_reason") or decision_obj.get("reason") or "N/A"

    if decision == "reactivate":
        # ✅ marcar en BD
        mark_signal_reactivated(sig["id"])

        # ✅ notificar por Telegram (si hay notifier configurado)
        notifier = getattr(app_layer, "notifier", None)
        if notifier is not None:
            try:
                await notifier.safe_send(
                    "♻️ Señal reactivada automáticamente:\n"
                    f"• Símbolo: {symbol}\n"
                    f"• Dirección: {direction}\n"
                    f"• Motivo: {primary_reason}"
                )
            except Exception:
                logger.exception(f"⚠️ No se pudo enviar notificación de reactivación para {symbol}")

        logger.info(f"✅ Señal {symbol} marcada como reactivada.")
    else:
        # No se reactiva, sólo se registra en logs
        logger.info(
            f"⏸ Señal {symbol} NO reactivada "
            f"(decisión={decision}, motivo={primary_reason})"
        )
