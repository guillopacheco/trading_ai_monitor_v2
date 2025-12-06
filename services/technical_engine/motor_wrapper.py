import logging
from typing import Optional, Dict, Any

from services.technical_engine.technical_engine import analyze as core_analyze

logger = logging.getLogger("motor_wrapper")


# ============================================================
#  Motor Único — Punto de entrada oficial del análisis técnico
# ============================================================

def analyze(
    symbol: str,
    direction_hint: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
    entry_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Análisis técnico estándar. Usado para:
    - validar señales
    - validar reactivaciones
    - validar reversals
    - análisis manual (/analizar) si se quiere
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
        logger.exception(f"❌ Error en motor_wrapper.analyze() para {symbol}: {e}")
        return {
            "error": True,
            "message": str(e),
        }


def analyze_for_signal(symbol: str, direction: str) -> Dict[str, Any]:
    """Análisis específico para señales recibidas desde Telegram."""
    return analyze(symbol, direction_hint=direction, context="signal")


def analyze_for_reactivation(symbol: str, direction: str) -> Dict[str, Any]:
    """Análisis específico para reactivaciones."""
    return analyze(symbol, direction_hint=direction, context="reactivation")


def analyze_for_reversal(
    symbol: str,
    direction: str,
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Análisis específico para reversales (operaciones abiertas).
    Aquí sí se usan roi y loss_pct.
    """
    return analyze(
        symbol,
        direction_hint=direction,
        context="reversal",
        roi=roi,
        loss_pct=loss_pct,
    )


def analyze_and_format(
    symbol: str,
    direction: Optional[str],
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
) -> str:
    """
    Versión formateada para enviar por Telegram.
    Adaptada al motor técnico unificado (snapshot).
    """
    data = analyze(
        symbol,
        direction_hint=direction,
        context=context,
        roi=roi,
        loss_pct=loss_pct,
    )

    if data.get("error"):
        return f"❌ Error en análisis: {data.get('message')}"

    snap = data.get("snapshot", {}) or {}

    major = snap.get("major_trend_label", "N/A")
    confidence = snap.get("match_ratio", 0.0)
    grade = snap.get("grade", "D")
    bias = snap.get("smart_bias", "N/A")

    msg = (
        f"📊 Análisis de {symbol}\n"
        f"• Tendencia mayor: {major}\n"
        f"• Smart Bias: {bias}\n"
        f"• Confianza: {confidence:.1f}% (Grado {grade})\n"
    )

    divs = data.get("divergences", [])
    if divs:
        msg += "\n⚠️ Divergencias detectadas:\n"
        for d in divs:
            msg += f"• {d.get('type')} en {d.get('tf')} ({d.get('direction')})\n"

    decision = data.get("decision", {})
    msg += (
        "\n📌 Recomendación: "
        f"{decision.get('decision', 'N/A')} "
        f"({decision.get('confidence', 0)*100:.1f}% confianza)"
    )

    return msg
