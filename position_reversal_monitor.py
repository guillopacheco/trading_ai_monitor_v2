import asyncio
import logging
from datetime import datetime
from bybit_client import get_open_positions, get_ohlcv_data
from indicators import get_technical_data
from divergence_detector import detect_divergences
from notifier import send_message

logger = logging.getLogger("reversal_monitor")


async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Monitorea las posiciones abiertas (reales o simuladas) y detecta reversiones técnicas.
    - Usa divergencias RSI / MACD y cambio de tendencia.
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
                if entry == 0:
                    logger.warning(f"⚠️ Precio de entrada inválido para {symbol}: {entry}")
                    continue

                checked += 1
                price_change = ((mark_price - entry) / entry) * 100
                if direction == "short":
                    price_change *= -1

                # Analizar solo si hay pérdida relevante
                if price_change > -3:
                    continue

                # Obtener datos OHLCV
                df = get_ohlcv_data(symbol, "5", limit=200)
                if df is None or df.empty:
                    logger.warning(f"⚠️ Sin datos OHLCV para {symbol}")
                    continue

                # Detectar divergencias técnicas
                divs = detect_divergences(symbol, df)
                has_divergence = divs.get("rsi_divergence") or divs.get("macd_divergence")

                # Verificar cambio de tendencia
                tech = get_technical_data(symbol, intervals=["5m", "15m"])
                new_trend = None
                if tech:
                    short_trend = tech.get("5m", {}).get("trend", "").lower()
                    high_trend = tech.get("15m", {}).get("trend", "").lower()
                    if direction == "long" and ("bear" in short_trend or "bear" in high_trend):
                        new_trend = "bajista"
                    elif direction == "short" and ("bull" in short_trend or "bull" in high_trend):
                        new_trend = "alcista"

                # Enviar alerta si hay divergencia o cambio de tendencia
                if has_divergence or new_trend:
                    alerts += 1
                    msg = (
                        f"🚨 *Reversión detectada en {symbol}*\n"
                        f"🔹 Entrada original: {direction.upper()} (x{lev})\n"
                        f"🔹 Precio actual: {mark_price:.5f}\n"
                        f"🔹 Cambio estimado: {price_change:.2f}%\n"
                    )
                    if has_divergence:
                        active_divs = [k for k, v in divs.items() if v]
                        msg += f"🧭 Divergencia: {', '.join(active_divs)}\n"
                    if new_trend:
                        msg += f"📈 Nueva tendencia probable: {new_trend.upper()}\n"
                    msg += "📌 Recomendación: Cerrar posición o abrir en dirección opuesta."

                    await send_message(msg)

            logger.info(f"✅ Monitor de reversiones: {checked} posiciones revisadas, {alerts} alertas emitidas.")

        except Exception as e:
            logger.error(f"❌ Error en monitor_reversals(): {e}")

        if run_once:
            break
        await asyncio.sleep(interval_seconds)
