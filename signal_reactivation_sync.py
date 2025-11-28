"""
signal_reactivation_sync.py
---------------------------
Servicio de reactivación automática de señales.

Flujo:
1) Lee señales pendientes en DB (signal_manager_db).
2) Para cada señal, llama al motor técnico unificado vía motor_wrapper.
3) Aplica lógica de reactivación según:
   - match_ratio vs thresholds["reactivation"]
   - decisión global del motor (enter / wait / skip / reversal-risk)
4) Si todo cuadra → marca reactivada + envía reporte al usuario.

Compatibilidad:
- start_reactivation_monitor() → usado por main.py
- run_reactivation_cycle()     → usado por command_bot (/reactivacion)
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

    # Si el motor unificado explícitamente bloquea → NO reactivar
    if not allowed:
        return False, "Motor técnico marcó la señal como no viable (allowed=False)."

    # Umbrales desde motor_wrapper (reactivation = 50 en tu configuración)
    thresholds = motor_wrapper.get_thresholds()
    min_ratio = thresholds.get("reactivation", 50)

    if match_ratio < min_ratio:
        return False, f"Match insuficiente ({match_ratio:.1f}% < {min_ratio}%)."

    # Si el motor marcó decisión WAIT / SKIP → aún no
    if decision in ("wait", "skip"):
        return False, f"Condiciones aún mixtas ({decision})."

    # Si el motor marcó reversión → ni tocar
    if decision == "reversal-risk":
        return False, "Riesgo de reversión detectado."

    # Si llega aquí → REACTIVABLE
    return True, "Condiciones favorables para reactivación."


# ============================================================
# 📨 FORMATO DEL MENSAJE DE REACTIVACIÓN
# ============================================================
def _build_reactivation_message(signal: dict, report, reason: str):
    """
    Construye mensaje robusto, aceptando report como:
    - string
    - lista
    - dict
    - None
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
# 🔍 PROCESA TODAS LAS SEÑALES PENDIENTES (UN SOLO CICLO)
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

        # 1) Análisis técnico actualizado (modo reactivación)
        try:
            analysis = motor_wrapper.analyze_for_reactivation(symbol, direction)
        except Exception as e:
            logger.error(f"❌ Error evaluando señal pendiente: {e}")
            continue

        # 2) Texto formateado profesional (mismo formato que análisis normal)
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

    logger.info(
        f"♻️ Revisión completada — {total} señales revisadas, {reactivated} reactivadas."
    )
    return {"total": total, "reactivated": reactivated}


# ============================================================
# 🔁 LOOP AUTOMÁTICO (USADO POR main.py)
# ============================================================
async def reactivation_loop():
    logger.info("♻️ Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            await _process_pending_signals()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        logger.info(
            f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos."
        )
        await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)


# ============================================================
# 🧷 API DE COMPATIBILIDAD
# ============================================================
async def start_reactivation_monitor():
    """
    Punto de entrada público para main.py.

    Antes:
        from signal_reactivation_sync import start_reactivation_monitor
        asyncio.create_task(start_reactivation_monitor())

    Ahora:
        main.py puede seguir llamando igual; esta función
        simplemente delega al loop oficial.
    """
    await reactivation_loop()


async def run_reactivation_cycle():
    """
    Punto de entrada para /reactivacion en command_bot.py.

    Antes:
        from signal_reactivation_sync import run_reactivation_cycle
        stats = await run_reactivation_cycle()

    Ahora:
        mantiene la misma firma, pero usa el nuevo motor.
    """
    logger.info("♻️ Ejecutando ciclo manual de reactivación…")
    stats = await _process_pending_signals()
    return stats


# ============================================================
# 🧪 Modo script (prueba manual)
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reactivation_cycle())
