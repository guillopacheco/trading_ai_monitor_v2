import asyncio
import logging
from datetime import datetime, timedelta
from database import get_signals
from bybit_client import get_ohlcv_data
from indicators import get_technical_data
from divergence_detector import detect_divergences
from notifier import send_message

logger = logging.getLogger("reversal_monitor")


async def monitor_reversals(poll_seconds: int = 600, interval_seconds: int = None):
    if interval_seconds is not None:
        poll_seconds = interval_seconds
    """Monitorea señales recientes y detecta posibles reversiones de tendencia."""
    logger.info("🚨 Iniciando monitor de reversiones de posiciones...")

    while True:
        try:
            recent_signals = get_signals(limit=30)
            now = datetime.utcnow()
            checked = 0
            reversals = 0

            for sig in recent_signals:
                ts = None
                try:
                    ts = datetime.fromisoformat(sig.get("timestamp", str(now)))
                except Exception:
                    ts = now
                if now - ts > timedelta(hours=24):
                    continue

                pair = sig.get("pair")
                direction = sig.get("direction", "").lower()
                entry = float(sig.get("entry", 0) or 0)
                lev = int(sig.get("leverage", 20) or 20)

                if not pair or entry == 0:
                    continue

                checked += 1
                df = get_ohlcv_data(pair, "5", limit=200)
                if df is None or df.empty:
                    logger.debug(f"⚠️ Sin datos OHLCV para {pair}")
                    continue

                current = float(df["close"].iloc[-1])
                price_change = (current - entry) / entry * 100
                if direction == "short":
                    price_change *= -1

                # Solo analizar si la operación va perdiendo más de 3%
                if price_change > -3:
                    continue

                # Detección de divergencias
                divs = detect_divergences(pair, df)
                has_divergence = divs.get("rsi_divergence") or divs.get("macd_divergence")

                # Confirmar con tendencia técnica
                tech = get_technical_data(pair, intervals=["5m", "15m"])
                new_trend = None
                if tech:
                    short_trend = tech.get("5m", {}).get("trend", "indefinida").lower()
                    higher_trend = tech.get("15m", {}).get("trend", "indefinida").lower()
                    if direction == "long" and ("bear" in short_trend or "bear" in higher_trend):
                        new_trend = "bajista"
                    elif direction == "short" and ("bull" in short_trend or "bull" in higher_trend):
                        new_trend = "alcista"

                if has_divergence or new_trend:
                    reversals += 1
                    msg = (
                        f"🚨 *Reversión detectada en {pair}*\n"
                        f"🔹 Entrada original: {direction.upper()} (x{lev})\n"
                        f"🔹 Precio actual: {current:.5f}\n"
                        f"🔹 Cambio estimado: {price_change:.2f}%\n"
                    )
                    if has_divergence:
                        msg += f"🧭 Divergencia detectada ({', '.join([k for k, v in divs.items() if v])})\n"
                    if new_trend:
                        msg += f"📈 Nueva tendencia probable: {new_trend.upper()}\n"
                    msg += "📌 Recomendación: Cerrar posición o abrir en dirección opuesta."

                    await send_message(msg)

            logger.info(f"✅ Monitor de reversiones: {checked} señales revisadas, {reversals} alertas emitidas.")

        except Exception as e:
            logger.error(f"❌ Error en monitor_reversals(): {e}")

        await asyncio.sleep(interval_seconds)
