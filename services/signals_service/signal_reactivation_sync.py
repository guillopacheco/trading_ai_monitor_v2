import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


# ============================================================
# 🔄 Monitor Automático de Reactivación de Señales
# ============================================================

async def start_reactivation_monitor(app_layer, interval_sec: int = 60):
    """
    Ciclo automático que revisa señales pendientes y evalúa si deben reactivarse.
    """
    logger.info(f"♻️   Monitor de reactivación automática iniciado (intervalo={interval_sec}s).")

    while True:
        try:
            await _process_pending_signals(app_layer)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}", exc_info=True)

        await asyncio.sleep(interval_sec)


# ============================================================
# 🔍 Revisión de señales pendientes
# ============================================================

async def _process_pending_signals(app_layer):
    signal_service = app_layer.signal_service

    pending = signal_service.get_pending_signals()
    total = len(pending)

    logger.info(f"🔎 {total} señal(es) pendiente(s) para reactivación.")

    if total == 0:
        return

    for sig in pending:
        try:
            await _evaluate_single_signal(app_layer, sig)
        except Exception as e:
            symbol = sig.get("symbol", "N/A")
            logger.error(f"❌ Error evaluando reactivación de {symbol}: {e}", exc_info=True)


# ============================================================
# 🧠 Evaluación individual de reactivación
# ============================================================

async def _evaluate_single_signal(app_layer, sig: dict):
    """
    Evalúa si una señal debe reactivarse usando análisis técnico.
    """

    signal_service = app_layer.signal_service
    analysis_coord = app_layer.analysis

    symbol = sig.get("symbol")

    # --------------------------------------------------------
    # 🔧 Compatibilidad con DB vieja y DB nueva
    # --------------------------------------------------------
    original_side = sig.get("side") or sig.get("direction")
    if not original_side:
        logger.error(f"❌ Señal sin campo side/direction: {sig}")
        return

    # --------------------------------------------------------
    # 📊 1. Analizar mercado en vivo
    # --------------------------------------------------------
    analysis = await analysis_coord.analyze_for_signal(symbol, original_side)

    # Score numérico del análisis técnico
    match_ratio = analysis.get("score", 0)

    # --------------------------------------------------------
    # 🗃 2. Guardar resultados del análisis
    # --------------------------------------------------------
    try:
        signal_service.save_analysis_log(
            signal_id=sig["id"],
            symbol=symbol,
            result=f"match_ratio={match_ratio}",
            raw_json=analysis
        )
    except Exception as e:
        logger.error(f"⚠️ Error al guardar log de análisis: {e}")

    # --------------------------------------------------------
    # 🎯 3. Decidir si se reactiva
    # --------------------------------------------------------
    THRESHOLD = 70  # Requisito mínimo

    if match_ratio >= THRESHOLD:
        signal_service.mark_reactivated(sig["id"])
        logger.info(f"🔔 Señal {symbol} REACTIVADA automáticamente (score={match_ratio}).")
        return

    logger.info(f"⚪ Señal {symbol} NO se reactiva (score={match_ratio} < {THRESHOLD}).")
