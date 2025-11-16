"""
position_reversal_monitor.py
------------------------------------------------------------
Monitor de reversiones técnicas en posiciones abiertas.

- Lee posiciones desde bybit_client.get_open_positions()
- Calcula cambio porcentual respecto al entry
- Solo analiza si hay pérdida relevante (por defecto < -3%)
- Obtiene datos técnicos multi–TF y divergencias
- Envía una alerta a Telegram si detecta:

    • Divergencia técnica (RSI / MACD / Volumen)
    • Cambio de tendencia contrario a la dirección original

Se integra con:
- main.py (tarea periódica)
- command_bot.py (/reversion → run_once=True)
------------------------------------------------------------
"""

import asyncio
import logging
from typing import Dict, Any

from bybit_client import get_open_positions, get_ohlcv_data
from indicators import get_technical_data
from divergence_detector import detect_divergences
from notifier import send_message

logger = logging.getLogger("position_reversal_monitor")


async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Monitorea las posiciones abiertas (reales o simuladas) y detecta reversiones técnicas.

    - Usa divergencias RSI / MACD / Volumen con detect_divergences(symbol, tech_multi)
    - Verifica cambio de tendencia en 5m y 15m
    - Envía alertas si detecta condiciones contrarias o pérdidas notables.
    - Si run_once=True, ejecuta solo una pasada (modo manual desde /reversion).
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

            checked, alerts = 0, 0

            for pos in positions:
                symbol = pos.get("symbol")
                side = pos.get("side", "Buy")
                direction = "long" if side.lower() == "buy" else "short"
                entry = float(pos.get("entryPrice", 0) or 0)
                lev = int(float(pos.get("leverage", 20)))
                mark_price = float(pos.get("markPrice", entry))

                if not symbol or entry <= 0:
                    logger.warning(f"⚠️ Datos inválidos para posición: {pos}")
                    continue

                checked += 1

                # Cambio porcentual respecto al entry (sin apalancamiento)
                price_change = ((mark_price - entry) / entry) * 100.0
                if direction == "short":
                    price_change *= -1

                # Analizar solo si hay pérdida relevante (> -3%)
                if price_change > -3:
                    continue

                logger.info(
                    f"🔎 Revisando {symbol} ({direction.upper()} x{lev}) "
                    f"entry={entry:.6f}, mark={mark_price:.6f}, change={price_change:.2f}%"
                )

                # Obtener datos técnicos multi-TF
                tech_multi = get_technical_data(symbol, intervals=["5m", "15m"])
                if not tech_multi:
                    logger.warning(f"⚠️ Sin datos técnicos para {symbol}")
                    continue

                # Divergencias técnicas (usa divergence_detector.detect_divergences)
                divs = detect_divergences(symbol, tech_multi)
                # divs esperado: {"RSI": "Ninguna" / "...", "MACD": "...", "Volumen": "..."}

                has_divergence = any(
                    v and v not in ["Ninguna", "None"] for v in divs.values()
                )

                # Verificar cambio de tendencia (usamos campo 'trend' que indicators.get_technical_data ya setea)
                short_trend = (tech_multi.get("5m", {}).get("trend", "") or "").lower()
                high_trend = (tech_multi.get("15m", {}).get("trend", "") or "").lower()

                new_trend = None
                if direction == "long" and ("bear" in short_trend or "bear" in high_trend):
                    new_trend = "bajista"
                elif direction == "short" and ("bull" in short_trend or "bull" in high_trend):
                    new_trend = "alcista"

                # Enviar alerta si hay divergencia o cambio de tendencia
                if has_divergence or new_trend:
                    alerts += 1

                    active_divs = ", ".join(
                        f"{k}: {v}"
                        for k, v in divs.items()
                        if v and v not in ["Ninguna", "None"]
                    ) or "Ninguna"

                    msg_lines = [
                        f"🚨 *Reversión detectada en {symbol}*",
                        f"🔹 Entrada original: {direction.upper()} (x{lev})",
                        f"🔹 Precio actual: {mark_price:.6f}",
                        f"🔹 Cambio estimado (sin apalancamiento): {price_change:.2f}%",
                        f"🧪 Divergencias: {active_divs}",
                    ]
                    if new_trend:
                        msg_lines.append(
                            f"📈 Nueva tendencia probable en marcos cortos: {new_trend.upper()}"
                        )

                    msg_lines.append(
                        "📌 Recomendación: Revisar posición; considerar cierre o apertura en dirección opuesta."
                    )

                    await send_message("\n".join(msg_lines))

            logger.info(
                f"✅ Monitor de reversiones: {checked} posiciones revisadas, {alerts} alertas emitidas."
            )

        except Exception as e:
            logger.error(f"❌ Error en monitor_reversals(): {e}")

        if run_once:
            break

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
