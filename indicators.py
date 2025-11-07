"""
indicators.py
-------------------------------------------------------
Módulo central para obtención y cálculo de indicadores
técnicos de múltiples temporalidades.
-------------------------------------------------------
Proporciona:
- get_technical_data(symbol, timeframe)
- get_indicators(symbol, timeframes)
Usado por: signal_manager.py, trend_analysis.py, divergence_detector.py
-------------------------------------------------------
"""

import logging
import pandas as pd
import pandas_ta as ta
from bybit_client import get_ohlcv_data

logger = logging.getLogger("indicators")


# ================================================================
# 📈 Cálculo individual de indicadores técnicos
# ================================================================
def get_technical_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> dict:
    """
    Descarga datos OHLCV desde Bybit y calcula los indicadores técnicos principales.
    Devuelve un diccionario con los valores relevantes para el análisis de tendencia.
    """
    try:
        df = get_ohlcv_data(symbol, timeframe, limit=limit)

        if df is None or len(df) < 50:
            logger.warning(f"⚠️ Insuficientes velas para {symbol} ({timeframe})")
            return None

        # --- EMA 10 / EMA 30 (tendencia principal)
        df["ema_short"] = ta.ema(df["close"], length=10)
        df["ema_long"] = ta.ema(df["close"], length=30)

        # --- RSI 14 (momentum)
        df["rsi"] = ta.rsi(df["close"], length=14)

        # --- MACD (momentum + dirección)
        macd = ta.macd(df["close"])
        df["macd_line"] = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_hist"] = macd["MACDh_12_26_9"]

        # --- ATR 14 (volatilidad)
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["atr_rel"] = df["atr"] / df["close"]

        # --- Bollinger Bands (ancho de banda)
        bb = ta.bbands(df["close"], length=20, std=2)
        df["bb_width"] = (bb["BBU_20_2.0"] - bb["BBL_20_2.0"]) / df["close"]

        # --- Resultado final
        result = {
            "price": df["close"].tolist(),
            "ema_short": float(df["ema_short"].iloc[-1]),
            "ema_long": float(df["ema_long"].iloc[-1]),
            "rsi": float(df["rsi"].iloc[-1]),
            "macd_line": float(df["macd_line"].iloc[-1]),
            "macd_signal": float(df["macd_signal"].iloc[-1]),
            "macd_hist": float(df["macd_hist"].iloc[-1]),
            "atr": float(df["atr"].iloc[-1]),
            "atr_rel": float(df["atr_rel"].iloc[-1]),
            "bb_width": float(df["bb_width"].iloc[-1]),
            "volume": df["volume"].tolist(),
        }

        return result

    except Exception as e:
        logger.error(f"❌ Error calculando indicadores para {symbol} ({timeframe}): {e}")
        return None


# ================================================================
# 🧠 Multi-timeframe integration
# ================================================================
def get_indicators(symbol: str, timeframes=None) -> dict:
    """
    Obtiene indicadores para varias temporalidades.
    Retorna un dict con claves = timeframe y valores = datos de indicadores.
    """
    if timeframes is None:
        timeframes = ["1m", "5m", "15m"]

    results = {}
    for tf in timeframes:
        try:
            tf_data = get_technical_data(symbol, timeframe=tf)
            if tf_data:
                results[tf] = tf_data
                logger.info(f"✅ Indicadores {symbol} ({tf}) calculados correctamente.")
            else:
                logger.warning(f"⚠️ No se pudieron obtener indicadores para {symbol} ({tf})")
        except Exception as e:
            logger.error(f"❌ Error obteniendo indicadores de {symbol} ({tf}): {e}")

    return results


# ================================================================
# 🧪 Test local manual
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🔍 Test técnico de indicadores para BTCUSDT...")
    data = get_indicators("BTCUSDT", ["1m", "5m", "15m"])
    for tf, info in data.items():
        print(f"\n🕒 {tf}")
        for k, v in info.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
