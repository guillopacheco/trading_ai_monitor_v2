"""
position_reversal_monitor.py — versión final integrada
------------------------------------------------------------
Monitor especializado en detección de reversiones peligrosas
en posiciones abiertas, apoyado completamente en:

    technical_brain.analyze_for_reversal()

Funciones:
✔ Lee posiciones desde bybit_client.get_open_positions()
✔ Evalúa cambio porcentual real (sin apalancamiento)
✔ Usa el motor técnico para determinar si hay reversión
✔ Envía alerta si detecta:
    • Divergencias peligrosas
    • Giro fuerte de tendencia contra la operación
    • Señal explícita del motor: allowed = False

Este módulo NO toca la base de datos.
------------------------------------------------------------
"""

import asyncio
import logging
from bybit_client import get_open_positions
from technical_brain import analyze_for_reversal
from notifier import send_message

logger = logging.getLogger("position_reversal_monitor")


# ============================================================
# 🔢 Cambio porcentual sin apalancamiento
# ============================================================

def _calculate_price_change(entry: float, mark: float, direction: str) -> float:
    """
    Devuelve el cambio porcentual SIN apalancamiento.
    """
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
    Revisa las posiciones abiertas para detectar reversiones técnicas peligrosas.

    Lógica:
    ✔ Solo analiza posiciones con pérdida mayor a -3% (sin apalancamiento)
    ✔ Llama a technical_brain.analyze_for_reversal()
    ✔ Si allowed=False → envía alerta de reversión
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
                    symbol = pos.get("symbol")
                    side = (pos.get("side") or "").lower()
                    direction = "long" if side == "buy" else "short"

                    entry = float(pos.get("entryPrice") or 0)
                    mark = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))
                    pnl = float(pos.get("unrealisedPnl") or 0)

                    if not symbol or entry <= 0:
                        logger.warning(f"⚠️ Datos inválidos en posición: {pos}")
                        continue

                    reviewed += 1

                    # Cambio sin apalancamiento
                    price_change = _calculate_price_change(entry, mark, direction)

                    # Solo investigar si hay pérdida relevante
                    if price_change > -3:
                        continue

                    logger.info(
                        f"🔎 Revisando {symbol} ({direction.upper()} x{lev}) | "
                        f"Entry={entry:.6f} Mark={mark:.6f} Change={price_change:.2f}%"
                    )

                    # ===============================
                    # 🔍 Análisis técnico completo
                    # ===============================
                    analysis = analyze_for_reversal(
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry,
                        mark_price=mark,
                        leverage=lev,
                        roi=0  # el motor no depende del ROI aquí
                    )

                    # Si allowed=True → no hay reversión crítica
                    if analysis["allowed"]:
                        continue

                    alerts += 1

                    # ===============================
                    # 📡 Preparar mensaje final
                    # ===============================
                    msg = [
                        f"🚨 *Reversión crítica detectada en {symbol}*",
                        f"🔹 Dirección original: *{direction.upper()}* x{lev}",
                        f"💰 Cambio aprox.: {price_change:.2f}%",
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
                        f"🔎 Sesgo corto: {analysis['short_bias']}",
                        "",
                        f"🧠 *Recomendación:* {analysis['suggestion']}",
                        "",
                        "📌 Se recomienda revisar la operación inmediatamente."
                    ]

                    await asyncio.to_thread(send_message, "\n".join(msg))

                except Exception as e:
                    logger.error(f"❌ Error procesando posición: {e}")

            logger.info(
                f"✅ Reversion monitor: {reviewed} revisadas — {alerts} alertas enviadas."
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
