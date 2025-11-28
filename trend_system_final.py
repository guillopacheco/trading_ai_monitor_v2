"""
trend_system_final.py — versión UNIFICADA 2025-11
-------------------------------------------------

Este módulo ya NO realiza análisis técnico por sí mismo.
Ahora actúa como FACHADA hacia el motor técnico unificado:

    technical_brain_unified.run_unified_analysis()

Se mantiene 100% compatible con motor_wrapper.py y resto de la app:

✔ analyze_trend_core()  → usado por motor_wrapper
✔ analyze_and_format()  → usado por Telegram (textos)
✔ get_thresholds()      → usado por reactivación/monitoreo

No se rompe nada.
-------------------------------------------------
"""

import logging
from technical_brain_unified import (
    run_unified_analysis,
    get_thresholds
)

logger = logging.getLogger("trend_system_final")


# ============================================================
# 📌 FUNCIÓN BASE (utilizada por motor_wrapper)
# ============================================================

def analyze_trend_core(symbol: str, direction: str = None, context: str = "entry"):
    """
    API central que usa motor_wrapper.py.
    Devuelve un diccionario con el análisis técnico unificado.
    """
    try:
        result = run_unified_analysis(symbol, direction, context=context)
        return result
    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core: {e}")
        return {
            "symbol": symbol,
            "direction_hint": direction,
            "allowed": False,
            "decision": "error",
            "decision_reasons": [str(e)],
        }


# ============================================================
# 📩 FORMATEO DEL TEXTO PARA TELEGRAM
# ============================================================

def analyze_and_format(symbol: str, direction: str = None):
    """
    Produce un texto entendible para Telegram basado en la
    salida unificada del motor técnico.
    """

    data = analyze_trend_core(symbol, direction, context="entry")

    major = data.get("major_trend", "neutral")
    overall = data.get("overall_trend", "neutral")
    match_ratio = data.get("match_ratio", 0)
    tech_score = data.get("technical_score", 0)
    grade = data.get("grade", "D")
    conf = data.get("confidence_label", "low")
    smart_bias = data.get("smart_bias", "neutral")
    divergences = data.get("divergences", {})
    tf = data.get("timeframes", {})

    entry_grade = data.get("entry_grade", "D")
    entry_mode = data.get("entry_mode", "block")

    lines = [
        f"📊 **Análisis Técnico de {symbol} ({direction})**",
        "",
        f"**Tendencia Mayor:** {major}",
        f"**Tendencia General:** {overall}",
        "",
        f"**Match Ratio:** {match_ratio:.1f}%",
        f"**Technical Score:** {tech_score:.1f}",
        f"**Grado:** {grade}",
        f"**Confianza:** {conf}",
        f"**Smart Bias:** {smart_bias}",
        "",
        "📌 **Temporalidades:**"
    ]

    for k, v in tf.items():
        lines.append(f"• {k}: {v}")

    # Divergencias
    if divergences:
        lines.append("")
        lines.append("🔍 **Divergencias:**")
        for k, v in divergences.items():
            lines.append(f"• {k}: {v}")

    # Entrada inteligente
    lines.append("")
    lines.append("🎯 **Entrada Inteligente**")
    lines.append(f"• Modo: **{entry_mode.upper()}**")
    lines.append(f"• Calidad: **{entry_grade}**")

    # Decisión global
    decision = data.get("decision", "unknown")
    lines.append("")
    lines.append(f"📌 **Decisión:** {decision.upper()}")

    # Razones
    reasons = data.get("decision_reasons", [])
    if reasons:
        lines.append("")
        lines.append("📝 **Razones:**")
        for r in reasons:
            lines.append(f"• {r}")

    return "\n".join(lines)


# ============================================================
# ⚙️ GET THRESHOLDS (api pública)
# ============================================================

def _get_thresholds():
    return get_thresholds()


# Compatibilidad con motor_wrapper
get_thresholds_public = _get_thresholds
