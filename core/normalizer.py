"""
normalizer.py
-----------------------------------------
Normalización estándar para el Motor Técnico A+.
Convierte valores crudos de indicadores en una escala
coherente de 0–100 para cálculo de score y match_ratio.
"""

import numpy as np


# ================================================================
# 📌 UTILIDAD BASE
# ================================================================
def _clip(value, min_v=0, max_v=100):
    """Asegura que un valor esté dentro del rango 0-100."""
    try:
        return float(np.clip(value, min_v, max_v))
    except:
        return 50.0


# ================================================================
# 📈 1. TREND NORMALIZER
# ================================================================
def normalize_trend(trend_score):
    """
    Recibe trend_score crudo (generalmente -1.0 a +1.0)
    Devuelve un valor entre 0 y 100:
        0   = tendencia fuertemente bajista
        50  = neutral
        100 = tendencia fuertemente alcista
    """
    if trend_score is None:
        return 50

    norm = (trend_score + 1) * 50  # convierte -1→0, 0→50, 1→100
    return _clip(norm)


# ================================================================
# ⚡ 2. MOMENTUM NORMALIZER
# ================================================================
def normalize_momentum(momentum):
    """
    momentum esperado en escala:
      - fuerte negativa: -50
      - neutral: 0
      - fuerte positiva: +50
    """
    if momentum is None:
        return 50

    norm = 50 + momentum  # neutral = 50
    return _clip(norm)


# ================================================================
# ⚠ 3. DIVERGENCE NORMALIZER
# ================================================================
def normalize_divergence(divergence_signal):
    """
    divergence_signal: puede ser string o dict.
    Valores esperados:
        'none' / None → 50
        'bullish_weak' → 60
        'bullish_strong' → 80
        'bearish_weak' → 40
        'bearish_strong' → 20
    """
    if divergence_signal is None or divergence_signal == "none":
        return 50

    mapping = {
        "bullish_weak": 60,
        "bullish_strong": 80,
        "bearish_weak": 40,
        "bearish_strong": 20,
    }

    if isinstance(divergence_signal, dict):
        divergence_signal = divergence_signal.get("type", None)

    return mapping.get(divergence_signal, 50)


# ================================================================
# 🏛 4. STRUCTURE NORMALIZER (Market Structure)
# ================================================================
def normalize_structure(structure):
    """
    structure puede ser:
        'bullish', 'bearish', 'range', 'breakout', etc.
    """
    mapping = {
        "bullish": 75,
        "bearish": 25,
        "range": 50,
        "neutral": 50,
        "breakout_bull": 85,
        "breakout_bear": 15,
        "choppy": 45,
        "unknown": 50,
    }
    return mapping.get(structure, 50)


# ================================================================
# 🌪 5. VOLATILITY NORMALIZER (ATR / rango)
# ================================================================
def normalize_volatility(atr_percentage):
    """
    atr_percentage: ATR como % del precio.
    Rango recomendado:
        bajo: <1%
        medio: 1–3%
        alto: >3%

    Normalización:
        baja  → 70 (favorable)
        media → 50
        alta  → 30 (riesgoso)
    """
    if atr_percentage is None:
        return 50

    if atr_percentage < 1:
        return 70
    if atr_percentage < 3:
        return 50
    return 30


# ================================================================
# 🕒 6. MICRO-STRUCTURE NORMALIZER (1M/5M)
# ================================================================
def normalize_micro(micro_score):
    """
    micro_score puede venir entre -1 y +1.

    -1 → 0
     0 → 50
    +1 → 100
    """
    if micro_score is None:
        return 50

    return _clip((micro_score + 1) * 50)


# ================================================================
# 🎯 7. RISK CLASS NORMALIZER
# ================================================================
def normalize_risk(risk_factor):
    """
    risk_factor en escala:
        0 = riesgo mínimo
        1 = riesgo neutral
        2 = riesgo elevado
    """
    mapping = {
        0: 80,
        1: 50,
        2: 30,
    }
    return mapping.get(risk_factor, 50)


# ================================================================
# ⚖ 8. TF WEIGHT NORMALIZER
# ================================================================
def normalize_tf_weights(tf_score_dict):
    """
    tf_score_dict ejemplo:
        { "4H": 80, "1H": 70, "15M": 60 }
    Devuelve el promedio ponderado
    """
    if not tf_score_dict:
        return 50

    pesos = {
        "4H": 0.45,
        "1H": 0.35,
        "15M": 0.20,
    }

    total = 0
    for tf, val in tf_score_dict.items():
        p = pesos.get(tf, 0.10)
        total += val * p

    return _clip(total)
