"""
signal_engine.py
----------------
Motor técnico unificado para análisis de señales, reactivación
y monitoreo de posiciones.

Este motor es completamente independiente de Telegram, DB y Bybit.
Todos los accesos externos deben hacerse vía servicios.

Estructura del resultado estándar:

{
    "symbol": "BTCUSDT",
    "direction": "long",
    "timeframes": {
        "1h": { ... },
        "4h": { ... },
        "1d": { ... }
    },
    "trend_score": 0–100,
    "match_ratio": 0–100,
    "grade": "A" / "B" / "C" / "D",
    "divergences": { ... },
    "decision": "enter" | "wait" | "skip" | "reversal-risk",
    "allowed": True/False,
    "summary": "texto corto profesional",
    "details": "versión larga para logs o Telegram"
}
"""

import logging
import numpy as np

from services.bybit_service import (
    fetch_ohlcv,
    fetch_price,
)

logger = logging.getLogger("signal_engine")


# ============================================================
# 🔵 CONFIGURACIÓN DEL MOTOR
# ============================================================
DEFAULT_TIMEFRAMES = ["1h", "4h", "1d"]

GRADE_THRESHOLDS = {
    "A": 80,
    "B": 65,
    "C": 50,
    "D": 0,
}

DECISION_THRESHOLDS = {
    "enter": 70,
    "wait": 50,
    "skip": 0,
}


# ============================================================
# 🔵 UTILIDADES INTERNAS
# ============================================================
def _calc_trend(df):
    """
    Calcula una tendencia simple usando pendiente del cierre.
    """
    closes = df["close"].astype(float).values[-20:]

    if len(closes) < 5:
        return {"trend": "neutral", "score": 50}

    # Cálculo de pendiente lineal
    x = np.arange(len(closes))
    slope = np.polyfit(x, closes, 1)[0]

    if slope > 0:
        return {"trend": "up", "score": 70}
    elif slope < 0:
        return {"trend": "down", "score": 70}
    else:
        return {"trend": "neutral", "score": 50}


def _calc_rsi(df, period=14):
    closes = df["close"].astype(float)
    delta = closes.diff()

    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


def _detect_divergence(df):
    """
    Divergencia mínima básica RSI.
    """
    try:
        rsi = _calc_rsi(df)
        last_close = float(df["close"].iloc[-1])

        if rsi < 30:
            return {"type": "bullish", "strong": rsi < 20}
        if rsi > 70:
            return {"type": "bearish", "strong": rsi > 80}

        return {"type": None}
    except Exception:
        return {"type": None}


def _weighted_match(trends, direction):
    """
    Combina tendencias multitemporalidad para generar match_ratio.
    """
    score = 0
    total = 0

    for tf, info in trends.items():
        if info["trend"] == "up" and direction == "long":
            score += info["score"]
        elif info["trend"] == "down" and direction == "short":
            score += info["score"]
        total += 70  # constante simple

    if total == 0:
        return 0

    return round((score / total) * 100, 1)


def _grade_from_ratio(ratio):
    for grade, minval in GRADE_THRESHOLDS.items():
        if ratio >= minval:
            return grade
    return "D"


def _decision_from_ratio(ratio, divergence):
    if divergence.get("type") == "bearish" and ratio < 80:
        return "reversal-risk"
    if divergence.get("type") == "bullish" and ratio < 80:
        return "reversal-risk"

    if ratio >= DECISION_THRESHOLDS["enter"]:
        return "enter"
    if ratio >= DECISION_THRESHOLDS["wait"]:
        return "wait"
    return "skip"


# ============================================================
# 🔵 FUNCIÓN PRINCIPAL DEL MOTOR
# ============================================================
async def analyze_signal(symbol: str, direction: str):
    """
    Análisis completo para entrada inicial.
    """
    return await _run_analysis(symbol, direction, mode="signal")


async def analyze_reactivation(symbol: str, direction: str):
    """
    Análisis especial para reactivaciones.
    """
    return await _run_analysis(symbol, direction, mode="reactivation")


async def analyze_reversal(symbol: str, direction: str):
    """
    Análisis especial para riesgo de reversión.
    """
    return await _run_analysis(symbol, direction, mode="reversal")


# ============================================================
# 🔵 MOTOR TÉCNICO UNIFICADO
# ============================================================
async def _run_analysis(symbol: str, direction: str, mode: str):
    result = {
        "symbol": symbol,
        "direction": direction,
        "timeframes": {},
        "trend_score": 0,
        "match_ratio": 0,
        "grade": "D",
        "divergences": {},
        "decision": "skip",
        "allowed": False,
        "summary": "",
        "details": "",
    }

    # -----------------------------
    # Obtener precio actual
    # -----------------------------
    price = await fetch_price(symbol)
    if price is None:
        result["summary"] = "No hay precio disponible."
        return result

    # -----------------------------
    # Análisis por temporalidad
    # -----------------------------
    trends = {}

    for tf in DEFAULT_TIMEFRAMES:
        df = await fetch_ohlcv(symbol, tf, limit=200)
        if df is None:
            continue

        trend_info = _calc_trend(df)
        divergence = _detect_divergence(df)

        trends[tf] = {
            "trend": trend_info["trend"],
            "score": trend_info["score"],
            "divergence": divergence,
        }

    result["timeframes"] = trends

    if not trends:
        result["summary"] = "No hay datos suficientes en ninguna temporalidad."
        return result

    # -----------------------------
    # match_ratio
    # -----------------------------
    match_ratio = _weighted_match(trends, direction)
    result["match_ratio"] = match_ratio

    # -----------------------------
    # Grado A–D
    # -----------------------------
    result["grade"] = _grade_from_ratio(match_ratio)

    # -----------------------------
    # Divergencia global
    # -----------------------------
    all_div = [t["divergence"] for t in trends.values()]
    merged = {"type": None, "strong": False}

    for d in all_div:
        if d["type"] is not None:
            merged = d
            break

    result["divergences"] = merged

    # -----------------------------
    # Decisión
    # -----------------------------
    decision = _decision_from_ratio(match_ratio, merged)
    result["decision"] = decision
    result["allowed"] = decision == "enter"

    # -----------------------------
    # Summary
    # -----------------------------
    result["summary"] = (
        f"{symbol}: Tendencia {'favorable' if result['allowed'] else 'mixta'} "
        f"({match_ratio}%, grado {result['grade']})."
    )

    # -----------------------------
    # Detalle
    # -----------------------------
    details = []
    for tf, info in trends.items():
        details.append(
            f"{tf.upper()}: {info['trend']} "
            f"(score {info['score']}), div={info['divergence']['type']}"
        )

    result["details"] = "\n".join(details)

    return result
