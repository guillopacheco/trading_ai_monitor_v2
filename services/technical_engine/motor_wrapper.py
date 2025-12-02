import logging
from typing import Optional, Dict, Any

from services.technical_engine.trend_system_final import analyze_trend_core

logger = logging.getLogger("motor_wrapper")


# ============================================================
#  Motor Único — Punto de entrada oficial del análisis técnico
# ============================================================

def analyze(symbol: str, direction_hint: Optional[str] = None, context: str = "entry") -> Dict[str, Any]:
    """
    Análisis técnico estándar. Usado para:
    - validar señales
    - validar reactivaciones
    - validar reversals
    - análisis manual (/analizar)
    """
    try:
        result = analyze_trend_core(symbol, direction_hint, context)
        return result

    except Exception as e:
        logger.exception(f"❌ Error en motor_wrapper.analyze() para {symbol}: {e}")
        return {
            "error": True,
            "message": str(e)
        }


def analyze_for_signal(symbol: str, direction: str) -> Dict[str, Any]:
    """Análisis específico para señales recibidas desde Telegram."""
    return analyze(symbol, direction, context="signal")


def analyze_for_reactivation(symbol: str, direction: str) -> Dict[str, Any]:
    """Análisis específico para reactivaciones."""
    return analyze(symbol, direction, context="reactivation")


def analyze_for_reversal(symbol: str, direction: str) -> Dict[str, Any]:
    """Análisis específico para reversales (operaciones abiertas)."""
    return analyze(symbol, direction, context="reversal")


def analyze_and_format(symbol: str, direction: str, context: str = "entry") -> str:
    """
    Versión formateada para enviar por Telegram.
    """
    data = analyze(symbol, direction, context)

    if data.get("error"):
        return f"❌ Error en análisis: {data.get('message')}"

    # Formato simple, puedes personalizarlo luego
    summary = data.get("summary", {})
    trend = summary.get("trend", "N/A")
    confidence = summary.get("confidence", "N/A")

    return (
        f"📊 Análisis de {symbol}\n"
        f"• Tendencia: {trend}\n"
        f"• Confianza: {confidence}\n"
    )
