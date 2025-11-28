"""
signal_reactivation_sync.py
---------------------------
Módulo encargado del monitoreo periódico de señales pendientes
para detectar reactivaciones basadas en análisis técnico actualizado.

Versión 2025 — Integrada con:
• Motor técnico unificado
• Smart Entry 2.0
• Nuevo sistema de mensajes profesionales
• Manejo robusto de errores
"""

import asyncio
import logging
import motor_wrapper

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message

from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    update_signal_match_ratio,
    save_analysis_log,
)

logger = logging.getLogger("signal_reactivation_sync")


# ============================================================
# 🧠 REGLA DE REACTIVACIÓN
# ============================================================
def _can_reactivate(analysis: dict, direction: str):
    """
    Evalúa si una señal puede reactivarse según el motor técnico unificado.
    """

    allowed = analysis.get("allowed", False)
    decision = analysis.get("decision", "")
    match_ratio = float(analysis.get("match_ratio", 0.0) or 0.0)

    # Si el motor unificado explicitamente bloquea → NO reactivar
    if not allowed:
        return False, "Motor técnico marcó la señal como no viable (allowed=False)."

    # Umbrales desde motor_wrapper (reactivation = 50 en tu configuración)
    thresholds = motor_wrapper.get_thresholds()
    min_ratio = thresholds.get("reactivation", 50)

    if match_ratio < min_ratio:
        return False, f"Match insuficiente ({match_ratio:.1f}% < {min_ratio}%)."

    # Si el motor marcó decisión WAIT → no reactivar todavía
    if decision in ("wait", "skip"):
        return False, f"Condiciones aún mixtas ({decision})."

    # Si el motor marcó REVERSE → no reactivar
    if decision == "reversal-risk":
        return False, "Riesgo de reversión detectado."

    # Si llega aquí → REACTIVABLE
    return True, "Condiciones favorables para reactivación."


# ============================================================
# 📨 FORMATO LIMPIO DEL MENSAJE DE REACTIVACIÓN
# ============================================================
def _build_reactivation_message(signal: dict, report, reason: str):
    """
    Construye mensaje robusto, compatible con formatos:
    - report como string
    - report como lista
    - report como dict
    - report como None
    """

    if report is None:
        formatted = "Sin datos técnicos disponibles."
    elif isinstance(report, str):
        formatted = report
    elif isinstance(report, list):
        formatted = "\n".join(str(x) for x in report)
    elif isinstance(report, dict):
        formatted = "\n".join(f"{k}: {v}" for k, v in report.items())
    else:
        formatted = str(report)

    return (
        f"♻️ **Reactivación detectada**\n\n"
        f"🔸 **Par:** {signal['symbol']}\n"
        f"🔸 **Dirección:** {signal['direction']}\n"
        f"🔸 **Motivo:** {reason}\n\n"
        f"📊 **Análisis técnico actualizado:**\n{formatted}"
    )


# ============================================================
# 🔁 LOOP PRINCIPAL DE REACTIVACIÓN
# ============================================================
async def reactivation_loop():
    """
    Monitoreo periódico de reactivaciones cada N minutos.
    """
    logger.info("♻️ Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            logger.info("♻️ Ejecutando ciclo de reactivación…")
            await _process_pending_signals()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        logger.info(
            f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos."
        )
        await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)


# ============================================================
# 🔍 PROCESA TODAS LAS SEÑALES PENDIENTES
# ============================================================
async def _process_pending_signals():
    pending = get_pending_signals_for_reactivation()
    total = len(pending)
    logger.info(f"♻️ {total} señales pendientes encontradas para revisión.")

    reactivated = 0

    for sig in pending:
        signal_id = sig["id"]
        symbol = sig["symbol"]
        direction = sig["direction"]

        logger.info(f"♻️ Revisando señal pendiente: {symbol} ({direction}).")

        # 1) Análisis técnico actualizado
        try:
            analysis = motor_wrapper.analyze_for_reactivation(symbol, direction)
        except Exception as e:
            logger.error(f"❌ Error evaluando señal pendiente: {e}")
            continue

        # 2) Generar análisis formateado (mensaje profesional)
        try:
            report = motor_wrapper.analyze_and_format(symbol, direction)
        except Exception:
            report = None

        # 3) Guardar log técnico
        match_ratio = float(analysis.get("match_ratio", 0.0) or 0.0)

        try:
            save_analysis_log(
                signal_id=signal_id,
                match_ratio=match_ratio,
                recommendation=analysis.get("decision", ""),
                details=report,
            )
        except Exception as e:
            logger.error(f"⚠️ Error guardando log técnico: {e}")

        # 4) Actualizar match_ratio en tabla signals
        try:
            update_signal_match_ratio(signal_id, match_ratio)
        except Exception as e:
            logger.error(f"⚠️ Error actualizando match_ratio en DB: {e}")

        # 5) Evaluar reactivación
        allowed, reason = _can_reactivate(analysis, direction)

        if not allowed:
            logger.info(f"⏳ Señal {symbol} NO reactivada: {reason}")
            continue

        # 6) Marcar como reactivada
        try:
            mark_signal_reactivated(signal_id)
        except Exception as e:
            logger.error(f"⚠️ Error marcando señal como reactivada: {e}")

        reactivated += 1

        # 7) Notificar por Telegram
        msg = _build_reactivation_message(sig, report, reason)
        await asyncio.to_thread(send_message, msg)

    logger.info(f"♻️ Revisión completada — {total} señales revisadas, {reactivated} reactivadas.")
