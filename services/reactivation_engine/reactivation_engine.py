# ============================================================
#  ReactivationEngine — Reactivación inteligente y segura
# ============================================================

import logging

logger = logging.getLogger("reactivation_engine")


class ReactivationEngine:
    """
    Decide si una señal ignorada debe reactivarse,
    usando el resultado del motor técnico unificado.
    """

    def __init__(self):
        logger.info("🔧 ReactivationEngine inicializado.")

    async def evaluate_signal(
        self, symbol: str, direction: str, analysis: dict
    ) -> dict:
        """
        API usada por SignalCoordinator.auto_reactivate()

        Retorna:
        {
          "allowed": bool,
          "reason": str,
          "analysis": dict
        }
        """

        # -------------------------
        # Validación base
        # -------------------------
        if not analysis or not isinstance(analysis, dict):
            return {
                "allowed": False,
                "reason": "Análisis inválido",
                "analysis": analysis,
            }

        decision = analysis.get("decision")
        if decision == "error":
            return {
                "allowed": False,
                "reason": "Análisis en error",
                "analysis": analysis,
            }

        match_ratio = float(analysis.get("match_ratio", 0) or 0)
        score = float(analysis.get("technical_score", 0) or 0)
        confidence = float(analysis.get("confidence", 0) or 0)
        grade = analysis.get("grade", "-")

        divergences = analysis.get("divergences", {})
        major_trend = analysis.get("major_trend", {})

        reasons = []
        allowed = False

        # -------------------------
        # Regla dura de descarte
        # -------------------------
        if match_ratio < 50 or score < 45:
            return {
                "allowed": False,
                "reason": f"Descartada: match={match_ratio}, score={score}",
                "analysis": analysis,
            }

        # -------------------------
        # Caso 1: motor ya permite entrar
        # -------------------------
        if decision == "enter":
            allowed = True
            reasons.append("Motor indica entrada directa")

        # -------------------------
        # Caso 2: divergencia a favor
        # -------------------------
        def _is_div_favor(div):
            return (direction == "long" and div == "alcista") or (
                direction == "short" and div == "bajista"
            )

        rsi_div = divergences.get("RSI")
        macd_div = divergences.get("MACD")

        div_favor = _is_div_favor(rsi_div) or _is_div_favor(macd_div)

        if div_favor and score >= 55 and match_ratio >= 60:
            allowed = True
            reasons.append("Divergencia a favor + score/match suficientes")

        # -------------------------
        # Caso 3: reversión detectada
        # -------------------------
        trend_code = str(major_trend.get("trend_code", ""))
        is_reversal = "reversal" in trend_code

        if is_reversal and score >= 45 and match_ratio >= 55:
            allowed = True
            reasons.append("Reversión detectada (anti-TP4 perdido)")

        # -------------------------
        # Resultado final
        # -------------------------
        if not allowed:
            reasons.append(
                f"No cumple reactivación: decision={decision}, "
                f"score={score}, match={match_ratio}, grade={grade}"
            )

        return {
            "allowed": bool(allowed),
            "reason": " | ".join(reasons),
            "analysis": analysis,
        }
