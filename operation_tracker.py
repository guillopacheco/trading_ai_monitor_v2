import time
import logging
from datetime import datetime
from indicators import get_indicators
from notifier import notify_operation_alert
from database import update_operation_status, get_alert_record, update_alert_record
from helpers import calculate_roi, get_current_price

logger = logging.getLogger("operation_tracker")

# ================================================================
# ⚙️ Configuración
# ================================================================
ALERT_LEVELS = [-30, -50, -70, -90]   # Niveles de ROI (%)
ATR_INTERVALS = {
    "high": 300,   # ATR alto → cada 5 min
    "medium": 480, # ATR medio → cada 8 min
    "low": 720     # ATR bajo → cada 12 min
}

# ================================================================
# 📊 Cálculo de ATR (Volatilidad)
# ================================================================
def calculate_atr(symbol: str, period: int = 14):
    """
    Calcula el Average True Range (ATR) usando datos de 1m.
    Devuelve valor promedio y clasificación de volatilidad.
    """
    try:
        df = get_indicators(symbol, ["1m"]).get("1m")
        if df is None or len(df) < period + 1:
            logger.warning(f"⚠️ Datos insuficientes para ATR de {symbol}")
            return 0.0, "low"

        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())

        tr = high_low.combine(high_close, max).combine(low_close, max)
        atr = tr.rolling(window=period).mean().iloc[-1]
        avg_price = df["close"].mean()
        atr_percent = (atr / avg_price) * 100

        if atr_percent > 1.5:
            level = "high"
        elif atr_percent > 0.7:
            level = "medium"
        else:
            level = "low"

        logger.info(f"📈 ATR {symbol}: {atr_percent:.2f}% ({level})")
        return atr_percent, level

    except Exception as e:
        logger.error(f"❌ Error calculando ATR para {symbol}: {e}")
        return 0.0, "low"

# ================================================================
# 🔄 Monitoreo de operaciones
# ================================================================
def monitor_open_positions(positions):
    """
    Evalúa posiciones abiertas, ajusta frecuencia de análisis según ATR,
    y envía alertas progresivas por pérdida (ROI).
    """
    logger.info(f"🧭 Iniciando monitoreo de {len(positions)} operaciones abiertas...")

    while positions:
        for pos in positions:
            try:
                symbol = pos["symbol"]
                direction = pos["direction"]
                entry_price = pos["entry"]
                leverage = pos.get("leverage", 20)

                # === 1️⃣ Obtener precio actual ===
                current_price = get_current_price(symbol)
                roi = calculate_roi(entry_price, current_price, direction, leverage)
                atr_val, vol_level = calculate_atr(symbol)

                # === 2️⃣ Actualizar estado en base de datos ===
                update_operation_status(symbol, "open", roi)

                # === 3️⃣ Verificar si requiere alerta ===
                alert = get_alert_record(symbol)
                next_level = next((lvl for lvl in ALERT_LEVELS if roi <= lvl), None)

                if next_level and (not alert or alert["last_alert_level"] > next_level):
                    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    send_alert(symbol, direction, roi, next_level, vol_level)
                    update_alert_record(symbol, next_level, timestamp)

                # === 4️⃣ Ajustar intervalo según volatilidad ===
                delay = ATR_INTERVALS.get(vol_level, 600)
                logger.info(f"⏱️ {symbol}: ROI {roi:.2f}% | Vol {vol_level} | Próximo check en {delay/60:.1f} min")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"❌ Error monitoreando {pos['symbol']}: {e}")
                time.sleep(60)

# ================================================================
# 🚨 Envío de alertas
# ================================================================
def send_alert(symbol, direction, roi, level, volatility):
    """
    Envía una alerta de pérdida progresiva a Telegram.
    """
    try:
        msg = (
            f"⚠️ *ALERTA DE OPERACIÓN*\n\n"
            f"🪙 *Par:* {symbol}\n"
            f"📈 *Dirección:* {direction.upper()}\n"
            f"💰 *ROI actual:* {roi:.2f}%\n"
            f"📊 *Nivel de pérdida:* {level}%\n"
            f"🌡️ *Volatilidad:* {volatility.upper()}\n\n"
            f"📌 Sugerencia: Evaluar tendencia técnica y considerar mantener, cerrar o revertir posición."
        )
        notify_operation_alert(symbol, msg)
        logger.warning(f"🚨 Alerta enviada: {symbol} {level}% ({roi:.2f}%)")
    except Exception as e:
        logger.error(f"❌ Error enviando alerta de {symbol}: {e}")
