"""
divergence_detector.py (versión mejorada)
----------------------------------------
Detecta divergencias RSI/MACD y volumen.
Pondera por temporalidad y tipo de divergencia.
"""

import numpy as np
import logging

logger = logging.getLogger("divergence_detector")

# Pesos y lookbacks por temporalidad
TF_WEIGHTS = {"1m": 0.25, "5m": 0.35, "15m": 0.25, "30m": 0.10, "1h": 0.05}
LOOKBACKS = {"1m": 30, "5m": 25, "15m": 20, "30m": 15, "1h": 10}


# ================================================================
# 🧩 Detección de divergencias
# ================================================================
def detect_divergences(symbol, ind, tf, direction):
    """
    Analiza divergencias RSI/MACD/volumen.
    Devuelve un factor [-1, +1] que afecta el score total.
    """
    try:
        rsi_series = ind.get("rsi_series", [])
        macd_series = ind.get("macd_series", [])
        prices = ind.get("price", [])
        volumes = ind.get("volume", [])

        lookback = LOOKBACKS.get(tf, 20)
        weight = TF_WEIGHTS.get(tf, 0.2)

        if len(rsi_series) < 5 or len(macd_series) < 5:
            return 0

        # --- RSI Divergencia ---
        rsi_diff = np.diff(rsi_series[-lookback:])
        price_diff = np.diff(prices[-lookback:]) if isinstance(prices, list) else []

        if len(price_diff) > 3:
            if direction == "long" and rsi_diff[-1] > 0 and price_diff[-1] < 0:
                rsi_div = +1
            elif direction == "short" and rsi_diff[-1] < 0 and price_diff[-1] > 0:
                rsi_div = +1
            else:
                rsi_div = -0.5
        else:
            rsi_div = 0

        # --- MACD Divergencia ---
        macd_diff = np.diff(macd_series[-lookback:])
        if len(macd_diff) > 3:
            if direction == "long" and macd_diff[-1] > 0 and price_diff[-1] < 0:
                macd_div = +1
            elif direction == "short" and macd_diff[-1] < 0 and price_diff[-1] > 0:
                macd_div = +1
            else:
                macd_div = -0.5
        else:
            macd_div = 0

        # --- Divergencia de volumen ---
        vol_div = 0
        if len(volumes) > 5:
            vol_diff = np.diff(volumes[-lookback:])
            if price_diff[-1] > 0 and vol_diff[-1] < 0:
                vol_div = -0.5  # sube con volumen débil → bajista
            elif price_diff[-1] < 0 and vol_diff[-1] < 0:
                vol_div = +0.5  # cae con volumen débil → alcista

        # --- Consolidar ---
        divergence_score = (rsi_div + macd_div + vol_div) / 3
        divergence_score *= weight

        return np.clip(divergence_score, -1, 1)

    except Exception as e:
        logger.error(f"❌ Error detectando divergencias para {symbol} ({tf}): {e}")
        return 0
