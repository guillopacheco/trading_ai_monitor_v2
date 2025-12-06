"""
signal_reactivation_sync.py
Servicio de reactivación automática basado 100% en el motor técnico unificado.
"""

import asyncio
import logging

from services.technical_engine.motor_wrapper import analyze, analyze_and_format
from services.signals_service.signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    update_signal_match_ratio,
    save_analysis_log,
)
from services.telegram_service.notifier import send_message
from core.helpers import normalize_symbol
from config import SIGNAL_RECHECK_INTERVAL_MINUTES

logger = logging.getLogger("signal_reactivation_sync")


def _build_reactivation_message(signal, formatted, reason):
    return (
        f"♻️ **Reactivación detectada**\n\n"
        f"🔸 **Par:** {signal['symbol']}\n"
        f"🔸 **Dirección:** {signal['direction']}\n"
        f"🔸 **Motivo:** {reason}\n\n"
        f"📊 **Análisis técnico actualizado:**\n{formatted}"
    )


async def _process_pending_signals():
    pending = get_pending_signals_for_reactivation()
    logger.info(f"♻️ {len(pending)} señales pendientes encontradas para revisión.")
    reactivated = 0

    for sig in pending:
        symbol = sig["symbol"]
        direction = sig["direction"]
        signal_id = sig["id"]

        logger.info(f"♻️ Revisando señal pendiente: {symbol} ({direction}).")

        try:
            analysis = analyze(symbol=symbol, direction_hint=direction, context="reactivation")
        except Exception as e:
            logger.error(f"❌ Error analizando señal: {e}")
            continue

        match_ratio = float(analysis.get("match_ratio") or 0.0)
        decision = analysis.get("decision")
        allowed = analysis.get("allowed", False)

        # Guardar log en DB
        try:
            formatted_report = analyze_and_format(symbol, direction)
            save_analysis_log(
                signal_id=signal_id,
                match_ratio=match_ratio,
                recommendation=decision,
                details=formatted_report,
            )
        except Exception as e:
            logger.error(f"⚠️ Error guardando log técnico: {e}")

        # Actualizar match_ratio
        try:
            update_signal_match_ratio(signal_id, match_ratio)
        except Exception as e:
            logger.error(f"⚠️ Error actualizando match ratio: {e}")

        # 🔐 DECISIÓN FINAL DEL MOTOR ÚNICO
        if not allowed or decision != "reactivate":
            logger.info(
                f"⏳ Señal {symbol} NO reactivada "
                f"(decision={decision}, match={match_ratio}%)."
            )
            continue

        # Marcar como reactivada
        try:
            mark_signal_reactivated(signal_id)
        except Exception as e:
            logger.error(f"⚠️ Error marcando señal como reactivada: {e}")
            continue

        reactivated += 1
        logger.info(f"✅ Señal {symbol} REACTIVADA (match {match_ratio}%).")

        # Enviar notificación
        msg = _build_reactivation_message(
            sig,
            formatted_report,
            reason=f"Motor técnico autorizó reactivación (match={match_ratio}%).",
        )
        await asyncio.to_thread(send_message, msg)

    logger.info(
        f"♻️ Revisión completada — {len(pending)} señales revisadas, {reactivated} reactivadas."
    )

    return {"total": len(pending), "reactivated": reactivated}


async def reactivation_loop():
    logger.info("♻️ Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            await _process_pending_signals()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        logger.info(f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos.")
        await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)


async def start_reactivation_monitor():
    await reactivation_loop()


async def run_reactivation_cycle():
    logger.info("♻️ Ejecutando ciclo manual de reactivación…")
    return await _process_pending_signals()
