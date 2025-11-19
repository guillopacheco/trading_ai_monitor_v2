"""
position_reversal_monitor.py — versión final integrada con trend_system_final
-----------------------------------------------------------------------------
Detecta reversiones peligrosas en posiciones abiertas.

Criterios modernos de reversión:
✔ Pérdida real SIN apalancamiento < -3%
✔ match_ratio bajo (< threshold["internal"])
✔ smart_bias contrario a la dirección original
✔ divergencias en contra (RSI/MACD)
✔ tendencia mayor en contra (major_trend)
-------------------------------------------------------------------------------
"""

import asyncio
import logging

from bybit_client import get_open_positions
from helpers import calculate_price_change
from notifier import send_message
from trend_system_final import analyze_trend_core, _get_thresholds

logger = logging.getLogger("position_reversal_monitor")


# ============================================================
# 🧮 Cambio porcentual sin apalancamiento
# ============================================================

def _price_change_percent(entry: float, mark: float, direction: str) -> float:
    """
    Wrapper que usa helpers.calculate_price_change()
    evitando duplicación de lógica.
    """
    try:
        return calculate_price_change(entry_price=entry, current_price=mark, direction=direction)
    except Exception:
        # fallback si helpers no tiene exactamente la firma
        if entry <= 0:
            return 0.0

        change = ((mark - entry) / entry) * 100
        if direction == "short":
            change *= -1
        return change


# ============================================================
# 🚨 Lógica moderna de reversión
# ============================================================

def _is_reversal(direction: str, analysis: dict, loss_pct: float) -> tuple[bool, str]:
    """
    Evaluación de reversión basada en trend_system_final:

    ✔ match_ratio < internal_threshold
    ✔ smart_bias contrario
    ✔ divergencias contrarias
    ✔ loss_pct < -3%
    ✔ tendencia mayor en contra
    """

    thresholds = _get_thresholds()
    internal_thr = thresholds.get("internal", 55.0)

    direction = direction.lower()

    match_ratio = analysis.get("match_ratio", 0.0)
    major_trend = (analysis.get("major_trend") or "").lower()
    smart_bias = (analysis.get("smart_bias") or "").lower()
    divs = analysis.get("divergences", {})

    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    # 1) Pérdida significativa (sin apalancamiento)
    if loss_pct > -3:
        return False, "Pérdida pequeña, no aplica reversión."

    # 2) Tendencia mayor en contra
    if direction == "long" and "bear" in major_trend:
        return True, "Major trend bajista."

    if direction == "short" and "bull" in major_trend:
        return True, "Major trend alcista."

    # 3) Smart bias contrario
    if direction == "long" and "bear" in smart_bias:
        return True, "Smart bias bajista."

    if direction == "short" and "bull" in smart_bias:
        return True, "Smart bias alcista."

    # 4) Divergencias peligrosas
    if direction == "long":
        if "bear" in rsi or "bear" in macd:
            return True, "Divergencia bajista detectada."
    else:  # short
        if "bull" in rsi or "bull" in macd:
            return True, "Divergencia alcista detectada."

    # 5) match_ratio muy bajo
    if match_ratio < internal_thr:
        return True, f"Match_ratio muy bajo ({match_ratio:.1f} < {internal_thr})."

    return False, "Condiciones estables."


# ============================================================
# 🚨 Monitor principal
# ============================================================

async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Detecta reversiones técnicas peligrosas en posiciones abiertas.

    ✔ Solo analiza posiciones con pérdida real > -3%
    ✔ Usa trend_system_final.analyze_trend_core()
    ✔ Detecta divergencias, smart bias y tendencia global
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

                    entry = float(pos.get("entryPrice") or 0)
                    mark = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))

                    if entry <= 0:
                        continue

                    reviewed += 1

                    # ====================================================
                    # 📉 Cambio SIN apalancamiento (criterio moderno)
                    # ====================================================
                    loss_pct = _price_change_percent(entry, mark, direction)

                    if loss_pct > -3:
                        # pérdida muy pequeña → no revisar profundamente
                        continue

                    logger.info(
                        f"🔎 {symbol} ({direction.upper()} x{lev}) | "
                        f"entry={entry:.6f} mark={mark:.6f} loss={loss_pct:.2f}%"
                    )

                    # ====================================================
                    # 🔍 Análisis profundo vía trend_system_final
                    # ====================================================
                    analysis = analyze_trend_core(symbol, direction_hint=direction)

                    is_rev, reason = _is_reversal(direction, analysis, loss_pct)

                    if not is_rev:
                        continue

                    alerts += 1

                    # ====================================================
                    # 📨 Mensaje final
                    # ====================================================
                    msg = [
                        f"🚨 *Reversión peligrosa detectada en {symbol}*",
                        f"🔹 Dirección: *{direction.upper()}* x{lev}",
                        f"💵 Pérdida sin apalancamiento: `{loss_pct:.2f}%`",
                        "",
                        f"📊 Match técnico: {analysis.get('match_ratio', 0):.1f}%",
                        f"🧭 Tendencia mayor: {analysis.get('major_trend')}",
                        f"🔮 Smart bias: {analysis.get('smart_bias')}",
                        "",
                        "🧪 *Divergencias:*",
                        f"• RSI: {analysis.get('divergences', {}).get('RSI', 'N/A')}",
                        f"• MACD: {analysis.get('divergences', {}).get('MACD', 'N/A')}",
                        "",
                        f"⚠️ *Razón técnica:* {reason}",
                        "",
                        "📌 Revisa esta operación inmediatamente."
                    ]

                    await send_message("\n".join(msg))

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
# 🔧 Modo prueba
# ============================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
