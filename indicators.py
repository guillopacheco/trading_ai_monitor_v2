"""
indicators.py (versión optimizada)
----------------------------------
Genera indicadores técnicos multi-temporalidad para Bybit (futuros lineales USDT).
Compatible con trend_analysis.py.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from bybit_client import get_ohlcv_data

logger = logging.getLogger("indicators")

def get_technical_data(symbol, intervals=["1m", "5m", "15m"]):
    """Obtiene datos técnicos para varias temporalidades."""
    data = {}
    for tf in intervals:
        interval = tf.replace("m", "")  # Bybit usa 1,5,15
        df = get_ohlcv_data(symbol, interval=interval)
        if df is None or len(df) < 50:
            logger.warning(f"⚠️ Insuficientes velas para {symbol} ({tf})")
            continue

        df["ema_short"] = ta.ema(df["close"], length=20)
        df["ema_long"] = ta.ema(df["close"], length=50)
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["macd"], df["macd_signal"], df["macd_hist"] = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["bb_upper"], df["bb_mid"], df["bb_lower"] = ta.bbands(df["close"], length=20)[["BBU_20_2.0", "BBM_20_2.0", "BBL_20_2.0"]].values.T

        # 🧠 Mejora aplicada: ATR y relación normalizada
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["atr_rel"] = df["atr"] / df["close"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

        data[tf] = {
            "price": df["close"].tolist(),
            "ema_short": df["ema_short"].iloc[-1],
            "ema_long": df["ema_long"].iloc[-1],
            "rsi": df["rsi"].iloc[-1],
            "rsi_series": df["rsi"].tail(10).tolist(),
            "macd": df["macd"].iloc[-1],
            "macd_line": df["macd"].tail(10).tolist(),
            "macd_hist": df["macd_hist"].iloc[-1],
            "atr_rel": df["atr_rel"].iloc[-1],
            "bb_width": df["bb_width"].iloc[-1],
            "volume": df["volume"].tolist(),
        }

    if not data:
        logger.warning(f"⚠️ No se pudieron obtener indicadores para {symbol}")
        return None

    return data
