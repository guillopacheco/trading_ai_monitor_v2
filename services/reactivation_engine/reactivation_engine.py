# services/reactivation_engine/reactivation_engine.py

import logging

logger = logging.getLogger("reactivation_engine")


class ReactivationEngine:
    """
    Capa táctica: decide si una señal ignorada debe reactivarse,
    usando el resultado del análisis técnico (motor base).
    """

    def __init__(self):
        logger.info("🔧 ReactivationEngine inicializado.")

    async def evaluate_signal(
        self, symbol: str, direction: str, analysis: dict
    ) -> dict:
        """
        API ESTÁNDAR usada por SignalCoordinator.auto_reactivate()

        Retorna:
        {
          "allowed": bool,
          "reason": str,
          "analysis": dict
        }
        """

        decision = analysis.get("decision")
        score = float(analysis.get("technical_score", 0) or 0)
        match_ratio = float(analysis.get("match_ratio", 0) or 0)
        confidence = float(analysis.get("confidence", 0) or 0)
        grade = analysis.get("grade", "-")
        bias = analysis.get("smart_bias_code", "")

        # ---------------------------------------------------------
        # Regla 1: si el motor ya dice "skip" pero hay reversión fuerte
        # (bias bullish-reversal / bearish-reversal), permitir re-evaluación.
        # ---------------------------------------------------------
        strong_reversal = "reversal" in (bias or "")

        # ---------------------------------------------------------
        # Regla 2: umbrales mínimos para reactivación inteligente
        # (ajustables)
        # ---------------------------------------------------------
        allowed = False
        reasons = []

        # Caso obvio: si el análisis explícitamente decide "reactivate"
        if decision == "reactivate":
            allowed = True
            reasons.append("El motor marcó decision=reactivate")

        # Caso táctico: buen puntaje + match aceptable
        if (
            score >= 55
            and match_ratio >= 70
            and confidence >= 0.55
            and grade in ["A", "B", "C"]
        ):
            allowed = True
            reasons.append("Umbrales tácticos OK (score/match/confidence/grade)")

        # Caso especial: reversión fuerte detectada (para evitar perder el giro)
        if strong_reversal and score >= 45 and match_ratio >= 60:
            allowed = True
            reasons.append("Reversión fuerte + umbrales mínimos (anti-TP4 perdido)")

        if not allowed:
            reasons.append(
                f"No cumple reactivación: decision={decision}, score={score}, match={match_ratio}, "
                f"conf={confidence}, grade={grade}, bias={bias}"
            )

        return {
            "allowed": bool(allowed),
            "reason": " | ".join(reasons),
            "analysis": analysis,
        }
