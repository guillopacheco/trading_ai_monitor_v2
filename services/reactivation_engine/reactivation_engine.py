# services/reactivation_engine/reactivation_engine.py
import logging

logger = logging.getLogger("reactivation_engine")


class ReactivationEngine:
    def __init__(self):
        logger.info("🔧 ReactivationEngine inicializado.")

    async def evaluate_signal(
        self, symbol: str, direction: str, analysis: dict
    ) -> dict:
        # análisis esperado del technical_engine
        decision = (analysis or {}).get("decision", "error")
        score = float((analysis or {}).get("technical_score") or 0.0)
        match = float((analysis or {}).get("match_ratio") or 0.0)
        grade = (analysis or {}).get("grade") or "-"

        if decision == "error":
            return {
                "allowed": False,
                "reason": "Análisis en error",
                "analysis": analysis,
            }

        # ✅ regla mínima (ajustable): reactivar solo si allowed=True o score alto + match suficiente
        allowed = bool((analysis or {}).get("allowed", False))
        if allowed:
            return {
                "allowed": True,
                "reason": f"Reactivación OK: decision={decision}, score={score}, match={match}, grade={grade}",
                "analysis": analysis,
            }

        # fallback: permitir si se ve sólido aunque decision sea skip
        if score >= 70 and match >= 70:
            return {
                "allowed": True,
                "reason": f"Reactivación forzada por umbral: score={score}, match={match}, grade={grade}",
                "analysis": analysis,
            }

        return {
            "allowed": False,
            "reason": f"No cumple reactivación: decision={decision}, score={score}, match={match}, grade={grade}",
            "analysis": analysis,
        }
