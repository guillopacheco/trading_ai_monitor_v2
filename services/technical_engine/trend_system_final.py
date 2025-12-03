"""
trend_system_final.py — versión UNIFICADA 2025-11
-------------------------------------------------

Este módulo ya NO realiza análisis técnico por sí mismo.
Ahora actúa como FACHADA hacia el motor técnico unificado:

    technical_brain_unified.run_unified_analysis()

Se mantiene 100% compatible con motor_wrapper.py y resto de la app:

✔ analyze_trend_core()  → usado por motor_wrapper y operation_tracker
✔ analyze_and_format()  → usado por Telegram (textos)
✔ get_thresholds()      → usado por reactivación/monitoreo

-------------------------------------------------
"""

import logging
from typing import Optional

from services.technical_engine.technical_brain_unified import (
    get_thresholds,
    get_bias_weight,
    get_score_weight,
)


logger = logging.getLogger("trend_system_final")

# ============================================================
# THRESHOLDS Y PESOS — definidos localmente para evitar
# dependencias circulares innecesarias
# ============================================================

def get_thresholds():
    return {
        "grade_A": 85,
        "grade_B": 70,
        "grade_C": 55,
    }

def get_bias_weight():
    return {
        "strong": 1.0,
        "moderate": 0.7,
        "weak": 0.4,
    }

def get_score_weight():
    return {
        "trend": 0.5,
        "momentum": 0.3,
        "divergence": 0.2,
    }

# ============================================================
# 📌 FUNCIÓN BASE (utilizada por motor_wrapper y operation_tracker)
# ============================================================

def analyze_trend_core(
    symbol: str,
    direction: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
):
    """
    API central que usan motor_wrapper.py y operation_tracker.py.
    Devuelve un diccionario con el análisis técnico unificado.

    Parámetros:
    - symbol: par (ej. "BTCUSDT")
    - direction: "long"/"short" (hint de dirección)
    - context: "entry", "reactivation", "reversal", "operation"
    - roi: ROI con apalancamiento (opcional, solo para context="operation")
    - loss_pct: pérdida sin apalancamiento (opcional, solo para context="operation")
    """
    try:
        result = run_unified_analysis(
            symbol,
            direction,
            context=context,
            roi=roi,
            loss_pct=loss_pct,
        )
        return result
    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core: {e}")
        return {
            "symbol": symbol,
            "direction_hint": direction,
            "allowed": False,
            "decision": "error",
            "decision_reasons": [str(e)],
            "roi": roi,
            "loss_pct": loss_pct,
        }


# ============================================================
# 📩 FORMATEO DEL TEXTO PARA TELEGRAM
# ============================================================

def analyze_and_format(symbol: str, direction: str = None):
    """
    Versión profesional 2025 del mensaje técnico para Telegram.
    Compatible con el motor técnico unificado.
    """

    data = analyze_trend_core(symbol, direction, context="entry")

    # ============================
    # 📌 EXTRACCIÓN DE DATOS
    # ============================
    major = data.get("major_trend", "neutral")
    overall = data.get("overall_trend", "neutral")
    match_ratio = data.get("match_ratio", 0)
    tech_score = data.get("technical_score", 0)
    grade = data.get("grade", "D")
    conf_label = data.get("confidence_label", "low")
    smart_bias = data.get("smart_bias", "neutral")
    divergences = data.get("divergences", {})
    tf = data.get("timeframes", {})

    entry_grade = data.get("entry_grade", "D")
    entry_mode = data.get("entry_mode", "block")

    decision = data.get("decision", "unknown")
    decision_reasons = data.get("decision_reasons", [])

    # ============================
    # 🎯 ENCABEZADO
    # ============================
    title = f"📘 **Análisis Técnico — {symbol.upper()} ({direction.upper()})**"

    # PRECIO ACTUAL
    current_price = data.get("current_price")
    price_line = f"💵 Precio actual: {current_price}" if current_price else ""


    # ============================
    # 🎯 CONCLUSIÓN INMEDIATA
    # ============================
    if decision == "enter":
        conclusion = f"🎯 **Conclusión:** ENTRAR (Condición favorable)"
    elif decision == "reactivate":
        conclusion = f"🎯 **Conclusión:** REACTIVAR (Señal nuevamente favorable)"
    elif decision == "reversal-risk":
        conclusion = f"⚠️ **Conclusión:** RIESGO DE REVERSIÓN (precaución)"
    elif decision == "wait":
        conclusion = f"🕒 **Conclusión:** ESPERAR (Estructura mixta)"
    elif decision == "skip":
        conclusion = f"⛔ **Conclusión:** EVITAR (Condiciones desfavorables)"
    else:
        conclusion = f"❓ **Conclusión:** {decision.upper()}"

    # ============================
    # 📌 RESUMEN RÁPIDO
    # ============================
    resumen = [
        "📌 **Resumen Rápido**",
        f"• Tendencia Mayor: {major}",
        f"• Match Ratio: {match_ratio:.1f}%",
        f"• Score Técnico: {tech_score:.1f}",
        f"• Smart Bias: {smart_bias}",
        f"• Calidad Entrada: {entry_grade} ({entry_mode.upper()})",
    ]

    # ============================
    # 🕒 TEMPORALIDADES
    # ============================
    tfs_list = []
    for k, v in tf.items():
        tfs_list.append(f"{k}: {v.capitalize()}")

    temporalidades = " • ".join(tfs_list)
    tf_block = f"🕒 **Temporalidades**\n{temporalidades}"

    # ============================
    # 🔍 DIVERGENCIAS
    # ============================
    if divergences:
        if all(v in [None, "none", ""] for v in divergences.values()):
            div_block = "🔍 **Divergencias**\n• Ninguna relevante"
        else:
            lines = ["🔍 **Divergencias**"]
            for k, v in divergences.items():
                if v:
                    lines.append(f"• {k}: {v}")
            div_block = "\n".join(lines)
    else:
        div_block = "🔍 **Divergencias**\n• Ninguna relevante"

    # ============================
    # 📝 MOTIVOS
    # ============================
    if decision_reasons:
        motivos = ["📝 **Motivos**"]
        for r in decision_reasons:
            motivos.append(f"• {r}")
        motivos_block = "\n".join(motivos)
    else:
        motivos_block = ""

    # ============================
    # 📈 SUGERENCIA
    # ============================
    if decision == "enter":
        sugerencia = "📈 **Sugerencia:** operación viable, entrar con gestión de riesgo."
    elif decision == "reactivate":
        sugerencia = "📈 **Sugerencia:** oportunidad renovada, estructura nuevamente favorable."
    elif decision == "wait":
        sugerencia = "🕒 **Sugerencia:** esperar una mejor alineación del mercado."
    elif decision == "skip":
        sugerencia = "🚫 **Sugerencia:** evitar esta señal y monitorear posibles reactivaciones."
    elif decision == "reversal-risk":
        sugerencia = "⚠️ **Sugerencia:** riesgo de giro importante, revisar exposición."
    else:
        sugerencia = ""

    # ============================
    # 🧱 CONSTRUCCIÓN FINAL
    # ============================
    parts = [
        title,
        price_line,
        "",
        conclusion,
        "",
        "\n".join(resumen),
        "",
        tf_block,
        "",
        div_block,
        "",
        motivos_block,
        "",
        sugerencia,
    ]

    return "\n".join(part for part in parts if part.strip())


# ============================================================
# ⚙️ GET THRESHOLDS (api pública)
# ============================================================

def _get_thresholds():
    return get_thresholds()


# Compatibilidad con motor_wrapper
get_thresholds_public = _get_thresholds
