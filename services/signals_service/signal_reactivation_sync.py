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
        - app_layer.analysis (AnalysisCoordinator)
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
    analysis_coord = app_layer.analysis     # ← AnalysisCoordinator

    # 1) Obtener señales pendientes desde SignalService
    pending = signal_service.get_pending_signals()

    logger.info(f"🔎 {len(pending)} señal(es) pendiente(s) para reactivación.")

    if not pending:
        return

    # 2) Iterar una por una
    for sig in pending:
        try:
            await _evaluate_single_signal(app_layer, sig)
        except Exception as e:
            logger.error(f"❌ Error evaluando reactivación de {sig.get('symbol', '?')}: {e}", exc_info=True)


# ============================================================
# ⚙️ EVALÚA LA REACTIVACIÓN DE UNA SEÑAL
# ============================================================
async def _evaluate_single_signal(app_layer, sig: dict):
    """
    Flujo:
    1) Analiza el mercado nuevamente
    2) Calcula match_ratio
    3) Si supera umbral → reactivar
    4) Registrar todo en base de datos
    """
    signal_service = app_layer.signal_service
    analysis_coord = app_layer.analysis

    symbol = sig["symbol"]
    original_side = sig["side"]

    # ---------------------------------------------------------
    # 1) Obtener un análisis completo usando AnalysisCoordinator
    # ---------------------------------------------------------
    analysis = await analysis_coord.analyze_for_signal(symbol, original_side)

    # analysis contiene:
    #   {
    #     "symbol": "BTCUSDT",
    #     "score": 82,
    #     "summary": "Tendencia general alineada...",
    #     "details": {...}
    #   }

    match_ratio = analysis.get("score", 0)

    # Registrar análisis en DB
    signal_service.save_analysis_log(
        signal_id=sig["id"],
        symbol=symbol,
        result=f"match_ratio={match_ratio}",
        raw_json=analysis
    )

    # ---------------------------------------------------------
    # 2) Verificar si se reactiva
    # ---------------------------------------------------------
    THRESHOLD = 70  # puede hacerse configurable

    if match_ratio >= THRESHOLD:
        # REACTIVAR
        signal_service.mark_reactivated(sig["id"])
        logger.info(f"🔔 Señal {symbol} reactivada automáticamente (score={match_ratio}).")
        return

    # Si NO se reactiva:
    logger.info(f"⚪ Señal {symbol} NO se reactiva (score={match_ratio} < {THRESHOLD}).")
