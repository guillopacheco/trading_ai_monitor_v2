"""
core/indicators_core.py
-----------------------
Cálculo técnico puro:
✔ EMA / RSI / MACD / BB / ATR
✔ Divergencias clásicas
✔ Selección automática de temporalidades
"""

import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger("indicators_core")


# ============================================================
# 🧠 Selección de temporalidades
# ============================================================

PREFERRED_INTERVALS = ["4h", "1h", "30m", "15m", "5m", "3m", "1m"]


def _is_valid_df(df: pd.DataFrame, min_len: int = 150) -> bool:
    return df is not None and not df.empty and len(df) >= min_len


def select_best_intervals(available_data: dict, n: int = 3) -> list:
    """
    available_data: dict { "1h": df, "4h": df, ... }
    Devuelve las N mejores temporalidades en orden de prioridad.
    """
    valid = []
    for tf in PREFERRED_INTERVALS:
        if tf in available_data and _is_valid_df(available_data[tf]):
            valid.append(tf)
        if len(valid) == n:
            break

    if not valid:
        # fallback conservador
        return ["5m", "3m", "1m"]

    return valid[:n]


# ============================================================
# 🔍 Divergencias clásicas
# ============================================================

def detect_divergences(df: pd.DataFrame, method: str = "macd", lookback: int = 30):
    """
    Retorna:
        - 'bullish' / 'bearish' / None
    """
    try:
        if df is None or len(df) < lookback + 3:
            return None

        recent = df.tail(lookback).copy()

        if method == "macd":
            if not {"macd", "macd_signal"}.issubset(recent.columns):
                return None

            recent["macd_hist"] = recent["macd"] - recent["macd_signal"]

            # Máximo de precio sube pero histograma cae → divergencia bajista
            if (
                recent["high"].iloc[-1] > recent["high"].iloc[-2]
                and recent["macd_hist"].iloc[-1] < recent["macd_hist"].iloc[-2]
            ):
                return "bearish"

            # Mínimo de precio baja pero histograma sube → divergencia alcista
            if (
                recent["low"].iloc[-1] < recent["low"].iloc[-2]
                and recent["macd_hist"].iloc[-1] > recent["macd_hist"].iloc[-2]
            ):
                return "bullish"

        if method == "rsi":
            if "rsi" not in recent.columns:
                return None

            if (
                recent["high"].iloc[-1] > recent["high"].iloc[-2]
                and recent["rsi"].iloc[-1] < recent["rsi"].iloc[-2]
            ):
                return "bearish"

            if (
                recent["low"].iloc[-1] < recent["low"].iloc[-2]
                and recent["rsi"].iloc[-1] > recent["rsi"].iloc[-2]
            ):
                return "bullish"

        return None
    except Exception as e:
        logger.error(f"❌ Error en detect_divergences: {e}")
        return None


# ============================================================
# 📊 Cálculo de indicadores + foto de la última vela
# ============================================================

def compute_indicators(df: pd.DataFrame) -> dict | None:
    """
    Recibe OHLCV (DataFrame) y devuelve un dict con:
        - trend
        - price
        - ema_short / ema_long
        - rsi
        - macd / macd_hist
        - atr_rel
        - bb_width
    """
    try:
        if df is None or df.empty:
            return None

        df = df.copy()

        # EMAs
        df["ema_short"] = ta.ema(df["close"], length=10)
        df["ema_long"] = ta.ema(df["close"], length=30)

        # RSI
        df["rsi"] = ta.rsi(df["close"], length=14)

        # MACD
        macd = ta.macd(df["close"])
        if macd is not None and not macd.empty:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 1]
            df["macd_hist"] = macd.iloc[:, 2]

        # Bandas de Bollinger
        bb = ta.bbands(df["close"])
        if bb is not None and not bb.empty:
            df["bb_upper"] = bb.iloc[:, 0]
            df["bb_mid"] = bb.iloc[:, 1]
            df["bb_lower"] = bb.iloc[:, 2]

        # ATR
        df["atr"] = ta.atr(df["high"], df["low"], df["close"])
        df["atr_rel"] = df["atr"] / df["close"]

        # Anchura de bandas
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

        last = df.iloc[-1]

        trend = "bullish" if last["ema_short"] > last["ema_long"] else "bearish"

        return {
            "trend": trend,
            "price": float(last["close"]),
            "ema_short": float(last["ema_short"]),
            "ema_long": float(last["ema_long"]),
            "rsi": float(last["rsi"]),
            "macd": float(last.get("macd", 0.0)),
            "macd_hist": float(last.get("macd_hist", 0.0)),
            "atr_rel": float(last["atr_rel"]),
            "bb_width": float(last["bb_width"]),
        }

    except Exception as e:
        logger.error(f"❌ Error en compute_indicators: {e}")
        return None
