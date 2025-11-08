"""
divergence_detector.py (versión optimizada)
-------------------------------------------
Detecta divergencias RSI/MACD/Volumen con ponderación dinámica por temporalidad.
Compatible con trend_analysis.py y signal_manager.py
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("divergence_detector")

# ================================================================
# 🧠 Configuración dinámica
# ================================================================
LOOKBACKS = {"1m": 30, "5m": 25, "15m": 20, "30m": 15, "1h": 12}
tf_weights = {"1m": 0.25, "5m": 0.35, "15m": 0.25, "30m": 0.10, "1h": 0.05}

def _peak_trough(series: pd.Series):
    return series.idxmax(), series.idxmin()

def detect_divergence_for_indicator(price: pd.Series, indicator: pd.Series, lookback: int):
    """Detecta divergencia simple (bullish/bearish)"""
    if len(price) < lookback or len(indicator) < lookback:
        return None, 0.0
    recent_p, recent_i = price[-lookback:], indicator[-lookback:]

    try:
        corr = recent_p.corr(recent_i)
        strength = max(0.0, min(1.0, 1 - abs(corr)))
        price_low, price_high = recent_p.min(), recent_p.max()
        ind_low, ind_high = recent_i.min(), recent_i.max()

        if price_low < recent_p.iloc[0] and ind_low > recent_i.iloc[0]:
            return "bullish", strength
        if price_high > recent_p.iloc[0] and ind_high < recent_i.iloc[0]:
            return "bearish", strength
    except Exception:
        return None, 0.0

    return None, 0.0

def evaluate_divergences(data_by_tf: dict, signal_direction: str, leverage: int = 1):
    divergences, notes = {}, []
    total_impact = 0.0

    for tf, data in data_by_tf.items():
        lookback = LOOKBACKS.get(tf, 20)
        price = pd.Series(data["price"])
        rsi = pd.Series(data.get("rsi", np.zeros(len(price))))
        macd = pd.Series(data.get("macd_line", data.get("macd", np.zeros(len(price)))))
        vol = pd.Series(data.get("volume", np.zeros(len(price))))

        tf_weight = tf_weights.get(tf, 0.1)
        rsi_div, rsi_s = detect_divergence_for_indicator(price, rsi, lookback)
        macd_div, macd_s = detect_divergence_for_indicator(price, macd, lookback)

        # 🧠 Mejora aplicada: detección de divergencia de volumen
        vol_div = None
        if price.iloc[-1] > price.iloc[0] and vol.iloc[-1] < vol.iloc[0]:
            vol_div = "bearish"
        elif price.iloc[-1] < price.iloc[0] and vol.iloc[-1] < vol.iloc[0]:
            vol_div = "bullish"

        divergences[tf] = {
            "rsi": {"type": rsi_div, "strength": rsi_s},
            "macd": {"type": macd_div, "strength": macd_s},
            "volume_div": vol_div,
        }

        impact = 0.0
        for ind, (div, s) in {"RSI": (rsi_div, rsi_s), "MACD": (macd_div, macd_s)}.items():
            if not div:
                continue
            same = (signal_direction == "long" and div == "bullish") or (signal_direction == "short" and div == "bearish")
            factor = 0.2 if same else -0.1
            impact += factor * tf_weight * s
            notes.append(f"{tf}: {ind} {'support' if same else 'contrary'} ({div})")

        # Volumen divergente amplifica el impacto
        if vol_div:
            if (vol_div == "bullish" and signal_direction == "long") or (vol_div == "bearish" and signal_direction == "short"):
                impact *= 1.2
                notes.append(f"{tf}: Volume divergence aligns ({vol_div})")

        total_impact += impact

    # Ajuste por apalancamiento
    if leverage >= 20:
        total_impact *= 0.9

    total_impact = max(-1.0, min(1.0, total_impact))
    logger.info(f"divergence_detector: total_impact={total_impact:.3f}")
    return {"divergences": divergences, "confidence_impact": total_impact, "notes": notes}
