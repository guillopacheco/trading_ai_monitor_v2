"""
divergence_detector.py (versión final sincronizada)
------------------------------------------------------------
Analiza divergencias en RSI, MACD y Volumen a partir de los datos
calculados en indicators.py. Compatible con trend_analysis.py y
test_trend_system.py.
------------------------------------------------------------
"""

import numpy as np
import logging

logger = logging.getLogger("divergence_detector")

# ================================================================
# 📈 Detección de divergencias
# ================================================================
def detect_divergences(symbol: str, tech_data: dict):
    """
    Detecta divergencias básicas RSI, MACD y Volumen.

    Args:
        symbol (str): par analizado (ej. BTCUSDT)
        tech_data (dict): datos técnicos generados por indicators.get_technical_data()

    Returns:
        dict: estado de divergencias {'RSI': str, 'MACD': str, 'Volumen': str}
    """
    try:
        results = {"RSI": "Ninguna", "MACD": "Ninguna", "Volumen": "Ninguna"}

        for tf, data in tech_data.items():
            rsi_series = data.get("rsi_series", [])
            macd_series = data.get("macd_series", [])
            volume = data.get("volume", 0)

            # ================================================================
            # 🔹 Divergencia RSI (comparación últimas dos oscilaciones)
            # ================================================================
            if len(rsi_series) >= 3:
                prev, last = rsi_series[-3], rsi_series[-1]
                if last > prev and last > 60:
                    results["RSI"] = f"Alcista ({tf})"
                elif last < prev and last < 40:
                    results["RSI"] = f"Bajista ({tf})"

            # ================================================================
            # 🔹 Divergencia MACD (histograma)
            # ================================================================
            if len(macd_series) >= 3:
                prev, last = macd_series[-3], macd_series[-1]
                if last > prev and last > 0:
                    results["MACD"] = f"Alcista ({tf})"
                elif last < prev and last < 0:
                    results["MACD"] = f"Bajista ({tf})"

            # ================================================================
            # 🔹 Divergencia de Volumen
            # ================================================================
            if volume and volume > 0:
                atr_rel = data.get("atr_rel", 0)
                if atr_rel > 0.02 and volume > 1.3 * np.mean([v for v in [volume, volume * 0.9, volume * 1.1]]):
                    results["Volumen"] = f"Alta volatilidad ({tf})"

        logger.info(f"📊 {symbol}: divergencias detectadas {results}")
        return results

    except Exception as e:
        logger.error(f"❌ Error detectando divergencias en {symbol}: {e}")
        return {"RSI": "Error", "MACD": "Error", "Volumen": "Error"}
