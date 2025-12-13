"""
trend_system_final.py — Trend Engine 3.0
Evalúa tendencias multi-TF sin depender del motor completo.
"""

import logging

logger = logging.getLogger("trend_system")


def evaluate_trend_single_tf(tf_snapshot: dict) -> dict:
    """
    Evalúa una sola temporalidad y asigna:
    - trend_code_value  (numérico)
    - trend_label
    - votes_bull / votes_bear
    """

    ema_short = tf_snapshot.get("ema_short")
    ema_long = tf_snapshot.get("ema_long")
    rsi = tf_snapshot.get("rsi", 50)
    macd_hist = tf_snapshot.get("macd_hist", 0)

    votes_bull = 0
    votes_bear = 0

    # EMA crossover
    if ema_short > ema_long:
        votes_bull += 2
    else:
        votes_bear += 2

    # RSI bias
    if rsi > 55:
        votes_bull += 1
    elif rsi < 45:
        votes_bear += 1

    # MACD bias
    if macd_hist > 0:
        votes_bull += 1
    else:
        votes_bear += 1

    # Trend code final
    if votes_bull >= 4:
        trend_code = 2
        trend_label = "Fuerte alcista"
    elif votes_bull == 3:
        trend_code = 1
        trend_label = "Alcista"
    elif votes_bear == 3:
        trend_code = -1
        trend_label = "Bajista"
    else:
        trend_code = -2
        trend_label = "Fuerte bajista"

    tf_snapshot.update(
        {
            "votes_bull": votes_bull,
            "votes_bear": votes_bear,
            "trend_code": trend_code,
            "trend_label": trend_label,
        }
    )

    return tf_snapshot


def evaluate_major_trend(timeframes: list) -> dict:
    """
    Recibe lista de snapshots TF ya evaluados.
    Produce la tendencia mayor → usada por TechnicalEngine.
    """

    total = 0
    for tf in timeframes:
        total += tf.get("trend_code", 0)

    if total >= 4:
        code = 2
        label = "Fuerte alcista"
    elif total >= 1:
        code = 1
        label = "Alcista"
    elif total <= -4:
        code = -2
        label = "Fuerte bajista"
    elif total <= -1:
        code = -1
        label = "Bajista"
    else:
        code = 0
        label = "Neutral"

    return {
        "major_trend_code": label,
        "trend_code_value": code,
        "trend_label": label,
    }
