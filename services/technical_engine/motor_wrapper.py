"""
motor_wrapper.py — Capa de compatibilidad
-----------------------------------------
Este archivo unifica TODAS las llamadas técnicas de la aplicación
usando el motor OFICIAL: technical_engine.analyze()

✔ Reemplaza cualquier referencia al motor viejo
✔ Garantiza compatibilidad con todos los módulos existentes
"""

import logging

# ✅ Este es el motor técnico oficial y único
from services.technical_engine.technical_engine import analyze as core_analyze

logger = logging.getLogger("motor_wrapper")


def analyze(symbol: str,
            direction_hint: str = "long",
            context: str = "manual",
            roi: float = None,
            loss_pct: float = None):
    """
    Puente estandarizado usado por:
    - signal_reactivation_sync
    - operation_tracker
    - position_reversal_monitor
    - telegram_reader
    - command_bot (/analizar)

    Siempre llama al motor técnico real: core_analyze()
    """
    try:
        result = core_analyze(
            symbol=symbol,
            direction_hint=direction_hint,
            context=context,
            roi=roi,
            loss_pct=loss_pct
        )
        return result

    except Exception as e:
        logger.error(f"❌ Error en motor_wrapper.analyze() para {symbol}: {e}", exc_info=True)
        # Para evitar romper flujos críticos, devolvemos un fallback simple
        return {
            "snapshot": {},
            "decision": {"decision": "wait", "confidence": 0.0},
            "match_ratio": 0.0,
            "smart_bias": "N/A",
            "grade": "D",
            "error": str(e)
        }


# Alias por compatibilidad con código viejo (si fuera llamado)
def analyze_and_format(symbol: str, direction: str = "long"):
    """Formato simple usado por telegram_reader histórico."""
    result = analyze(symbol, direction_hint=direction, context="manual")

    snap = result.get("snapshot", {})
    decision = result.get("decision", {})

    msg = (
        f"📊 Análisis de {symbol}\n"
        f"• Tendencia mayor: {snap.get('major_trend_label', 'N/A')}\n"
        f"• Smart Bias: {snap.get('smart_bias', 'N/A')}\n"
        f"• Confianza: {result.get('match_ratio', 0):.1f}% "
        f"(Grado {result.get('grade', 'D')})\n\n"
        f"📌 Recomendación: {decision.get('decision', 'N/A')} "
        f"({decision.get('confidence', 0)*100:.1f}% confianza)\n"
    )

    return msg

def analyze_for_signal(symbol: str, direction: str = "long"):
    """
    Compatibilidad con telegram_reader.
    Usa el motor técnico oficial en contexto 'signal'.
    """
    return analyze(
        symbol=symbol,
        direction_hint=direction,
        context="signal"
    )
