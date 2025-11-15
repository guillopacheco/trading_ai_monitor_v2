"""
indicators.py (actualizado 2025-11)
---------------------------------
Cálculo técnico multi-temporalidad + detección de divergencias RSI/MACD.
Integrado con bybit_client.py.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from bybit_client import get_ohlcv_data  # ✅ versión actual
from smart_divergences import detect_smart_divergences  # 🆕 NUEVO
logger = logging.getLogger("indicators")


# ================================================================
# 🔍 Validación de datos
# ================================================================
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


# ================================================================
# 🔍 Detección de divergencias
# ================================================================
def detect_divergences(df: pd.DataFrame, method: str = "macd", lookback: int = 30):
    """
    Detecta divergencias simples en MACD o RSI.
    Retorna 'bullish', 'bearish' o None.
    """
    try:
        if len(df) < lookback + 3:
            return None

        recent = df.tail(lookback).copy()

        if method.lower() == "macd":
            if not all(x in recent.columns for x in ["macd", "macd_signal"]):
                return None
            recent["macd_hist"] = recent["macd"] - recent["macd_signal"]

            # Divergencia bajista: precio sube pero MACD baja
            price_highs = recent["high"].iloc[-3:]
            macd_highs = recent["macd_hist"].iloc[-3:]
            if price_highs.iloc[-1] > price_highs.iloc[-2] and macd_highs.iloc[-1] < macd_highs.iloc[-2]:
                return "bearish"

            # Divergencia alcista: precio baja pero MACD sube
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

            # Divergencia bajista RSI
            if price_highs.iloc[-1] > price_highs.iloc[-2] and rsi_highs.iloc[-1] < rsi_highs.iloc[-2]:
                return "bearish"

            # Divergencia alcista RSI
            if price_lows.iloc[-1] < price_lows.iloc[-2] and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
                return "bullish"

        return None
    except Exception as e:
        logger.warning(f"⚠️ Error detectando divergencias: {e}")
        return None


def enrich_with_divergences(df: pd.DataFrame):
    """
    Analiza divergencias MACD y RSI dentro del DataFrame técnico.
    Devuelve etiquetas de riesgo si se detectan contradicciones.
    """
    try:
        macd_div = detect_divergences(df, "macd")
        rsi_div = detect_divergences(df, "rsi")

        alerts = []
        if macd_div == "bearish" or rsi_div == "bearish":
            alerts.append("⚠️ Divergencia bajista detectada (riesgo de reversión).")
        elif macd_div == "bullish" or rsi_div == "bullish":
            alerts.append("⚠️ Divergencia alcista detectada (posible rebote).")

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
def get_technical_data(symbol: str, intervals=["1m", "5m", "15m"]):
    """Calcula EMA, RSI, MACD, Bollinger, ATR y divergencias."""
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

            # 🆕 Money Flow Index (MFI)
            try:
                df["mfi"] = ta.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)
            except Exception:
                df["mfi"] = np.nan

            last = df.iloc[-1]
            trend = "bullish" if last["ema_short"] > last["ema_long"] else "bearish"

            # 🔍 Enriquecimiento con divergencias simples (legacy)
            divs = enrich_with_divergences(df)

            # 🆕 Divergencias avanzadas "tipo TradingView"
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

                # 🆕 Campos de divergencias avanzadas
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
