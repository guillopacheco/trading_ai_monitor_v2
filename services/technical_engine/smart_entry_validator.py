"""
smart_entry_validator.py — Smart Entry 2.0
------------------------------------------
Refinamiento del sistema de entrada inteligente para
trabajar junto al motor técnico unificado.

Produce:
• entry_score (0–100)
• entry_grade (A–D)
• entry_mode ("ok", "warn", "block")
• entry_reasons (list)

------------------------------------------
"""

import logging
logger = logging.getLogger("smart_entry")

def evaluate_entry(symbol, direction, snapshot):
    """
    Evalúa la calidad técnica de la entrada usando
    el snapshot del motor técnico unificado.
    """

    reasons = []
    entry_score = 0

    # ================================
    # EXTRAER DATOS DEL SNAPSHOT
    # ================================
    match_ratio = snapshot.get("match_ratio", 0)
    tech_score = snapshot.get("technical_score", 0)
    major_code = snapshot.get("major_trend_code", 0)
    bias = snapshot.get("smart_bias_code", "neutral")
    divergences = snapshot.get("divergences", {})

    # Flags de divergencias
    div_bearish = any(
        v in ("bearish", "strong_bearish") for v in divergences.values()
    )
    div_bullish = any(
        v in ("bullish", "strong_bullish") for v in divergences.values()
    )

    # ================================
    # SCORING BASE
    # ================================
    # match_ratio (40%)
    entry_score += min(40, match_ratio * 0.4)

    # tech_score (40%)
    entry_score += min(40, tech_score * 0.4)

    # tendencia mayor (10%)
    if major_code == 2:
        entry_score += 10
    elif major_code == 1:
        entry_score += 6
    elif major_code == 0:
        entry_score += 4
    elif major_code == -1:
        entry_score += 2
    else:
        entry_score += 0

    # smart_bias (10%)
    if "continuation" in str(bias):
        entry_score += 10
    elif "neutral" in str(bias):
        entry_score += 5
    elif "reversal" in str(bias):
        entry_score -= 5

    # ================================
    # AJUSTES POR DIVERGENCIAS
    # ================================
    if div_bearish and direction == "long":
        entry_score -= 15
        reasons.append("Divergencia bajista fuerte contra el LONG")

    if div_bullish and direction == "short":
        entry_score -= 15
        reasons.append("Divergencia alcista fuerte contra el SHORT")

    # Penalización leve por divergencias menores
    if any(v in ("bearish", "bullish") for v in divergences.values()):
        entry_score -= 5

    # ================================
    # LIMITES
    # ================================
    entry_score = max(0, min(100, entry_score))

    # ================================
    # CLASIFICACIÓN (A–D)
    # ================================
    if entry_score >= 75:
        entry_grade = "A"
    elif entry_score >= 60:
        entry_grade = "B"
    elif entry_score >= 45:
        entry_grade = "C"
    else:
        entry_grade = "D"

    # ================================
    # MODO ENTRADA
    # ================================
    if entry_grade == "A":
        entry_mode = "ok"
    elif entry_grade == "B":
        entry_mode = "ok"
    elif entry_grade == "C":
        entry_mode = "warn"
        reasons.append("Condiciones mixtas — entrada con cautela")
    else:
        entry_mode = "block"
        reasons.append("Condiciones técnicas insuficientes")

    # Si bias indica reversión clara → degradar
    if "reversal" in str(bias) and entry_grade in ("C", "D"):
        entry_mode = "block"
        reasons.append("Smart Bias indica reversión fuerte en contra")

    # ================================
    # RETORNO
    # ================================
    return {
        "entry_score": entry_score,
        "entry_grade": entry_grade,
        "entry_mode": entry_mode,
        "entry_allowed": entry_mode != "block",
        "entry_reasons": reasons,
    }
