"""
trend_analysis.py
Combina indicadores + divergencias para producir:
- match_ratio (0..1)
- recommendation: ENTRADA | ENTRADA_CON_PRECAUCION | ESPERAR | DESCARTAR
"""

import logging
from typing import Dict
from divergence_detector import evaluate_divergences

logger = logging.getLogger("trend_analysis")

# Umbrales y penalizaciones
MIN_MATCH_TO_ENTER = 0.50
MIN_MATCH_TO_CAUTION = 0.33
PRICE_MOVE_THRESHOLD = 0.003  # 0.3%
VOLATILITY_PENALTY = 0.15     # penalización total si atr_rel/bb_width son altos

def _score_tf(ind: Dict, signal_direction: str) -> float:
    """
    Calcula un score 0..1 por timeframe usando valores actuales:
    - EMA short vs long
    - sesgo RSI
    - histograma MACD
    """
    s = 0.0
    try:
        es = ind.get("ema_short_value")
        el = ind.get("ema_long_value")
        if es is not None and el is not None:
            if es > el and signal_direction == "long":
                s += 0.35
            elif es < el and signal_direction == "short":
                s += 0.35
    except Exception:
        pass

    r = ind.get("rsi_value")
    if r is not None:
        if signal_direction == "long":
            if r > 55: s += 0.20
            elif r > 50: s += 0.10
        else:
            if r < 45: s += 0.20
            elif r < 50: s += 0.10

    mh = ind.get("macd_hist_value")
    if mh is not None:
        if signal_direction == "long" and mh > 0:
            s += 0.25
        elif signal_direction == "short" and mh < 0:
            s += 0.25

    return max(0.0, min(1.0, s))


def _basic_match(indicators_by_tf: Dict[str, Dict], signal_direction: str) -> float:
    if not indicators_by_tf:
        return 0.0
    scores = []
    for tf, ind in indicators_by_tf.items():
        scores.append(_score_tf(ind, signal_direction))
    return sum(scores) / len(scores)


def _last_price(indicators_by_tf: Dict[str, Dict], primary="1m"):
    # busca último precio
    if primary in indicators_by_tf and "price" in indicators_by_tf[primary]:
        arr = indicators_by_tf[primary]["price"]
        if arr: return float(arr[-1])
    for tf, block in indicators_by_tf.items():
        if "price" in block and block["price"]:
            return float(block["price"][-1])
    return None


def analyze_trend(symbol: str, signal_direction: str, entry_price: float,
                  indicators_by_tf: Dict[str, Dict], leverage: int = 1) -> Dict:
    """
    Retorna:
    {
      'symbol': str,
      'match_ratio': float,
      'recommendation': str,
      'details': {...}
    }
    """
    logger.info(f"[trend] {symbol} {signal_direction} entry={entry_price}")

    basic = _basic_match(indicators_by_tf, signal_direction)

    # Divergencias
    div = evaluate_divergences(indicators_by_tf, signal_direction, leverage=leverage)
    div_imp = float(div.get("confidence_impact", 0.0))

    # Volatilidad (ATR / BandWidth)
    vol_pen = 0.0
    for tf, data in indicators_by_tf.items():
        bbw = data.get("bb_width")
        atr_rel = data.get("atr_rel")
        if bbw is not None and bbw > 0.02:
            vol_pen += VOLATILITY_PENALTY * 0.5
        if atr_rel is not None and atr_rel > 0.02:
            vol_pen += VOLATILITY_PENALTY * 0.5

    # Combinar
    match = max(0.0, min(1.0, basic + div_imp - vol_pen))

    details = {
        "basic_match": basic,
        "divergence_impact": div_imp,
        "vol_penalty": vol_pen,
        "divergences": div.get("divergences", {}),
        "notes": div.get("notes", []),
    }

    # Recomendación inicial
    if match >= MIN_MATCH_TO_ENTER:
        rec = "ENTRADA"
    elif match >= MIN_MATCH_TO_CAUTION:
        # Confirmación por movimiento rápido de precio
        cur = _last_price(indicators_by_tf, "1m")
        details["current_price"] = cur
        if cur is not None:
            if signal_direction == "long" and cur >= entry_price * (1 + PRICE_MOVE_THRESHOLD):
                match = min(1.0, match + 0.15)
                details["price_confirm"] = True
            elif signal_direction == "short" and cur <= entry_price * (1 - PRICE_MOVE_THRESHOLD):
                match = min(1.0, match + 0.15)
                details["price_confirm"] = True
            else:
                details["price_confirm"] = False

        rec = "ENTRADA_CON_PRECAUCION" if match >= MIN_MATCH_TO_ENTER else "ESPERAR"
    else:
        rec = "DESCARTAR"

    # Conservador con alto apalancamiento
    if leverage >= 20 and rec == "ENTRADA" and match < (MIN_MATCH_TO_ENTER + 0.10):
        rec = "ENTRADA_CON_PRECAUCION"

    result = {
        "symbol": symbol,
        "match_ratio": float(match),
        "recommendation": rec,
        "details": details,
    }
    logger.info(f"[trend] result {symbol}: match={match:.3f} rec={rec}")
    return result
