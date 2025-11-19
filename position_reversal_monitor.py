"""
position_reversal_monitor.py — versión final integrada con technical_brain
---------------------------------------------------------------------------
Detecta reversiones reales en posiciones abiertas usando:

    technical_brain.analyze_market()

Se analiza:
✔ Pérdida real sin apalancamiento (> -3%)
✔ Tendencias 5m, 15m, 1h
✔ Divergencias peligrosas
✔ Tendencia global del mercado
✔ Sesgo (smart bias)
✔ allowed=False → reversal crítica

Este módulo NO toca la base de datos.
--------------------------------------------------------------------------- 
"""

import asyncio
import logging

from bybit_client import get_open_positions
from technical_brain import analyze_market
from notifier import send_message

logger = logging.getLogger("position_reversal_monitor")


# ============================================================
# 🔢 Cambio porcentual sin apalancamiento
# ============================================================

def _calculate_price_change(entry: float, mark: float, direction: str) -> float:
    if entry <= 0:
        return 0.0

    change = ((mark - entry) / entry) * 100.0
    if direction == "short":
        change *= -1

    return change


# ============================================================
# 🚨 Monitor principal
# ============================================================

async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Detecta reversiones técnicas peligrosas en posiciones abiertas.

    ✔ Solo analiza posiciones con pérdida > -3%
    ✔ Usa technical_brain.analyze_market()
    ✔ allowed=False  → reversal crítica
    """

    logger.info("🚨 Iniciando monitor de reversiones de posiciones...")

    while True:
        try:
            positions = get_open_positions()

            if not positions:
                logger.info("📭 No hay posiciones abiertas para analizar.")
                if run_once:
                    break
                await asyncio.sleep(interval_seconds)
                continue

            reviewed = 0
            alerts = 0

            for pos in positions:
                try:
                    symbol = pos.get("symbol", "")
                    side = (pos.get("side") or "").lower()
                    direction = "long" if side == "buy" else "short"

                    entry = float(pos.get("entryPrice") or 0)
                    mark = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))

                    if not symbol or entry <= 0:
                        logger.warning(f"⚠️ Datos inválidos en posición: {pos}")
                        continue

                    reviewed += 1

                    # Cambio sin apalancamiento
                    change = _calculate_price_change(entry, mark, direction)

                    # Solo analizar pérdidas serias
                    if change > -3:
                        continue

                    logger.info(
                        f"🔎 {symbol} ({direction.upper()} x{lev}) "
                        f"entry={entry:.6f} mark={mark:.6f} "
                        f"change={change:.2f}%"
                    )

                    # ==========================================
                    # 🔍 Análisis técnico unificado
                    # ==========================================
                    analysis = analyze_market(symbol, direction_hint=direction)

                    # allowed=True → NO hay reversal crítica
                    if analysis.get("allowed", True):
                        continue

                    alerts += 1

                    # ==========================================
                    # 📡 Preparar mensaje final
                    # ==========================================
                    msg = [
                        f"🚨 *Reversión crítica detectada en {symbol}*",
                        f"🔹 Dirección original: *{direction.upper()}* x{lev}",
                        f"💰 Pérdida estimada: {change:.2f}% (sin apalancamiento)",
                        "",
                        "📊 *Tendencias:*",
                        f"• 5m: {analysis['trend_multi']['5m']}",
                        f"• 15m: {analysis['trend_multi']['15m']}",
                        f"• 1h: {analysis['trend_multi']['1h']}",
                        "",
                        "🧪 *Divergencias:*",
                        f"• RSI: {analysis['divergences']['RSI']}",
                        f"• MACD: {analysis['divergences']['MACD']}",
                        "",
                        f"🌡️ ATR: {analysis['atr']}",
                        f"🔎 Sesgo general: {analysis['overall_trend']} ({analysis['short_bias']})",
                        "",
                        f"🧠 *Recomendación:* {analysis['suggestion']}",
                        "",
                        "📌 Revisa la operación inmediatamente."
                    ]

                    await asyncio.to_thread(send_message, "\n".join(msg))

                except Exception as e:
                    logger.error(f"❌ Error procesando posición individual: {e}")

            logger.info(
                f"✅ Monitor: {reviewed} posiciones revisadas — {alerts} alertas enviadas."
            )

        except Exception as e:
            logger.error(f"❌ Error general en monitor_reversals(): {e}")

        if run_once:
            break

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
