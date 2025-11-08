"""
indicators.py (versión estable)
-------------------------------
Obtiene y calcula indicadores técnicos multi-temporalidad para análisis de señales.
Compatible con signal_manager.py, trend_analysis.py y operation_tracker.py.
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from bybit_client import get_ohlcv_data

logger = logging.getLogger("indicators")


# ================================================================
# 📊 Obtener indicadores técnicos multi-temporalidad
# ================================================================
def get_technical_data(symbol: str, intervals=["1m", "5m", "15m"]):
    """
    Recupera indicadores EMA, RSI, MACD, Bollinger Bands, ATR y volatilidad.
    Maneja tolerancia ante columnas faltantes y nombres diferentes.
    """
    data = {}

    for tf in intervals:
        try:
            interval = tf.replace("m", "")  # Bybit usa "1", "5", "15" ...
            df = get_ohlcv_data(symbol, interval=interval)

            if df is None or len(df) < 50:
                logger.warning(f"⚠️ Insuficientes velas para {symbol} ({tf})")
                continue

            # ================================================================
            # 🧮 Indicadores técnicos principales
            # ================================================================
            df["ema_short"] = ta.ema(df["close"], length=20)
            df["ema_long"] = ta.ema(df["close"], length=50)
            df["rsi"] = ta.rsi(df["close"], length=14)

            macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if macd_df is not None and isinstance(macd_df, pd.DataFrame):
                df["macd"] = macd_df.iloc[:, 0]
                df["macd_signal"] = macd_df.iloc[:, 1]
                df["macd_hist"] = macd_df.iloc[:, 2]
            else:
                df["macd"] = df["macd_signal"] = df["macd_hist"] = np.nan

            # ================================================================
            # 📊 Bollinger Bands (tolerante a nombres de columnas)
            # ================================================================
            try:
                bb = ta.bbands(df["close"], length=20)
                if bb is not None and isinstance(bb, pd.DataFrame):
                    # Buscar columnas U/M/L sin importar formato decimal
                    bb_cols = {c.split("_")[1]: c for c in bb.columns if c.startswith("BB")}
                    df["bb_upper"] = bb[bb_cols.get("U", list(bb.columns)[0])]
                    df["bb_mid"] = bb[bb_cols.get("M", list(bb.columns)[1])]
                    df["bb_lower"] = bb[bb_cols.get("L", list(bb.columns)[2])]
                else:
                    df["bb_upper"] = df["bb_mid"] = df["bb_lower"] = np.nan
            except Exception as e:
                logger.warning(f"⚠️ Error calculando Bollinger Bands para {symbol}: {e}")
                df["bb_upper"] = df["bb_mid"] = df["bb_lower"] = np.nan

            # ================================================================
            # 📈 ATR, volatilidad y ancho de bandas
            # ================================================================
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            df["atr_rel"] = df["atr"] / df["close"]
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

            # ================================================================
            # 🧠 Resumen técnico final
            # ================================================================
            data[tf] = {
                "price": df["close"].iloc[-1],
                "ema_short": df["ema_short"].iloc[-1],
                "ema_long": df["ema_long"].iloc[-1],
                "rsi": df["rsi"].iloc[-1],
                "rsi_series": df["rsi"].tail(10).tolist(),
                "macd": df["macd"].iloc[-1],
                "macd_hist": df["macd_hist"].iloc[-1],
                "macd_series": df["macd"].tail(10).tolist(),
                "atr_rel": df["atr_rel"].iloc[-1],
                "bb_width": df["bb_width"].iloc[-1],
                "volume": df["volume"].iloc[-1],
            }

            logger.info(f"📊 {symbol}: {len(df)} velas {tf} procesadas correctamente.")

        except Exception as e:
            logger.error(f"❌ Error calculando indicadores para {symbol} ({tf}): {e}")

    if not data:
        logger.warning(f"⚠️ No se pudieron obtener indicadores para {symbol}")
        return None

    return data
