"""
smart_divergences.py
Detección simplificada de divergencias RSI / MACD para uso en TechnicalEngine.
"""

import logging
import numpy as np

logger = logging.getLogger("divergences")


def _detect_rsi_divergence(rsi_series: list, price_series: list) -> str:
    """
    Detecta divergencia alcista o bajista básica usando últimos 3 pivotes.
    """

    if len(rsi_series) < 3 or len(price_series) < 3:
        return "ninguna"

    r1, r2 = rsi_series[-3], rsi_series[-1]
    p1, p2 = price_series[-3], price_series[-1]

    # Divergencia alcista: precio hace mínimo más bajo, RSI hace mínimo más alto
    if p2 < p1 and r2 > r1:
        return "alcista"

    # Divergencia bajista: precio hace máximo más alto, RSI hace máximo más bajo
    if p2 > p1 and r2 < r1:
        return "bajista"

    return "ninguna"


def _detect_macd_divergence(macd_series: list, price_series: list) -> str:
    """
    Divergencia básica MACD vs precio.
    """

    if len(macd_series) < 3 or len(price_series) < 3:
        return "ninguna"

    m1, m2 = macd_series[-3], macd_series[-1]
    p1, p2 = price_series[-3], price_series[-1]

    # Alcista: precio baja, MACD sube
    if p2 < p1 and m2 > m1:
        return "alcista"

    # Bajista: precio sube, MACD baja
    if p2 > p1 and m2 < m1:
        return "bajista"

    return "ninguna"


def detect_divergences(rsi_series, macd_hist_series, close_series) -> dict:
    """
    Función principal usada por TechnicalEngine.

    Devuelve:
    {
        "RSI": "alcista/bajista/ninguna",
        "MACD": "alcista/bajista/ninguna"
    }
    """

    try:
        rsi_div = _detect_rsi_divergence(rsi_series, close_series)
        macd_div = _detect_macd_divergence(macd_hist_series, close_series)

        return {
            "RSI": rsi_div,
            "MACD": macd_div,
        }

    except Exception as e:
        logger.exception(f"❌ Error detectando divergencias: {e}")
        return {
            "RSI": "ninguna",
            "MACD": "ninguna",
        }
