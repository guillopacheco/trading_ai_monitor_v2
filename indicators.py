import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from bybit import BybitClient

logger = logging.getLogger("indicators")

# ================================================================
# ⚙️ Configuración general
# ================================================================
MIN_REQUIRED_CANDLES = 50   # mínimo de velas válidas por temporalidad
ATR_PERIOD = 14             # período estándar para el ATR

# ================================================================
# 📈 Funciones principales
# ================================================================
def get_available_timeframes():
    """Temporalidades más usadas; se adaptan según disponibilidad."""
    return ["1m", "5m", "15m", "1h", "4h", "1d"]


def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 100):
    """Obtiene los datos OHLCV desde Bybit."""
    try:
        client = BybitClient()
        df = client.get_ohlcv(symbol, timeframe, limit)
        if df is None or len(df) < MIN_REQUIRED_CANDLES:
            logger.warning(f"⚠️ Insuficientes datos para {symbol} en {timeframe} ({len(df) if df is not None else 0} velas).")
            return None
        return df
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos OHLCV para {symbol} {timeframe}: {e}")
        return None


def calculate_ema(series, period: int = 10):
    """Cálculo genérico de EMA."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series, period: int = 14):
    """Cálculo del RSI."""
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(series, fast=12, slow=26, signal=9):
    """Cálculo del MACD."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD):
    """Cálculo del Average True Range (ATR)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1] if len(atr) > period else None


def determine_volatility_level(atr_value: float, price: float):
    """Clasifica la volatilidad en baja, media o alta."""
    if atr_value is None or price == 0:
        return "unknown"

    ratio = (atr_value / price) * 100
    if ratio > 2.0:
        return "alta"
    elif ratio > 1.0:
        return "media"
    else:
        return "baja"


# ================================================================
# 🔍 Análisis completo por símbolo
# ================================================================
def analyze_symbol(symbol: str):
    """
    Obtiene los datos del símbolo en múltiples temporalidades disponibles,
    calcula EMA, RSI, MACD, ATR y clasifica volatilidad.
    """
    results = {}
    available_timeframes = []
    logger.info(f"🔍 Analizando temporalidades disponibles para {symbol}...")

    for tf in get_available_timeframes():
        df = fetch_ohlcv(symbol, tf)
        if df is not None and len(df) >= MIN_REQUIRED_CANDLES:
            available_timeframes.append(tf)
            close = df["close"]

            ema10 = calculate_ema(close, 10).iloc[-1]
            ema30 = calculate_ema(close, 30).iloc[-1]
            rsi = calculate_rsi(close, 14).iloc[-1]
            macd, signal_line = calculate_macd(close)
            atr = calculate_atr(df)
            price = close.iloc[-1]
            vol_level = determine_volatility_level(atr, price)

            results[tf] = {
                "ema10": round(ema10, 5),
                "ema30": round(ema30, 5),
                "rsi": round(rsi, 2),
                "macd": round(macd.iloc[-1], 5),
                "signal": round(signal_line.iloc[-1], 5),
                "atr": round(atr, 5) if atr else None,
                "volatility": vol_level,
                "price": price,
                "trend": "alcista" if ema10 > ema30 else "bajista"
            }
        else:
            logger.warning(f"⛔ {symbol}: sin datos válidos para {tf}")

    if not available_timeframes:
        logger.error(f"❌ No se encontraron temporalidades útiles para {symbol}")
        return None

    logger.info(f"✅ Análisis técnico completado para {symbol}: {len(available_timeframes)} temporalidades válidas.")
    return results
