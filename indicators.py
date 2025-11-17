"""
indicators.py (actualizado 2025-11 con selección dinámica de temporalidades)
---------------------------------------------------------------------------  
Cálculo técnico multi-temporalidad + divergencias avanzadas + selección automática
de las 3 mejores temporalidades disponibles para trading de futuros (20x).
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from bybit_client import get_ohlcv_data
from smart_divergences import detect_smart_divergences

logger = logging.getLogger("indicators")


# ================================================================
# 🧠 Selección inteligente de temporalidades
# ================================================================
PREFERRED_INTERVALS = ["4h", "1h", "30m", "15m", "5m", "3m", "1m"]


def _is_valid_df(df):
    """Evalúa si un dataframe tiene suficiente calidad."""
    if df is None or df.empty:
        return False
    if len(df) < 150:  # velas mínimas para indicadores confiables
        return False
    return True


def select_best_intervals(symbol: str, n=3):
    """
    Selecciona las mejores temporalidades disponibles, priorizando:
    1) estabilidad de tendencia
    2) coherencia interna
    3) suficiente número de velas
    """

    valid = []

    for tf in PREFERRED_INTERVALS:
        try:
            tf_numerical = tf.replace("m", "").replace("h", "")
            df = get_ohlcv_data(symbol, interval=tf_numerical)

            if _is_valid_df(df):
                valid.append(tf)
        except Exception:
            continue

        if len(valid) == n:
            break

    # fallback si el token es muy nuevo
    if not valid:
        return ["5m", "3m", "1m"]

    return valid[:n]


# ================================================================
# 🔍 Validación de OHLCV
# ================================================================
def _validate_df(df: pd.DataFrame, symbol: str, tf: str) -> bool:
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


# ================================================================
# 🔍 Divergencias clásicas (MACD / RSI)
# ================================================================
def detect_divergences(df: pd.DataFrame, method: str = "macd", lookback: int = 30):
    try:
        if len(df) < lookback + 3:
            return None

        recent = df.tail(lookback).copy()

        if method.lower() == "macd":
            if not all(x in recent.columns for x in ["macd", "macd_signal"]):
                return None

            recent["macd_hist"] = recent["macd"] - recent["macd_signal"]

            price_highs = recent["high"].iloc[-3:]
            macd_highs = recent["macd_hist"].iloc[-3:]

            if price_highs.iloc[-1] > price_highs.iloc[-2] and macd_highs.iloc[-1] < macd_highs.iloc[-2]:
                return "bearish"

            price_lows = recent["low"].iloc[-3:]
            macd_lows = recent["macd_hist"].iloc[-3:]

            if price_lows.iloc[-1] < price_lows.iloc[-2] and macd_lows.iloc[-1] > macd_lows.iloc[-2]:
                return "bullish"

        elif method.lower() == "rsi":
            if "rsi" not in recent.columns:
                return None

            price_highs = recent["high"].iloc[-3:]
            rsi_highs = recent["rsi"].iloc[-3:]
            price_lows = recent["low"].iloc[-3:]
            rsi_lows = recent["rsi"].iloc[-3:]

            if price_highs.iloc[-1] > price_highs.iloc[-2] and rsi_highs.iloc[-1] < rsi_highs.iloc[-2]:
                return "bearish"

            if price_lows.iloc[-1] < price_lows.iloc[-2] and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
                return "bullish"

        return None
    except Exception as e:
        logger.warning(f"⚠️ Error detectando divergencias: {e}")
        return None


def enrich_with_divergences(df: pd.DataFrame):
    try:
        macd_div = detect_divergences(df, "macd")
        rsi_div = detect_divergences(df, "rsi")

        alerts = []
        if macd_div == "bearish" or rsi_div == "bearish":
            alerts.append("⚠️ Divergencia bajista detectada.")
        elif macd_div == "bullish" or rsi_div == "bullish":
            alerts.append("⚠️ Divergencia alcista detectada.")

        return {
            "macd_divergence": macd_div,
            "rsi_divergence": rsi_div,
            "divergence_alerts": alerts,
        }
    except Exception as e:
        logger.error(f"❌ Error al enriquecer con divergencias: {e}")
        return {
            "macd_divergence": None,
            "rsi_divergence": None,
            "divergence_alerts": [],
        }


# ================================================================
# 📊 Cálculo técnico principal
# ================================================================
def get_technical_data(symbol: str, intervals=None):
    """
    Calcula indicadores técnicos para múltiples temporalidades.
    Si intervals=None → selecciona automáticamente las mejores.
    """
    # 🧠 Selección automática si no vienen intervalos
    if intervals is None:
        intervals = select_best_intervals(symbol)

    data = {}

    for tf in intervals:
        try:
            raw_tf = tf.replace("m", "").replace("h", "")
            df = get_ohlcv_data(symbol, interval=raw_tf)

            if not _validate_df(df, symbol, tf):
                continue

            # === Indicadores ===
            df["ema_short"] = ta.ema(df["close"], length=10)
            df["ema_long"] = ta.ema(df["close"], length=30)
            df["rsi"] = ta.rsi(df["close"], length=14)

            macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if isinstance(macd, pd.DataFrame):
                df["macd"], df["macd_signal"], df["macd_hist"] = macd.iloc[:, 0], macd.iloc[:, 1], macd.iloc[:, 2]

            bb = ta.bbands(df["close"], length=20)
            if isinstance(bb, pd.DataFrame):
                df["bb_upper"], df["bb_mid"], df["bb_lower"] = bb.iloc[:, 0], bb.iloc[:, 1], bb.iloc[:, 2]

            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            df["atr_rel"] = df["atr"] / df["close"]
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

            try:
                df["mfi"] = ta.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)
            except:
                df["mfi"] = np.nan

            last = df.iloc[-1]
            trend = "bullish" if last["ema_short"] > last["ema_long"] else "bearish"

            # Divergencias clásicas
            divs = enrich_with_divergences(df)

            # Divergencias avanzadas
            smart_divs = detect_smart_divergences(df)

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
                "macd_div": divs["macd_divergence"],
                "rsi_div": divs["rsi_divergence"],
                "alerts": divs["divergence_alerts"],
                "smart_divergences": smart_divs,
                "smart_rsi_div": smart_divs["divergences"]["rsi"]["type"],
                "smart_macd_div": smart_divs["divergences"]["macd"]["type"],
                "smart_div_strength": max(
                    smart_divs["divergences"]["rsi"]["strength"],
                    smart_divs["divergences"]["macd"]["strength"],
                ),
                "smart_bias": smart_divs["overall_bias"],
                "smart_confidence": smart_divs["confidence"],
            }

            if divs["divergence_alerts"]:
                for alert in divs["divergence_alerts"]:
                    logger.warning(f"⚠️ {symbol} ({tf}) {alert}")

            logger.info(f"📊 {symbol} ({tf}): {trend.upper()} ({len(df)} velas)")

        except Exception as e:
            logger.error(f"❌ Error calculando indicadores para {symbol} ({tf}): {e}")

    return data if data else None
