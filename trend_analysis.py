"""
trend_analysis.py (versión optimizada)
-------------------------------------
Evalúa señales multi-temporalidad combinando EMA, RSI, MACD, divergencias y volatilidad.
"""

import logging, numpy as np
from divergence_detector import evaluate_divergences

logger = logging.getLogger("trend_analysis")

MIN_MATCH_TO_ENTER = 0.5
MIN_MATCH_TO_CAUTION = 0.33
VOLATILITY_PENALTY = 0.15
TF_VOL_FACTORS = {"1m": 0.5, "5m": 0.8, "15m": 1.0, "30m": 1.2}
RAPID_REEVAL_WINDOW = 3

def _compute_basic_match(indicators_by_tf, signal_direction):
    scores = []
    for tf, ind in indicators_by_tf.items():
        s = 0.0
        ema_s, ema_l = ind.get("ema_short"), ind.get("ema_long")
        if ema_s and ema_l:
            if ema_s > ema_l and signal_direction == "long": s += 0.35
            elif ema_s < ema_l and signal_direction == "short": s += 0.35

        rsi = ind.get("rsi")
        if rsi:
            if signal_direction == "long":
                if rsi > 55: s += 0.2
                elif rsi > 50: s += 0.1
            else:
                if rsi < 45: s += 0.2
                elif rsi < 50: s += 0.1

        macd_hist = ind.get("macd_hist")
        if macd_hist:
            if signal_direction == "long" and macd_hist > 0: s += 0.25
            elif signal_direction == "short" and macd_hist < 0: s += 0.25

        s = max(0.0, min(1.0, s))
        scores.append(s)
    return np.mean(scores) if scores else 0.0

def analyze_trend(symbol, signal_direction, entry_price, indicators_by_tf, leverage=1):
    logger.info(f"trend_analysis: analyzing {symbol} {signal_direction} entry={entry_price}")
    basic = _compute_basic_match(indicators_by_tf, signal_direction)
    divs = evaluate_divergences(indicators_by_tf, signal_direction, leverage)
    div_impact = divs["confidence_impact"]

    # 🧠 Mejora aplicada: volatilidad por TF
    vol_pen = 0
    for tf, ind in indicators_by_tf.items():
        atr_rel = ind.get("atr_rel", 0)
        bbw = ind.get("bb_width", 0)
        if atr_rel > 0.02:
            vol_pen += VOLATILITY_PENALTY * (atr_rel / TF_VOL_FACTORS.get(tf, 1))
        if bbw > 0.02:
            vol_pen += VOLATILITY_PENALTY * 0.5

    match = basic + div_impact - vol_pen
    match = max(0.0, min(1.0, match))

    # 🧠 Mejora aplicada: momentum RSI/MACD
    for tf, ind in indicators_by_tf.items():
        if "rsi_series" in ind and "macd_line" in ind:
            try:
                rsi_slope = np.sign(ind["rsi_series"][-1] - ind["rsi_series"][-4])
                macd_slope = np.sign(ind["macd_line"][-1] - ind["macd_line"][-4])
                if (signal_direction == "long" and (rsi_slope < 0 or macd_slope < 0)) or \
                   (signal_direction == "short" and (rsi_slope > 0 or macd_slope > 0)):
                    match -= 0.1
                    logger.debug(f"{tf}: penalizado por momentum decreciente")
            except Exception:
                pass

    # 🧠 Mejora aplicada: confirmación dinámica según ATR
    atr_avg = np.mean([ind.get("atr_rel", 0) for ind in indicators_by_tf.values()]) or 0.02
    PRICE_MOVE_THRESHOLD = max(0.003, atr_avg * 1.5)

    if match >= MIN_MATCH_TO_ENTER: rec = "ENTRADA"
    elif match >= MIN_MATCH_TO_CAUTION: rec = "ENTRADA_CON_PRECAUCION"
    else: rec = "DESCARTAR"

    if leverage >= 20 and rec == "ENTRADA" and match < 0.65:
        rec = "ENTRADA_CON_PRECAUCION"

    return {
        "symbol": symbol,
        "match_ratio": float(match),
        "recommendation": rec,
        "details": {
            "basic_match": basic,
            "div_impact": div_impact,
            "vol_penalty": vol_pen,
            "momentum_applied": True,
            "PRICE_MOVE_THRESHOLD": PRICE_MOVE_THRESHOLD,
            "recommendation": rec,
        },
    }
