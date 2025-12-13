"""
smart_entry_validator.py — Smart Entry 2.1
Compatibilidad total con technical_engine.py
"""

import logging

logger = logging.getLogger("smart_entry")


def evaluate_smart_entry(snapshot: dict, major_trend: dict, direction: str) -> dict:
    """
    NUEVA FIRMA — requerida por technical_engine.py

    snapshot: dict completo multi-TF
    major_trend: dict con major_trend_code, label, etc.
    direction: "long" | "short"
    """

    reasons = []
    entry_score = 0

    # ================================================
    # DATOS EXTRAÍDOS DEL SNAPSHOT
    # ================================================
    match_ratio = snapshot.get("match_ratio", 0)
    tech_score = snapshot.get("technical_score", 0)

    # nuevo motor entrega esto:
    major_code = major_trend.get("trend_code_value", 0)
    bias_code = snapshot.get("smart_bias_code", "neutral")
    divergences = snapshot.get("divergences", {})

    # Flags
    div_bearish = any(v in ("bearish", "strong_bearish") for v in divergences.values())
    div_bullish = any(v in ("bullish", "strong_bullish") for v in divergences.values())

    # ================================================
    # SCORING BASE
    # ================================================
    entry_score += min(40, match_ratio * 0.4)  # match_ratio = 40%
    entry_score += min(40, tech_score * 0.4)  # technical_score = 40%

    # tendencia mayor (10%)
    if major_code == 2:
        entry_score += 10
    elif major_code == 1:
        entry_score += 6
    elif major_code == 0:
        entry_score += 4
    elif major_code == -1:
        entry_score += 2

    # smart_bias (10%)
    if "continuation" in str(bias_code):
        entry_score += 10
    elif "neutral" in str(bias_code):
        entry_score += 5
    elif "reversal" in str(bias_code):
        entry_score -= 5

    # ================================================
    # AJUSTES POR DIVERGENCIAS
    # ================================================
    if div_bearish and direction == "long":
        entry_score -= 15
        reasons.append("Divergencia bajista fuerte contra LONG")

    if div_bullish and direction == "short":
        entry_score -= 15
        reasons.append("Divergencia alcista fuerte contra SHORT")

    # Penalización leve por divergencias menores
    if any(v in ("bearish", "bullish") for v in divergences.values()):
        entry_score -= 5

    # ================================================
    # LIMITE FINAL
    # ================================================
    entry_score = max(0, min(100, entry_score))

    # ================================================
    # CLASIFICACIÓN (A–D)
    # ================================================
    if entry_score >= 75:
        entry_grade = "A"
    elif entry_score >= 60:
        entry_grade = "B"
    elif entry_score >= 45:
        entry_grade = "C"
    else:
        entry_grade = "D"

    # ================================================
    # MODO FINAL (ok / warn / block)
    # ================================================
    if entry_grade in ("A", "B"):
        entry_mode = "ok"
    elif entry_grade == "C":
        entry_mode = "warn"
        reasons.append("Condiciones mixtas — entrada con cautela")
    else:
        entry_mode = "block"
        reasons.append("Condiciones técnicas insuficientes")

    # Bias de reversión → bloquear siempre si score es bajo
    if "reversal" in bias_code and entry_grade in ("C", "D"):
        entry_mode = "block"
        reasons.append("Smart Bias indica reversión fuerte en contra")

    # ================================================
    # RETORNO UNIFICADO
    # ================================================
    return {
        "entry_score": entry_score,
        "entry_grade": entry_grade,
        "entry_mode": entry_mode,
        "entry_allowed": entry_mode != "block",
        "entry_reasons": reasons,
    }
