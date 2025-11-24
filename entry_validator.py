"""
entry_validator.py
-------------------
Validador profesional de ENTRADA basado en snapshot multi-TF.

Este módulo NO ejecuta análisis técnico.
Trabaja únicamente con el snapshot generado por motor_wrapper_core.

Usa:
- Coherencia de tendencia (4h→1h→30m→15m→5m)
- Momentum (RSI)
- Divergencias RSI / MACD
- EMA short/long en marcos bajos (timing)
- Smart bias
- Confianza global
- match_ratio inicial

Devuelve:
- entry_allowed
- entry_score (0–100)
- entry_grade (A–D)
- entry_mode (swing / scalp / neutral)
- entry_reasons (explicación)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("entry_validator")


# ============================================================
# Utilidades internas
# ============================================================
def _normalize_direction(direction_hint: Optional[str]) -> Optional[str]:
    if not direction_hint:
        return None
    d = direction_hint.lower().strip()
    if d in ("long", "buy"):
        return "long"
    if d in ("short", "sell"):
        return "short"
    return None


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def _build_tf_index(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    idx = {}
    for tf in snapshot.get("timeframes", []):
        label = tf.get("tf_label") or tf.get("tf")
        if label:
            idx[str(label)] = tf
    return idx


# ============================================================
# Núcleo del validador profesional
# ============================================================
def validate_entry(snapshot: Dict[str, Any], signal_side: Optional[str]) -> Dict[str, Any]:
    """
    snapshot = resultado del motor técnico (motor_wrapper_core):
        snapshot["timeframes"], snapshot["match_ratio"], snapshot["divergences"], etc.
    signal_side = "long" / "short" / None

    Devuelve:
      {
        "allowed": bool,
        "score": float,
        "grade": str,
        "mode": "swing"|"scalp"|"neutral",
        "reasons": [ ... ]
      }
    """

    direction = _normalize_direction(signal_side)
    reasons: List[str] = []
    score: float = float(snapshot.get("match_ratio", 50.0))
    conf: float = float(snapshot.get("confidence", 0.0))
    divs: Dict[str, Any] = snapshot.get("divergences") or {}

    reasons.append(f"Match ratio inicial: {score:.1f}%")

    # Tendencia global
    major_code = snapshot.get("major_trend_code")
    smart_bias = snapshot.get("smart_bias_code")

    tf = _build_tf_index(snapshot)

    # -------------------------------------------------------------
    # 1) Sin dirección → modo exploratorio (neutro)
    # -------------------------------------------------------------
    if direction is None:
        if conf >= 0.7:
            score += 5
            reasons.append("Confianza alta → +5.")
        elif conf < 0.4:
            score -= 5
            reasons.append("Confianza baja → -5.")

        score = max(0, min(score, 100))
        return {
            "allowed": True,
            "score": score,
            "grade": _grade(score),
            "mode": "neutral",
            "reasons": reasons,
        }

    # -------------------------------------------------------------
    # 2) Tendencia mayor vs dirección
    # -------------------------------------------------------------
    want = "bull" if direction == "long" else "bear"

    if major_code == want:
        score += 8
        reasons.append("Alineado con tendencia mayor → +8.")
    elif major_code in ("bull", "bear"):
        score -= 12
        reasons.append("Contra la tendencia mayor → -12.")
    else:
        reasons.append("Tendencia mayor lateral.")

    # -------------------------------------------------------------
    # 3) Coherencia multi-TF (más peso a 4h, 1h)
    # -------------------------------------------------------------
    weights = {"4h": 2.0, "1h": 1.6, "30m": 1.3, "15m": 1.0, "5m": 0.8}

    def ok_dir(code: str) -> bool:
        return (direction == "long" and code == "bull") or (
            direction == "short" and code == "bear"
        )

    for label, w in weights.items():
        tf_data = tf.get(label)
        if not tf_data:
            continue

        code = tf_data.get("trend_code")
        if code:
            if ok_dir(code):
                score += 2.5 * w
            elif code in ("bull", "bear"):
                score -= 3.0 * w

        rsi = tf_data.get("rsi")
        if rsi is not None:
            rsi = float(rsi)
            if direction == "long":
                if rsi >= 55:
                    score += 1.5 * w
                elif rsi <= 45:
                    score -= 1.5 * w
            else:
                if rsi <= 45:
                    score += 1.5 * w
                elif rsi >= 55:
                    score -= 1.5 * w

    # -------------------------------------------------------------
    # 4) EMA short / long (timing)
    # -------------------------------------------------------------
    low = tf.get("15m") or tf.get("30m") or tf.get("5m")
    if low:
        es = low.get("ema_short")
        el = low.get("ema_long")
        if es is not None and el is not None:
            if direction == "long":
                if es > el:
                    score += 6
                    reasons.append("EMA short > EMA long en TF bajo → +6.")
                else:
                    score -= 8
                    reasons.append("EMA short < EMA long en TF bajo → -8.")
            else:
                if es < el:
                    score += 6
                    reasons.append("EMA short < EMA long en TF bajo → +6.")
                else:
                    score -= 8
                    reasons.append("EMA short > EMA long en TF bajo → -8.")

    # -------------------------------------------------------------
    # 5) Divergencias peligrosas
    # -------------------------------------------------------------
    div_rsi = str(divs.get("RSI") or "").lower()
    div_macd = str(divs.get("MACD") or "").lower()

    if direction == "long":
        if "bajista" in div_rsi or "bajista" in div_macd:
            score -= 15
            reasons.append("Divergencias bajistas contra LONG → -15.")
    else:
        if "alcista" in div_rsi or "alcista" in div_macd:
            score -= 15
            reasons.append("Divergencias alcistas contra SHORT → -15.")

    # -------------------------------------------------------------
    # 6) Smart bias + confianza
    # -------------------------------------------------------------
    if smart_bias == "continuation":
        score += 4
        reasons.append("Smart bias: continuación → +4.")
    elif smart_bias in ("bullish-reversal", "bearish-reversal"):
        score -= 6
        reasons.append("Smart bias advierte giro → -6.")

    if conf >= 0.7:
        score += 4
        reasons.append("Confianza global alta → +4.")
    elif conf < 0.4:
        score -= 6
        reasons.append("Confianza global baja → -6.")

    # Clamp
    score = max(0, min(score, 100))
    grade = _grade(score)

    # -------------------------------------------------------------
    # 7) Decisión final
    # -------------------------------------------------------------
    allowed = score >= 50

    if score < 45:
        # Divergencias fuertes = prohibido
        if (direction == "long" and "bajista" in div_rsi) or (
            direction == "short" and "alcista" in div_rsi
        ):
            allowed = False
            reasons.append("Peligro crítico: divergencias fuertes + score bajo.")

    # -------------------------------------------------------------
    # 8) Clasificación del modo
    # -------------------------------------------------------------
    swing = False
    scalp = False

    if tf.get("4h") and ok_dir(tf["4h"].get("trend_code", "")):
        swing = True
    if tf.get("1h") and ok_dir(tf["1h"].get("trend_code", "")):
        swing = True
    if tf.get("5m") and ok_dir(tf["5m"].get("trend_code", "")):
        scalp = True
    if tf.get("15m") and ok_dir(tf["15m"].get("trend_code", "")):
        scalp = True

    if swing and not scalp:
        mode = "swing"
    elif scalp and not swing:
        mode = "scalp"
    elif swing and scalp:
        mode = "swing"
    else:
        mode = "neutral"

    return {
        "allowed": allowed,
        "score": score,
        "grade": grade,
        "mode": mode,
        "reasons": reasons,
    }
