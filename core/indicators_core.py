# =====================================================================
# indicators_core.py
# ---------------------------------------------------------------
# Cálculos estandarizados de indicadores:
#   - RSI
#   - MACD
#   - ATR
#   - Tendencia Zero-Lag
#   - Divergencias inteligentes
# =====================================================================

import pandas as pd
import pandas_ta as ta
from services.bybit_service import get_ohlcv


async def fetch_indicators(symbol: str, timeframe: str) -> dict:
    """
    Devuelve un paquete completo de indicadores para 1 TF.
    """

    df = await get_ohlcv(symbol, timeframe)
    if df is None or df.empty:
        return None

    # ========= RSI =========
    rsi = ta.rsi(df["close"], length=14)
    df["rsi"] = rsi

    # ========= MACD =========
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd_hist"] = macd["MACDh_12_26_9"]

    # ========= ATR % =========
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["atr_pct"] = (atr / df["close"]) * 100

    # ========= Tendencia Zero-Lag =========
    df["t_zl"] = ta.ema(df["close"], length=34)
    df["trend"] = df["close"] > df["t_zl"]

    # ========= Divergencias inteligentes =========
    # (placeholder simple, el Motor A+ usa detect_smart_divergences internamente)
    df["divergence"] = None

    return {
        "rsi": float(df["rsi"].iloc[-1]),
        "macd_hist": float(df["macd_hist"].iloc[-1]),
        "atr_pct": float(df["atr_pct"].iloc[-1]),
        "trend_raw": bool(df["trend"].iloc[-1]),
        "divergence": None,
    }
