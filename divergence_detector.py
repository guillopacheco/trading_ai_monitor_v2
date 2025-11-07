"""
divergence_detector.py
Detección simple de divergencias RSI / MACD por ventana.
Devuelve impacto agregado para sumar/restar a la confianza.
"""

import logging
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("divergence_detector")

LOOKBACK = 30  # velas revisadas por TF

def _as_series(arr) -> pd.Series:
    if isinstance(arr, pd.Series):
        return arr
    return pd.Series(list(arr))

def _divergence(price: pd.Series, indicator: pd.Series) -> Tuple[Optional[str], float]:
    """
    Regla simple:
    - Bullish: precio hace mínimos descendentes y el indicador hace mínimos ascendentes
    - Bearish: precio hace máximos ascendentes y el indicador hace máximos descendentes
    Strength ~ (1 - |corr|) para premiar desacople.
    """
    if len(price) < 5 or len(indicator) < 5:
        return None, 0.0

    p = price.dropna()
    i = indicator.dropna()
    n = min(len(p), len(i))
    if n < 5:
        return None, 0.0

    p = p.iloc[-LOOKBACK:]
    i = i.iloc[-LOOKBACK:]

    # extremos
    p_low1 = p.iloc[: len(p)//2].min()
    p_low2 = p.iloc[len(p)//2 :].min()
    i_low1 = i.iloc[: len(i)//2].min()
    i_low2 = i.iloc[len(i)//2 :].min()

    p_high1 = p.iloc[: len(p)//2].max()
    p_high2 = p.iloc[len(p)//2 :].max()
    i_high1 = i.iloc[: len(i)//2].max()
    i_high2 = i.iloc[len(i)//2 :].max()

    bull = (p_low2 < p_low1) and (i_low2 > i_low1)
    bear = (p_high2 > p_high1) and (i_high2 < i_high1)

    corr = p.corr(i)
    corr = 0 if pd.isna(corr) else corr
    strength = max(0.0, min(1.0, 1 - abs(corr)))

    if bull:
        return "bullish", strength
    if bear:
        return "bearish", strength
    return None, 0.0


def evaluate_divergences(data_by_tf: Dict, signal_direction: str, leverage: int = 1) -> Dict:
    """
    data_by_tf: dict por TF con:
      'price' (lista/serie), 'rsi_series', 'macd_line_series', 'volume' (opcional)
    """
    tf_weights = {"1m": 0.45, "5m": 0.30, "15m": 0.25, "30m": 0.20, "1h": 0.15}
    divergences = {}
    notes = []
    total = 0.0

    for tf, data in data_by_tf.items():
        price = _as_series(data.get("price", []))
        rsi_s = _as_series(data.get("rsi_series", []))
        macd_s = _as_series(data.get("macd_line_series", []))
        vol = _as_series(data.get("volume", []))
        w = tf_weights.get(tf, 0.1)

        r_div, r_str = _divergence(price, rsi_s)
        m_div, m_str = _divergence(price, macd_s)

        divergences[tf] = {
            "rsi": {"type": r_div, "strength": float(r_str)},
            "macd": {"type": m_div, "strength": float(m_str)},
            "volume_mean": float(np.mean(vol)) if len(vol) else 0.0,
        }

        impact = 0.0
        # apoyo a la señal
        def supports(div_type: str) -> bool:
            return ((signal_direction == "long" and div_type == "bullish") or
                    (signal_direction == "short" and div_type == "bearish"))

        if r_div and m_div and r_div == m_div:
            if supports(r_div):
                impact += 0.25 * w * (r_str + m_str) / 2
                notes.append(f"{tf}: divergencia RSI+MACD a favor ({r_div})")
            else:
                impact -= 0.10 * w * (r_str + m_str) / 2
                notes.append(f"{tf}: divergencia RSI+MACD en contra ({r_div})")
        else:
            if r_div:
                if supports(r_div):
                    impact += 0.18 * w * r_str
                    notes.append(f"{tf}: RSI a favor ({r_div})")
                else:
                    impact -= 0.10 * w * r_str
                    notes.append(f"{tf}: RSI en contra ({r_div})")
            if m_div:
                if supports(m_div):
                    impact += 0.18 * w * m_str
                    notes.append(f"{tf}: MACD a favor ({m_div})")
                else:
                    impact -= 0.10 * w * m_str
                    notes.append(f"{tf}: MACD en contra ({m_div})")

        # volumen realza el peso de la divergencia
        vol_mean = divergences[tf]["volume_mean"]
        vol_ratio = vol_mean / (1 + vol_mean)
        if (r_div or m_div) and vol_ratio > 0.2:
            impact *= (1 + 0.3 * vol_ratio)
            notes.append(f"{tf}: volumen refuerza (ratio {vol_ratio:.2f})")

        total += impact

    if leverage >= 20:
        total *= 0.9

    total = max(-1.0, min(1.0, total))
    logger.info(f"[divergence] impacto total={total:.3f}")
    return {"divergences": divergences, "confidence_impact": float(total), "notes": notes}
