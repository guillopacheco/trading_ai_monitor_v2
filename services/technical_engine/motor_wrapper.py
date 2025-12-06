# motor_wrapper.py — Capa de compatibilidad del motor técnico unificado

import logging

# ✅ Import correcto del motor técnico REAL
from services.technical_engine.technical_brain_unified import run_unified_analysis as core_analyze

logger = logging.getLogger("motor_wrapper")


def analyze(symbol: str,
            direction_hint: str = "long",
            context: str = "manual",
            roi: float = None,
            loss_pct: float = None):
    """
    Puente unificado que llama SIEMPRE al motor técnico oficial.
    Usado por:
      - signal_reactivation_sync
      - smart_reactivation_validator
      - operation_tracker
      - position_reversal_monitor
      - command_bot (/analizar)
      - telegram_reader
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
        logger.error(
            f"❌ Error en motor_wrapper.analyze() para {symbol}: {e}",
            exc_info=True
        )

        return {
            "snapshot": {},
            "decision": {"decision": "wait", "confidence": 0.0},
            "match_ratio": 0.0,
            "smart_bias": "N/A",
            "grade": "D",
            "error": str(e)
        }


def analyze_and_format(symbol: str, direction: str = "long"):
    """Compatibilidad con mensajes antiguos del bot."""
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
    """Compatibilidad con telegram_reader."""
    return analyze(
        symbol=symbol,
        direction_hint=direction,
        context="signal"
    )

# ================================================================
# 🔁 Alias específicos para compatibilidad con servicios antiguos
# ================================================================

def analyze_for_reactivation(symbol: str, direction: str, context: str = "reactivation"):
    """
    Alias específico para reactivación.

    Mantiene compatibilidad con smart_reactivation_validator:
    internamente delega a `analyze`, que ya construye el snapshot
    multi-TF con fallbacks (15m/30m/1h/4h) usando trend_system_final.
    """
    return analyze(symbol=symbol, direction_hint=direction, context=context)
