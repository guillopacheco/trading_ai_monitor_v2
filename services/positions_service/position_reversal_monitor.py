"""
position_reversal_monitor.py — Monitor de reversiones peligrosas
-----------------------------------------------------------------------------

Detecta reversiones peligrosas en posiciones abiertas de Bybit.

Criterios modernos de reversión:
✔ Pérdida real SIN apalancamiento < -3%
✔ match_ratio bajo vs thresholds["internal"]
✔ smart_bias contrario a la dirección original
✔ divergencias en contra (RSI/MACD, vía trend_system_final)
✔ tendencia mayor en contra (major_trend)

IMPORTANTE:
- notifier.send_message es SINCRÓNICO → aquí usamos asyncio.to_thread.
-----------------------------------------------------------------------------
"""

import asyncio
import logging
from typing import Tuple

from services.technical_engine.motor_wrapper import analyze
from services.bybit_service.bybit_client import (
    get_open_positions,
    reverse_position,
    close_position,
    get_position_risk,
    get_last_price,
    place_market_order,
)

from services.telegram_service.notifier import send_message

from helpers import calculate_roi, calculate_loss_pct_from_roi

logger = logging.getLogger("position_reversal_monitor")

# ============================================================
# 🧮 Cambio porcentual sin apalancamiento
# ============================================================
def _price_change_percent(entry: float, mark: float, direction: str) -> float:
    """
    Calcula variación porcentual SIN apalancamiento, normalizada
    para long/short.

      - Para LONG:  (mark - entry) / entry * 100
      - Para SHORT: (entry - mark) / entry * 100
    """
    try:
        if entry <= 0:
            return 0.0

        change = ((mark - entry) / entry) * 100.0
        if direction.lower() == "short":
            change *= -1
        return change
    except Exception:
        return 0.0

# ============================================================
# 🚨 Lógica moderna de reversión
# ============================================================
def _is_reversal(direction: str, analysis: dict, loss_pct: float) -> Tuple[bool, str]:
    """
    Evalúa si una posición está en riesgo de reversión grave, combinando:

    ✔ Pérdida real SIN apalancamiento < -3%
    ✔ match_ratio < thresholds["internal"]
    ✔ smart_bias contrario
    ✔ divergencias peligrosas en contra (RSI/MACD)
    ✔ tendencia mayor en contra
    """
    thresholds = get_thresholds()
    internal_thr = thresholds.get("internal", 70.0)

    direction = (direction or "").lower()

    match_ratio = float(analysis.get("match_ratio", 0.0) or 0.0)
    major_trend = (analysis.get("major_trend") or "").lower()
    smart_bias = (analysis.get("smart_bias") or "").lower()
    divs = analysis.get("divergences", {}) or {}

    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    # 1) Pérdida significativa (sin apalancamiento)
    if loss_pct > -3.0:
        return False, "Pérdida pequeña, no aplica reversión."

    # 2) Tendencia mayor claramente en contra
    if direction == "long" and "bajista" in major_trend:
        return True, "Tendencia mayor bajista contra LONG."
    if direction == "short" and "alcista" in major_trend:
        return True, "Tendencia mayor alcista contra SHORT."

    # 3) Smart bias contrario
    if direction == "long" and "bear" in smart_bias:
        return True, "Smart bias bajista contra LONG."
    if direction == "short" and "bull" in smart_bias:
        return True, "Smart bias alcista contra SHORT."

    # 4) Divergencias peligrosas
    if direction == "long":
        if "bajista" in rsi or "bear" in rsi or "bajista" in macd or "bear" in macd:
            return True, "Divergencias bajistas en RSI/MACD contra LONG."
    elif direction == "short":
        if "alcista" in rsi or "bull" in rsi or "alcista" in macd or "bull" in macd:
            return True, "Divergencias alcistas en RSI/MACD contra SHORT."

    # 5) match_ratio muy bajo
    if match_ratio < internal_thr:
        return True, f"Match técnico muy bajo ({match_ratio:.1f}% < {internal_thr}%)."

    return False, "Condiciones aún estables."

# ============================================================
# 🚨 Monitor principal
# ============================================================
async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Detecta reversiones técnicas peligrosas en posiciones abiertas.

    ✔ Solo analiza posiciones con pérdida real > -3%
    ✔ Usa trend_system_final.analyze_trend_core()
    ✔ Notifica por Telegram cuando detecta riesgo alto
    """
    logger.info("🚨 Iniciando monitor de reversiones de posiciones...")

    while True:
        try:
            positions = get_open_positions()

            if not positions:
                logger.info("📭 No hay posiciones abiertas.")
                if run_once:
                    break
                await asyncio.sleep(interval_seconds)
                continue

            reviewed = 0
            alerts = 0

            for pos in positions:
                try:
                    symbol = (pos.get("symbol") or "").upper()
                    side = (pos.get("side") or "").lower()
                    direction = "long" if side == "buy" else "short"

                    entry = float(pos.get("entryPrice") or 0.0)
                    mark = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))

                    if entry <= 0:
                        continue

                    reviewed += 1

                    # Pérdida sin apalancamiento
                    loss_pct = _price_change_percent(entry, mark, direction)

                    if loss_pct > -3.0:
                        # Pérdida muy pequeña → se ignora
                        continue

                    logger.info(
                        f"🔎 {symbol} ({direction.upper()} x{lev}) | "
                        f"entry={entry:.6f} mark={mark:.6f} loss={loss_pct:.2f}%"
                    )

                    # Análisis técnico usando el motor único
                    analysis = analyze(
                        symbol=symbol,
                        direction_hint=direction,
                        context="reversal",
                        loss_pct=loss_pct,
                    )

                    decision = analysis.get("decision")
                    allowed = analysis.get("allowed", False)
                    reason = "; ".join(analysis.get("decision_reasons", []))

                    # Solo alertar si hay riesgo real de reversión
                    if decision != "reversal-risk" or not allowed:
                        continue

                    alerts += 1

                    divs = analysis.get("divergences", {}) or {}

                    msg_lines = [
                        f"🚨 *Reversión peligrosa detectada en {symbol}*",
                        f"🔹 Dirección: *{direction.upper()}* x{lev}",
                        f"💵 Pérdida sin apalancamiento: `{loss_pct:.2f}%`",
                        "",
                        f"🧭 Tendencia mayor: {analysis.get('major_trend')}",
                        f"📊 Match técnico: {analysis.get('match_ratio', 0):.1f}%",
                        f"🔮 Smart bias: {analysis.get('smart_bias')}",
                        "",
                        "🧪 *Divergencias:*",
                        f"• RSI: {divs.get('RSI', 'N/A')}",
                        f"• MACD: {divs.get('MACD', 'N/A')}",
                        "",
                        f"⚠️ *Razón técnica:* {reason}",
                        "",
                        "📌 Revisa esta operación inmediatamente.",
                    ]

                    msg = "\n".join(msg_lines)
                    await asyncio.to_thread(send_message, msg)

                except Exception as e:
                    logger.error(f"❌ Error en posición individual: {e}")

            logger.info(
                f"✔ Monitor: {reviewed} posiciones evaluadas — {alerts} alertas enviadas."
            )

        except Exception as e:
            logger.error(f"❌ Error general en monitor_reversals(): {e}")

        if run_once:
            break

        await asyncio.sleep(interval_seconds)

# ============================================================
# 🏁 Servicio oficial para main.py
# ============================================================

async def start_reversal_monitor(interval_seconds: int = 600):
    """
    Función oficial esperada por main.py.
    Ejecuta monitor_reversals() en loop infinito.
    """
    logger.info("🔄 Iniciando start_reversal_monitor()...")

    while True:
        try:
            await monitor_reversals(interval_seconds=interval_seconds, run_once=False)
        except Exception as e:
            logger.error(f"❌ Error en start_reversal_monitor: {e}")

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
