# =====================================================================
# normalizers.py
# ---------------------------------------------------------------
# Normalización de señales técnicas para consolidar multi-TF.
# Genera valores entre 0 y 1 usados para el Motor Técnico A+.
# =====================================================================

def normalize_trend(trend: str) -> float:
    """
    Convierte tendencia textual en score numérico 0–1.
    """
    if trend is None:
        return 0.5

    t = trend.lower()

    if t in ("strong_up", "very_bullish", "bullish_strong"):
        return 1.0
    if t in ("up", "bullish", "slightly_up"):
        return 0.8
    if t in ("sideways", "neutral"):
        return 0.5
    if t in ("down", "bearish"):
        return 0.25
    if t in ("strong_down", "very_bearish", "bearish_strong"):
        return 0.0

    return 0.5


def normalize_rsi(rsi: float) -> float:
    """
    RSI 0–100 → 0–1 híbrido con sobrecompra/sobreventa.
    """
    if rsi is None:
        return 0.5

    # Zonas dinámicas
    if rsi < 30:
        return 0.2
    if rsi > 70:
        return 0.8

    # Normalización lineal
    return (rsi - 20) / 60  # 20–80 → 0–1


def normalize_macd_hist(hist: float) -> float:
    """
    MACD histogram → 0–1
    """
    if hist is None:
        return 0.5

    # Saturación suave
    if hist > 0.01:
        return 0.9
    if hist < -0.01:
        return 0.1

    # Valores cercanos a neutro
    return 0.5 + (hist * 25)  # pequeño rango


def normalize_volatility(atr_pct: float) -> float:
    """
    ATR% → score estabilidad.
    """
    if atr_pct is None:
        return 0.5

    if atr_pct < 1.0:
        return 0.8
    if atr_pct < 2.0:
        return 0.6
    if atr_pct < 3.0:
        return 0.5
    if atr_pct < 5.0:
        return 0.3

    return 0.15


def normalize_divergence(div: str) -> float:
    """
    divergencia → 0–1
    """
    if div is None:
        return 0.5

    d = div.lower()
    if d == "bullish":
        return 0.8
    if d == "bearish":
        return 0.2
    if d == "hidden_bullish":
        return 0.7
    if d == "hidden_bearish":
        return 0.3

    return 0.5


def merge_block_scores(scores: dict) -> float:
    """
    Combina los valores normalizados de un bloque (1 TF).
    Bloque = tendencia + rsi + macd + volatilidad + divergencia.
    """
    s = [
        scores.get("trend", 0.5),
        scores.get("rsi", 0.5),
        scores.get("macd", 0.5),
        scores.get("volatility", 0.5),
        scores.get("divergence", 0.5),
    ]
    return sum(s) / len(s)


def merge_multi_tf(blocks: dict) -> float:
    """
    Promedia varios TF en un score global.
    """
    if not blocks:
        return 0.5

    vals = [v.get("score", 0.5) for v in blocks.values()]
    return sum(vals) / len(vals)
