"""
divergence_detector.py - VERSIÓN CHATGPT ADAPTADA
Detecta divergencias RSI/MACD con el enfoque mejorado de ChatGPT
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# parámetros ajustables
LOOKBACK = 12       # velas para comparar puntos altos/bajos en divergencia
MIN_CONF = 0.0
MAX_CONF = 1.0

def _peak_trough(series: pd.Series):
    """Devuelve índice del máximo y mínimo en la ventana."""
    return series.idxmax(), series.idxmin()

def detect_divergence_for_indicator(price: pd.Series, indicator: pd.Series, lookback=LOOKBACK):
    """
    Detecta una divergencia simple en la ventana 'lookback'.
    Retorna 'bullish', 'bearish' o None y una medida de fuerza (0..1).
    """
    if len(price) < lookback or len(indicator) < lookback:
        return None, 0.0

    recent_price = price[-lookback:]
    recent_ind = indicator[-lookback:]

    p_high_idx, p_low_idx = _peak_trough(recent_price)
    i_high_idx, i_low_idx = _peak_trough(recent_ind)

    # comparaciones directas
    price_movement = recent_price.iloc[-1] - recent_price.iloc[0]
    ind_movement = recent_ind.iloc[-1] - recent_ind.iloc[0]

    # detect simple divergence by comparing successive extremes
    # bullish divergence: price makes lower low while indicator makes higher low
    # bearish divergence: price makes higher high while indicator makes lower high
    try:
        price_high = recent_price.max()
        price_low = recent_price.min()
        ind_high = recent_ind.max()
        ind_low = recent_ind.min()
    except Exception:
        return None, 0.0

    # Compute simple strength measure (normalized)
    # Use correlation as proxy of agreement (low correlation -> possible divergence)
    corr = recent_price.corr(recent_ind)
    corr = 0 if pd.isna(corr) else corr

    strength = max(0.0, min(1.0, 1 - abs(corr)))  # if corr near 0 -> higher strength

    # conditions
    # bullish: price_low occurs later and is lower, but indicator low is higher
    if (recent_price.idxmin() >= recent_price.idxmin() and price_low < recent_price.iloc[0]) and (ind_low > recent_ind.iloc[0]):
        return "bullish", strength
    # bearish: price_high > earlier high, indicator high lower
    if (price_high > recent_price.iloc[0]) and (ind_high < recent_ind.iloc[0]):
        return "bearish", strength

    return None, 0.0

def evaluate_divergences(data_by_tf: dict, signal_direction: str, leverage: int = 1):
    """
    data_by_tf: dict of timeframe -> dict with keys 'price', 'rsi', 'macd', 'volume'
    signal_direction: 'LONG' or 'SHORT' (adaptado para tu sistema)
    leverage: numeric
    Returns:
        summary: {
           'divergences': {tf: {'rsi': (...), 'macd': (...)}},
           'confidence_impact': float (-1..+1),
           'notes': [...]
        }
    """
    divergences = {}
    notes = []
    total_impact = 0.0

    # weights: give more importancia a lower TF for intraday signals
    tf_weight_map = {
        "1": 0.45,   # 1m
        "5": 0.30,   # 5m  
        "15": 0.25,  # 15m
        "60": 0.15,  # 1h
        "240": 0.10, # 4h
        "1440": 0.05 # 1d
    }

    for tf, data in data_by_tf.items():
        # Para datos simples (solo punto actual), usar enfoque simplificado
        if not isinstance(data, dict):
            continue
            
        # Crear series simples para el análisis
        price_value = data.get('close_price', 0)
        rsi_value = data.get('rsi', 50)
        macd_value = data.get('macd_hist', 0)
        
        price = pd.Series([price_value, price_value * 0.99])  # Pequeña variación
        rsi = pd.Series([rsi_value, rsi_value])
        macd_line = pd.Series([macd_value, macd_value])

        # Usar timeframe numérico para pesos
        tf_numeric = tf.replace('tf_', '').replace('m', '')
        tf_weight = tf_weight_map.get(tf_numeric, 0.1)

        rsi_div, rsi_strength = detect_divergence_for_indicator(price, rsi)
        macd_div, macd_strength = detect_divergence_for_indicator(price, macd_line)

        divergences[tf] = {
            "rsi": {"type": rsi_div, "strength": float(rsi_strength)},
            "macd": {"type": macd_div, "strength": float(macd_strength)},
        }

        # compute impact per tf: divergences that *support* the signal add positive,
        # those that are contrary subtract but less (reduced penalty).
        impact = 0.0

        # prefer MACD + RSI agreement
        if rsi_div and macd_div and rsi_div == macd_div:
            # reinforce agreement
            if (signal_direction == "LONG" and rsi_div == "bullish") or (signal_direction == "SHORT" and rsi_div == "bearish"):
                impact += 0.25 * tf_weight * (rsi_strength + macd_strength) / 2
                notes.append(f"{tf}: divergence BOTH support ({rsi_div})")
            else:
                # less penalty if contrary
                impact -= 0.10 * tf_weight * (rsi_strength + macd_strength) / 2
                notes.append(f"{tf}: divergence BOTH contrary ({rsi_div}) - reduced penalty")
        else:
            # single indicator cases
            if rsi_div:
                if (signal_direction == "LONG" and rsi_div == "bullish") or (signal_direction == "SHORT" and rsi_div == "bearish"):
                    impact += 0.18 * tf_weight * rsi_strength
                    notes.append(f"{tf}: RSI supports ({rsi_div})")
                else:
                    impact -= 0.10 * tf_weight * rsi_strength
                    notes.append(f"{tf}: RSI contrary ({rsi_div}) - reduced penalty")
            if macd_div:
                if (signal_direction == "LONG" and macd_div == "bullish") or (signal_direction == "SHORT" and macd_div == "bearish"):
                    impact += 0.18 * tf_weight * macd_strength
                    notes.append(f"{tf}: MACD supports ({macd_div})")
                else:
                    impact -= 0.10 * tf_weight * macd_strength
                    notes.append(f"{tf}: MACD contrary ({macd_div}) - reduced penalty")

        total_impact += impact

    # adjust for leverage: higher leverage => require slightly stricter (reduce positive impact)
    if leverage >= 20:
        total_impact *= 0.9  # slightly reduce positive impact to be more conservative

    # cap
    total_impact = max(-1.0, min(1.0, total_impact))

    logger.info(f"divergence_detector: total_impact={total_impact:.4f}, notes={notes}")
    return {
        "divergences": divergences,
        "confidence_impact": float(total_impact),
        "notes": notes
    }

# Clase wrapper para mantener compatibilidad con tu código
class DivergenceDetector:
    def __init__(self):
        pass
    
    def analyze_divergences(self, symbol: str, timeframe_analysis: Dict) -> List:
        """
        Wrapper para mantener compatibilidad con tu código existente
        Retorna lista vacía ya que ChatGPT maneja divergencias internamente
        """
        return []  # ChatGPT maneja divergencias en trend_analysis

# Instancia global para compatibilidad
divergence_detector = DivergenceDetector()