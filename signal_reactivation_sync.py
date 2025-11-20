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
from datetime import datetime

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message
from trend_system_final import analyze_and_format, _get_thresholds
from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
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
    Evalúa si una señal puede reactivarse a partir del análisis técnico:

    Criterios:
    - result["allowed"] debe ser True
    - match_ratio >= thresholds["reactivation"]
    - major_trend / overall_trend coherente con la dirección
    - divergencias NO fuertemente en contra
    - smart_bias NO fuertemente contrario
    """
    thresholds = _get_thresholds()
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

    if match_ratio < re_thr:
        return False, f"Match insuficiente para reactivar ({match_ratio:.1f}% < {re_thr}%)."

    # Direccionalidad global
    if direction == "long":
        if "bear" in overall_trend or "bajista" in major_trend:
            return False, "Tendencia mayor bajista contra LONG."
    elif direction == "short":
        if "bull" in overall_trend or "alcista" in major_trend:
            return False, "Tendencia mayor alcista contra SHORT."

    # Divergencias fuertes en contra
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


def _build_reactivation_message(signal: dict, report: str, reason: str) -> str:
    symbol = signal.get("symbol", "N/A")
    direction = (signal.get("direction") or "").upper()
    lev = signal.get("leverage", 20)
    entry = signal.get("entry_price")

    lines = [
        f"♻️ *Reactivación de señal*: **{symbol}**",
        f"🎯 Dirección original: *{direction}* x{lev}",
        f"💵 Entry: `{entry}`",
        "",
        f"✅ *Motivo técnico:* {reason}",
        "",
        "🌀 *Análisis actual del mercado:*",
        report,
    ]
    return "\n".join(lines)


# ============================================================
# 🔁 Ciclo de reactivación (una pasada)
# ============================================================
async def run_reactivation_cycle() -> dict:
    """
    Ejecuta UNA pasada de reactivación:
    - Lee señales pendientes
    - Analiza cada una
    - Reactiva las que cumplan criterios
    """
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
        try:
            checked += 1
            symbol = sig.get("symbol")
            direction = sig.get("direction")

            logger.info(f"♻️ Revisando señal pendiente: {symbol} ({direction}).")

            result, report = analyze_and_format(symbol, direction_hint=direction)
            ok, reason = _can_reactivate(result, direction)

            if not ok:
                logger.info(f"⏳ Señal {symbol} NO reactivada: {reason}")
                continue

            # Marcar en DB
            sig_id = sig.get("id")
            if sig_id is not None:
                try:
                    mark_signal_reactivated(sig_id)
                except Exception as e:
                    logger.error(f"❌ Error marcando señal {sig_id} como reactivada: {e}")

            reactivated += 1

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
    """
    Bucle infinito que ejecuta run_reactivation_cycle()
    cada SIGNAL_RECHECK_INTERVAL_MINUTES.
    """
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


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_reactivation_cycle())
