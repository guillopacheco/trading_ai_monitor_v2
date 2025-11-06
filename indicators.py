"""
Indicadores técnicos y utilidades de análisis
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("indicators")

# ================================================================
# 📊 Parámetros técnicos de indicadores
# ================================================================
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_PERIOD = 14
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ================================================================
# 📈 Funciones de indicadores
# ================================================================
def ema(df: pd.DataFrame, period: int, column="close"):
    return df[column].ewm(span=period, adjust=False).mean()

def rsi(df: pd.DataFrame, period: int = 14, column="close"):
    delta = df[column].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(df: pd.DataFrame, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    ema_fast = ema(df, fast)
    ema_slow = ema(df, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD):
    try:
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = high_low.combine(high_close, max).combine(low_close, max)
        atr = tr.rolling(window=period).mean()
        return atr
    except Exception as e:
        logger.error(f"Error calculando ATR: {e}")
        return pd.Series(dtype=float)
