# services/technical_engine/engine_port.py

"""
engine_port.py
==================================================
Único punto de acceso externo al Motor Técnico.
Garantiza estabilidad aunque se reescriba el motor.
==================================================
"""

import logging
from services.technical_engine.motor_wrapper import analyze, analyze_and_format

logger = logging.getLogger("engine_port")


async def run_reactivation_analysis(symbol: str, direction: str):
    """
    Punto de entrada ESTABLE para el servicio de reactivación.
    Nunca expone lógica interna del motor técnico.
    """

    try:
        # --- 1) Ejecutar motor en modo reactivación ---
        result = analyze(
            symbol=symbol,
            direction_hint=direction,
            context="reactivation"
        )

    except Exception as e:
        logger.error(f"❌ Error ejecutando motor técnico: {e}")
        return {
            "should_reactivate": False,
            "match_ratio": 0.0,
            "score": 0.0,
            "reason": f"Error motor técnico: {e}",
            "report": None,
        }

    # --- 2) Normalizar salida ---
    match_ratio = float(result.get("match_ratio") or 0.0)
    decision     = result.get("decision")
    allowed      = bool(result.get("allowed"))
    score        = float(result.get("technical_score") or 0.0)

    # --- 3) Veredicto de reactivación estándar ---
    should_reactivate = (allowed and decision == "reactivate")

    # --- 4) Reporte formateado seguro ---
    try:
        report = analyze_and_format(symbol, direction)
    except Exception:
        report = "⚠️ Error generando reporte formateado."

    reason = (
        f"Motor técnico autorizó reactivación (match={match_ratio}%, score={score})."
        if should_reactivate else
        f"No cumple criterios (decision={decision}, score={score})."
    )

    return {
        "should_reactivate": should_reactivate,
        "match_ratio": match_ratio,
        "score": score,
        "reason": reason,
        "report": report
    }
