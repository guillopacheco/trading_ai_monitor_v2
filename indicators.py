"""
indicators.py (sincronizado 2025)
---------------------------------
Cálculo técnico multi-temporalidad — integrado con bybit_client_v13_signals_fix.py.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from bybit_client_v13_signals_fix import get_ohlcv_data

logger = logging.getLogger("indicators")


def _validate_df(df: pd.DataFrame, symbol: str, tf: str) -> bool:
    """Valida estructura mínima del DataFrame."""
    if df is None or df.empty:
        logger.warning(f"⚠️ No se recibieron datos para {symbol} ({tf})")
        return False
    if not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
        logger.error(f"❌ Columnas faltantes en OHLCV {symbol} ({tf})")
        return False
    if len(df) < 20:
        logger.warning(f"⚠️ Solo {len(df)} velas disponibles para {symbol} ({tf})")
        return False
    return True


def get_technical_data(symbol: str, intervals=["1m", "5m", "15m"]):
    """Calcula EMA, RSI, MACD, Bollinger, ATR y devuelve resumen técnico."""
    data = {}
    for tf in intervals:
        try:
            interval = tf.replace("m", "")
            df = get_ohlcv_data(symbol, interval=interval)
            if not _validate_df(df, symbol, tf):
                continue

            # EMA / RSI
            df["ema_short"] = ta.ema(df["close"], length=10)
            df["ema_long"] = ta.ema(df["close"], length=30)
            df["rsi"] = ta.rsi(df["close"], length=14)

            # MACD
            macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if isinstance(macd, pd.DataFrame):
                df["macd"], df["macd_signal"], df["macd_hist"] = macd.iloc[:, 0], macd.iloc[:, 1], macd.iloc[:, 2]

            # Bollinger
            bb = ta.bbands(df["close"], length=20)
            if isinstance(bb, pd.DataFrame):
                df["bb_upper"], df["bb_mid"], df["bb_lower"] = bb.iloc[:, 0], bb.iloc[:, 1], bb.iloc[:, 2]

            # ATR
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            df["atr_rel"] = df["atr"] / df["close"]
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

            last = df.iloc[-1]
            trend = "bullish" if last["ema_short"] > last["ema_long"] else "bearish"

            data[tf] = {
                "price": float(last["close"]),
                "ema_short": float(last["ema_short"]),
                "ema_long": float(last["ema_long"]),
                "rsi": float(last["rsi"]),
                "macd": float(last["macd"]),
                "macd_hist": float(last["macd_hist"]),
                "atr_rel": float(last["atr_rel"]),
                "bb_width": float(last["bb_width"]),
                "volume": float(last["volume"]),
                "trend": trend,
            }

            logger.info(f"📊 {symbol} ({tf}): {trend.upper()} ({len(df)} velas)")

        except Exception as e:
            logger.error(f"❌ Error calculando indicadores para {symbol} ({tf}): {e}")

    return data if data else None
