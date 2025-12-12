import logging
from services.technical_engine.technical_engine import analyze as technical_analyze

logger = logging.getLogger("reactivation_engine")


class ReactivationEngine:
    """
    Motor táctico de reactivación de señales.

    - No recibe parámetros en __init__()
    - Invoca technical_engine.analyze() internamente
    - Evalúa condiciones de activación tardía
    """

    def __init__(self):
        logger.info("🔄 ReactivationEngine inicializado (constructor vacío).")

    # ---------------------------------------------------------
    # MÉTODO PRINCIPAL
    # ---------------------------------------------------------
    async def evaluate_signal(self, symbol: str, direction: str):
        """
        Evalúa si una señal puede/ debe ser reactivada.

        Devuelve un dict estandarizado:
        {
            "allowed": bool,
            "reason": str,
            "analysis": dict
        }
        """
        logger.info(f"🔎 ReactivationEngine: evaluando {symbol} ({direction})...")

        try:
            analysis = await technical_analyze(symbol, direction)
        except Exception as e:
            logger.error(f"❌ Error técnico analizando {symbol}: {e}", exc_info=True)
            return {
                "allowed": False,
                "reason": "Error técnico en análisis",
                "analysis": None,
            }

        # -----------------------------------------------------
        # DECISIÓN BÁSICA (placeholder seguro)
        # La lógica completa se implementará en Fase B del motor real.
        # -----------------------------------------------------
        match_ratio = analysis.get("match_ratio", 0)
        tech_score = analysis.get("technical_score", 0)

        if match_ratio >= 50 and tech_score >= 50:
            return {
                "allowed": True,
                "reason": "Condiciones favorables para reactivación",
                "analysis": analysis,
            }

        return {
            "allowed": False,
            "reason": "Aún no coincide suficiente para reactivar",
            "analysis": analysis,
        }
