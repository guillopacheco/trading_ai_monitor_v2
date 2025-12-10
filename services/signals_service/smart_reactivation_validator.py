# ================================================================
# smart_reactivation_validator.py — VERSIÓN GPT FINAL 2025-12
# Normaliza el análisis para decidir reactivación de forma segura.
# Compatible con motores GPT / DeepSeek / snapshot v2.
# ================================================================

import logging
logger = logging.getLogger("smart_reactivation_validator")


# ================================================================
# FUNCIÓN PRINCIPAL
# ================================================================
def evaluate_for_reactivation(analysis: dict) -> dict:
    """
    Recibe el dict bruto del motor técnico y devuelve:
      {
        "allowed": True/False,
        "score": float,
        "reason": "texto"
      }
    """

    if not analysis or analysis.get("error"):
        return {
            "allowed": False,
            "score": 0,
            "reason": "Motor devolvió error"
        }

    # ------------------------------------------------------------
    # 1) Extraer campos con máxima compatibilidad
    # ------------------------------------------------------------
    snapshot = analysis.get("snapshot", {})
    decision_block = analysis.get("decision", {})
    entry_block = analysis.get("entry", {})
    smart_entry_block = analysis.get("smart_entry", {})

    # Tendencia mayor
    major_trend = (
        snapshot.get("major_trend_label")
        or snapshot.get("major_trend")
        or "unknown"
    )

    # Match técnico
    match_ratio = (
        snapshot.get("match_ratio")
        or snapshot.get("technical_match")
        or smart_entry_block.get("match_ratio")
        or 0
    )
    try:
        match_ratio = float(match_ratio)
    except Exception:
        match_ratio = 0.0

    # Confianza global
    confidence = (
        snapshot.get("confidence")
        or smart_entry_block.get("confidence")
        or 0
    )
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    # Allowed según motor
    allowed_decision = decision_block.get("allowed")
    allowed_entry = entry_block.get("allowed")
    allowed_smart_entry = smart_entry_block.get("entry_allowed")

    allowed = any([
        allowed_decision,
        allowed_entry,
        allowed_smart_entry
    ])

    # ------------------------------------------------------------
    # 2) Reglas de reactivación (versión final)
    # ------------------------------------------------------------

    #  Rule A — si el motor ya marcó allowed, reactivar
    if allowed:
        return {
            "allowed": True,
            "score": 100,
            "reason": "El motor marcó allowed=True"
        }

    # Rule B — match técnico suficientemente alto
    if match_ratio >= 70:
        return {
            "allowed": True,
            "score": match_ratio,
            "reason": f"Match técnico alto ({match_ratio}%)"
        }

    # Rule C — confianza global alta
    if confidence >= 0.65:   # 65%+
        return {
            "allowed": True,
            "score": confidence * 100,
            "reason": f"Confianza elevada ({confidence*100:.1f}%)"
        }

    # Rule D — Tendencia mayor a favor
    if major_trend.lower() in ["bullish", "bearish", "long", "short"]:
        # Aunque no active allowed, se reconoce tendencia válida
        return {
            "allowed": False,
            "score": match_ratio,
            "reason": f"Tendencia mayor válida pero match bajo ({match_ratio}%)"
        }

    # Rule E — Caso neutral
    return {
        "allowed": False,
        "score": match_ratio,
        "reason": "Condiciones técnicas insuficientes"
    }
