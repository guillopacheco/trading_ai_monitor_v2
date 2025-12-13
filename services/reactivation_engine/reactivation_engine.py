import logging
from services.technical_engine.technical_engine import analyze as technical_analyze

logger = logging.getLogger("reactivation_engine")


class ReactivationState:
    """Estados posibles para reactivación (placeholder simple)."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    PENDING = "pending"


class ReactivationEngine:
    """
    Motor táctico de reactivación de señales.

    - No recibe parámetros en __init__()
    - Invoca technical_engine.analyze() internamente
    - Evalúa condiciones de activación tardía de forma segura.
    """

    def __init__(self):
        logger.info("🔄 ReactivationEngine inicializado (constructor vacío).")

    # ---------------------------------------------------------
    # MÉTODO PRINCIPAL (async para integrarse con el resto)
    # ---------------------------------------------------------
    async def evaluate_signal(
        self,
        symbol: str,
        direction: str,
        analysis: dict | None = None,
    ) -> dict:
        """
        Evalúa si una señal puede / debe ser reactivada.

        Devuelve un dict estandarizado:
        {
            "allowed": bool,
            "reason": str,
            "analysis": dict
        }
        """
        logger.info(f"🔎 ReactivationEngine: evaluando {symbol} ({direction})...")

        try:
            # Si no nos pasan análisis pre-calculado, lo generamos
            if analysis is None:
                analysis = technical_analyze(
                    symbol,
                    direction_hint=direction,
                    context="reactivation",
                )
        except Exception as e:
            logger.error(f"❌ Error técnico analizando {symbol}: {e}", exc_info=True)
            return {
                "allowed": False,
                "reason": "Error técnico en análisis",
                "analysis": None,
            }

        if not analysis:
            return {
                "allowed": False,
                "reason": "Motor técnico no devolvió resultado",
                "analysis": None,
            }

        # -----------------------------------------------------
        # DECISIÓN BÁSICA (placeholder seguro)
        # Aquí se puede conectar smart_reactivation_validator más adelante.
        # -----------------------------------------------------
        match_ratio = float(analysis.get("match_ratio", 0) or 0)
        tech_score = float(analysis.get("technical_score", 0) or 0)

        # Regla simple:
        # - match >= 60 y score >= 55 → permitir reactivación
        if match_ratio >= 60 and tech_score >= 55:
            return {
                "allowed": True,
                "reason": f"Condiciones favorables (match={match_ratio:.1f}, "
                f"score={tech_score:.1f})",
                "analysis": analysis,
            }

        return {
            "allowed": False,
            "reason": f"Aún no coincide suficiente para reactivar "
            f"(match={match_ratio:.1f}, score={tech_score:.1f})",
            "analysis": analysis,
        }
