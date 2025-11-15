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
    Versión nueva:
    - Usa los campos 'smart_rsi_div', 'smart_macd_div', 'smart_confidence'
      generados en indicators.get_technical_data().
    - Mantiene el formato de salida: {'RSI': str, 'MACD': str, 'Volumen': str}
    para compatibilidad con trend_analysis.py.
    """
    try:
        results = {"RSI": "Ninguna", "MACD": "Ninguna", "Volumen": "Ninguna"}

        if not tech_data:
            return results

        best_rsi = None
        best_macd = None
        best_conf = 0.0
        high_vol = False

        for tf, data in tech_data.items():
            rsi_type = data.get("smart_rsi_div") or data.get("rsi_div")
            macd_type = data.get("smart_macd_div") or data.get("macd_div")
            conf = float(data.get("smart_confidence", 0.0))
            atr_rel = float(data.get("atr_rel", 0.0))
            bb_width = float(data.get("bb_width", 0.0))

            # Elegimos la divergencia con mayor confianza
            if rsi_type and rsi_type != "none" and conf >= best_conf:
                best_conf = conf
                best_rsi = f"{'Alcista' if rsi_type == 'bullish' else 'Bajista'} ({tf})"

            if macd_type and macd_type != "none" and conf >= best_conf:
                best_conf = conf
                best_macd = f"{'Alcista' if macd_type == 'bullish' else 'Bajista'} ({tf})"

            # Volatilidad / volumen altos como “divergencia de volatilidad”
            if atr_rel > 0.02 or bb_width > 0.06:
                high_vol = True

        if best_rsi:
            results["RSI"] = best_rsi
        if best_macd:
            results["MACD"] = best_macd
        if high_vol:
            results["Volumen"] = "Alta volatilidad"

        logger.info(f"📊 {symbol}: divergencias smart {results}")
        return results

    except Exception as e:
        logger.error(f"❌ Error detectando divergencias en {symbol}: {e}")
        return {"RSI": "Error", "MACD": "Error", "Volumen": "Error"}
