# ================================================================
# signal_reactivation_sync.py — VERSIÓN FINAL GPT 2025-12
# Reactivación estable, sin loops, sin romper arquitectura GPT.
# ================================================================

import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")

INTERVAL_SECONDS = 60  # cada 1 minuto (ajustable)


# ================================================================
#  EVALUAR UNA SOLA SEÑAL
# ================================================================
async def _evaluate_single_signal(app_layer, signal: dict):
    """
    Evalúa una señal pendiente y decide si reactivarla o no.
    Usa solamente:
      • app_layer.signal_service.get_pending_signals()
      • app_layer.analysis_service.analyze()
      • app_layer.signal_service.mark_signal_reactivated()
      • app_layer.signal_service.save_analysis_log()
      • app_layer.notifier.send_message()
    """

    try:
        signal_id = signal.get("id")
        symbol = signal.get("symbol")
        direction = signal.get("direction")

        logger.info(
            f"🔎 Evaluando reactivación | ID={signal_id} | {symbol} {direction}"
        )

        # -----------------------------------------------------------
        # 1) Ejecutar análisis técnico REAL
        # -----------------------------------------------------------
        analysis = await app_layer.analysis_service.analyze(symbol, direction)

        # Guardar log en DB
        app_layer.signal_service.save_analysis_log(
            signal_id,
            "reactivation",
            analysis
        )


        if not analysis or analysis.get("error"):
            logger.info(
                f"⚠️ No se pudo analizar {symbol} para reactivación (ID {signal_id})."
            )
            return

        # -----------------------------------------------------------
        # 2) Decisión de reactivación basada en motor técnico
        # -----------------------------------------------------------
        decision = analysis.get("decision", "unknown")
        allowed = False

        # Motores GPT/DeepSeek usan "allowed" en distintos lugares
        # Intentar detectar cualquiera
        entry_block = analysis.get("entry", {})
        decision_block = analysis.get("decision", {})

        if isinstance(decision_block, dict):
            allowed = decision_block.get("allowed", False)

        if not allowed and isinstance(entry_block, dict):
            allowed = entry_block.get("allowed", False)

        # -----------------------------------------------------------
        # 3) Si está permitido → reactivar
        # -----------------------------------------------------------
        if allowed:
            app_layer.signal_service.mark_signal_reactivated(signal_id)

            logger.info(
                f"✅ Señal REACTIVADA: {symbol} ({direction})\n"
                f"ID: {signal_id} | decisión: {decision}"
            )

            logger.info(f"✔ Señal {signal_id} reactivada correctamente.")
        else:
            logger.info(
                f"⏳ Señal pendiente (no viable aún): {symbol} {direction}\n"
                f"ID={signal_id} | decisión={decision}"
            )
            logger.info(f"↷ Señal {signal_id} sigue pendiente: decisión={decision}")

    except Exception as e:
        logger.error(f"❌ Error evaluando señal ID={signal.get('id')}: {e}", exc_info=True)
        logger.info(
            f"❌ Error interno en reactivación de señal ID={signal.get('id')}"
        )


# ================================================================
#  LOOP PRINCIPAL
# ================================================================
async def start_reactivation_monitor(app_layer):
    """
    Loop estable: cada INTERVAL_SECONDS revisa señales 'pending'.
    No usa coordinadores. No rompe arquitectura.
    """
    logger.info("🔁 Monitor de reactivación iniciado (GPT versión final).")

    while True:
        try:
            pending = app_layer.signal_service.get_pending_signals()

            if pending:
                logger.info(f"📌 {len(pending)} señal(es) pendiente(s) para evaluar.")

            for signal in pending:
                await _evaluate_single_signal(app_layer, signal)

        except Exception as e:
            logger.error(f"❌ Error en monitor de reactivación: {e}", exc_info=True)

        await asyncio.sleep(INTERVAL_SECONDS)
