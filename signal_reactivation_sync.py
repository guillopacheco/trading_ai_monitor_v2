"""
signal_reactivation_sync.py — Reactivación automática de señales
-----------------------------------------------------------------
Flujo:
1) Lee señales pendientes en DB (signal_manager_db).
2) Para cada señal, llama a trend_system_final.analyze_and_format().
3) Aplica lógica de reactivación según:
   - match_ratio vs thresholds["reactivation"]
   - major_trend / overall_trend
   - divergencias y smart_bias
4) Si todo cuadra → marca reactivada + envía reporte al usuario.

IMPORTANTE:
- notifier.send_message es SINCRÓNICO → aquí usamos asyncio.to_thread.
-----------------------------------------------------------------
"""
import asyncio
import logging
import motor_wrapper   # ✔ necesario
from datetime import datetime

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message

from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    update_signal_match_ratio,
    save_analysis_log,
)

logger = logging.getLogger("signal_reactivation_sync")


# Estado global para /estado
_reactivation_status = {
    "running": False,
    "last_run": "Nunca",
    "monitored_signals": 0,
    "reactivated_count": 0,
}


def get_reactivation_status() -> dict:
    return dict(_reactivation_status)


# ============================================================
# 🔍 Reglas de reactivación
# ============================================================
def _can_reactivate(result: dict, original_direction: str) -> tuple[bool, str]:
    """
    Aplica reglas de reactivación a partir del snapshot técnico.

    Criterios:
    - result["allowed"] debe ser True
    - match_ratio >= thresholds["reactivation"]
    - major_trend / overall_trend coherente con la dirección
    - divergencias NO fuertemente en contra
    - smart_bias NO fuertemente contrario
    """
    thresholds = motor_wrapper.get_thresholds()
    re_thr = thresholds.get("reactivation", 75.0)

    direction = (original_direction or "").lower()
    match_ratio = float(result.get("match_ratio", 0.0) or 0.0)
    allowed = bool(result.get("allowed", True))

    major_trend = (result.get("major_trend") or "").lower()
    overall_trend = (result.get("overall_trend") or "").lower()
    smart_bias = (result.get("smart_bias") or "").lower()
    divs = result.get("divergences", {}) or {}

    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    if not allowed:
        return False, "Motor técnico marcó la señal como no viable (allowed=False)."

    # Filtro por match_ratio
    if match_ratio < re_thr:
        return False, f"Match insuficiente para reactivar ({match_ratio:.1f}% < {re_thr}%)."

    # Direccionalidad global
    if direction == "long":
        if "bear" in overall_trend or "bajista" in major_trend:
            return False, "Tendencia mayor bajista contra LONG."
    elif direction == "short":
        if "bull" in overall_trend or "alcista" in major_trend:
            return False, "Tendencia mayor alcista contra SHORT."

    # Divergencias fuertes
    if direction == "long":
        if "bajista" in rsi or "bear" in rsi or "bajista" in macd or "bear" in macd:
            return False, "Divergencias bajistas en contra de LONG."
    elif direction == "short":
        if "alcista" in rsi or "bull" in rsi or "alcista" in macd or "bull" in macd:
            return False, "Divergencias alcistas en contra de SHORT."

    # Smart bias contrario
    if direction == "long" and "bear" in smart_bias:
        return False, "Smart bias bajista en contra de LONG."
    if direction == "short" and "bull" in smart_bias:
        return False, "Smart bias alcista en contra de SHORT."

    return True, "Condiciones favorables para reactivar."


# ============================================================
# 🧱 Construcción del mensaje enviado al usuario
# ============================================================
def _build_reactivation_message(signal, report, reason):
    """
    Construye mensaje limpio y robusto, aceptando report como:
    - string
    - lista
    - dict
    - None
    """

    # Normalización de report
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
        f"📊 **Análisis técnico:**\n{formatted}"
    )



# ============================================================
# 🔁 Ejecutar un ciclo de reactivación (una sola pasada)
# ============================================================
async def run_reactivation_cycle() -> dict:
    _reactivation_status["running"] = True
    _reactivation_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        signals = get_pending_signals_for_reactivation()
    except Exception as e:
        logger.error(f"❌ Error obteniendo señales pendientes: {e}")
        _reactivation_status["monitored_signals"] = 0
        return {"checked": 0, "reactivated": 0}

    if not signals:
        logger.info("ℹ️ No hay señales pendientes para revisar.")
        _reactivation_status["monitored_signals"] = 0
        return {"checked": 0, "reactivated": 0}

    checked = 0
    reactivated = 0

    for sig in signals:
        checked += 1
        try:
            symbol = sig.get("symbol")
            direction = sig.get("direction")
            signal_id = sig.get("id")

            logger.info(f"♻️ Revisando señal pendiente: {symbol} ({direction}).")

            # 1) Análisis técnico
            analysis = motor_wrapper.analyze_for_reactivation(symbol, direction)

            # Reporte formateado (texto limpio profesional)
            report = motor_wrapper.analyze_and_format(symbol, direction)

            # Valores técnicos
            match_ratio = float(analysis.get("match_ratio", 0.0) or 0.0)

            # Regla de reactivación
            allowed, reason = _can_reactivate(analysis, direction)

            # Guardar log técnico de este análisis
            try:
                save_analysis_log(
                    signal_id=signal_id,
                    match_ratio=match_ratio,
                    recommendation=reason,
                    details=report,
                )
            except Exception as e:
                logger.error(f"⚠️ Error guardando log de análisis: {e}")

            # Actualizar match_ratio en tabla signals
            try:
                update_signal_match_ratio(signal_id, match_ratio)
            except Exception as e:
                logger.error(f"⚠️ Error actualizando match_ratio en DB: {e}")

            if not allowed:
                logger.info(f"⏳ Señal {symbol} NO reactivada: {reason}")
                continue

            # 2) Marcar en DB
            try:
                mark_signal_reactivated(signal_id)
            except Exception as e:
                logger.error(f"⚠️ Error marcando señal como reactivada: {e}")

            reactivated += 1

            # 3) Notificar por Telegram
            msg = _build_reactivation_message(sig, report, reason)
            await asyncio.to_thread(send_message, msg)


        except Exception as e:
            logger.error(f"❌ Error evaluando señal pendiente: {e}")

    _reactivation_status["monitored_signals"] = checked
    _reactivation_status["reactivated_count"] += reactivated

    logger.info(
        f"♻️ Revisión completada — {checked} señales revisadas, "
        f"{reactivated} reactivadas en este ciclo."
    )

    return {"checked": checked, "reactivated": reactivated}


# ============================================================
# 🔁 Bucle automático
# ============================================================
async def auto_reactivation_loop():
    interval_min = int(SIGNAL_RECHECK_INTERVAL_MINUTES or 15)
    interval_sec = interval_min * 60

    logger.info("♻️ Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            logger.info("♻️ Ejecutando ciclo de reactivación…")
            await run_reactivation_cycle()
            logger.info(f"🕒 Próxima revisión en {interval_min} minutos.")
        except Exception as e:
            logger.error(f"❌ Error en auto_reactivation_loop: {e}")

        await asyncio.sleep(interval_sec)


async def start_reactivation_monitor():
    '''Punto de entrada público para main.py.
    Inicia el bucle automático de reactivaciones.'''
    await auto_reactivation_loop()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reactivation_cycle())
