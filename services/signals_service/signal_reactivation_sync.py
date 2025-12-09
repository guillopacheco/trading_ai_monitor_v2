# services/signals_service/signal_reactivation_sync.py

import logging
import asyncio

from services.application.signal_service import SignalService

logger = logging.getLogger("signal_reactivation_sync")

signal_service = SignalService()

POLL_INTERVAL = 60  # segundos


async def start_reactivation_monitor(app_layer):
    """
    Inicia el monitor de reactivación automática de señales.
    Corre en segundo plano sin bloquear el event loop.
    """
    logger.info(f"♻️ Monitor de reactivación automática iniciado (intervalo={POLL_INTERVAL}s).")
    asyncio.create_task(_reactivation_loop(app_layer))


async def _reactivation_loop(app_layer):
    """
    Loop infinito que revisa señales pendientes.
    """
    while True:
        try:
            await _process_pending_signals(app_layer)
        except Exception as e:
            logger.exception(f"❌ Error en reactivation loop: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def _process_pending_signals(app_layer):
    """
    Obtiene señales pendientes desde la base de datos y evalúa
    si deben reactivarse según el motor técnico.
    """

    pending = signal_service.get_pending_signals()

    if not pending:
        return

    for sig in pending:

        symbol = sig["symbol"]
        direction = sig["direction"]

        logger.info(f"♻️ Revisando señal pendiente: {symbol} ({direction}).")

        # Ejecuta el motor técnico con contexto "reactivation"
        analysis = await signal_service.evaluate_for_reactivation(symbol, direction)

        decision = analysis.get("decision")
        score = analysis.get("technical_score", 0)

        if decision == "reactivate":
            logger.info(f"✅ Señal {symbol} reactivada automáticamente (score={score}).")
            await signal_service.mark_signal_reactivated(symbol)

            # Notificar al usuario vía ApplicationLayer → Notifier
            if hasattr(app_layer, "notifier"):
                await app_layer.notifier.notify_signal_event(
                    f"♻️ **Reactivada señal en {symbol}** (score={score})"
                )

        elif decision == "skip":
            logger.info(f"⏳ Señal {symbol} permanece pendiente (decision=skip).")

        elif decision == "wait":
            logger.info(f"⏳ Señal {symbol} permanece PENDIENTE (wait).")

        else:
            logger.info(f"ℹ️ Señal {symbol} sin cambios.")
