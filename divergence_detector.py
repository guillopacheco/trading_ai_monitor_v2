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
    Versión nueva corregida:
    - Toma divergencias reales desde indicators.py (smart divergences).
    - Si no hay smart, cae en divergencias simples (legacy).
    - Devuelve formato clásico: {'RSI': str, 'MACD': str, 'Volumen': str}
    para compatibilidad con trend_analysis.
    """
    try:
        results = {"RSI": "Ninguna", "MACD": "Ninguna", "Volumen": "Ninguna"}

        if not tech_data:
            return results

        best_conf = 0

        # Selección final
        best_rsi_text = None
        best_macd_text = None

        for tf, data in tech_data.items():

            # --- SMART DIVERGENCIAS (preferidas) ---
            smart_rsi = data.get("smart_rsi_div", "none")
            smart_macd = data.get("smart_macd_div", "none")
            conf = float(data.get("smart_confidence", 0.0))

            # --- LEGACY BACKUP ---
            legacy_rsi = data.get("rsi_div")
            legacy_macd = data.get("macd_div")

            # === RSI ===
            if smart_rsi != "none":
                if conf >= best_conf:
                    best_conf = conf
                    best_rsi_text = f"{'Alcista' if smart_rsi=='bullish' else 'Bajista'} ({tf})"
            elif legacy_rsi and legacy_rsi not in ["None", None, "Ninguna"]:
                best_rsi_text = f"{legacy_rsi} ({tf})"

            # === MACD ===
            if smart_macd != "none":
                if conf >= best_conf:
                    best_conf = conf
                    best_macd_text = f"{'Alcista' if smart_macd=='bullish' else 'Bajista'} ({tf})"
            elif legacy_macd and legacy_macd not in ["None", None, "Ninguna"]:
                best_macd_text = f"{legacy_macd} ({tf})"

            # === Volumen / volatilidad ===
            atr_rel = float(data.get("atr_rel", 0))
            if atr_rel > 0.02:
                results["Volumen"] = f"Alta volatilidad ({tf})"

        # Aplicar resultados
        if best_rsi_text:
            results["RSI"] = best_rsi_text

        if best_macd_text:
            results["MACD"] = best_macd_text

        return results

    except Exception as e:
        logger.error(f"❌ Error detectando divergencias en {symbol}: {e}")
        return {"RSI": "Error", "MACD": "Error", "Volumen": "Error"}

