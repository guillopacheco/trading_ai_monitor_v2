# =====================================================================
#  signal_engine.py
#  ---------------------------------------------------------------
#  Capa intermedia entre:
#     - technical_brain_unified (motor A+)
#     - controllers (signal_controller / reactivation / positions)
#     - services (telegram, db, scheduler)
#
#  Aquí NO se hace análisis técnico crudo: aquí simplemente
#  orquestamos el uso del motor técnico.
# =====================================================================

import logging

from core.technical_brain_unified import (
    run_full_analysis,
    evaluate_reactivation,
    analyze_open_position,
)

from utils.formatters import (
    format_signal_intro,
    format_tf_summary,
    format_entry_grade,
    format_analysis_summary,
)

logger = logging.getLogger("signal_engine")

# =====================================================================
# 🔹 1. ANALIZAR UNA NUEVA SEÑAL
# =====================================================================

async def analyze_signal(symbol: str, direction: str):
    """
    Entrada principal para analizar una señal nueva.
    """

    logger.info(f"🔍 Analizando señal nueva: {symbol} ({direction})")

    result = await run_full_analysis(symbol, direction)

    if not result["ok"]:
        return {
            "ok": False,
            "error": result.get("error", "Unknown"),
            "text": f"⚠️ No se pudo analizar {symbol}."
        }

    # ------- Formatear salida para Telegram -------
    header = format_signal_intro(symbol, direction)
    tf_msg = format_tf_summary(result["blocks"])
    grade_msg = format_entry_grade(result["entry_grade"])
    summary = format_analysis_summary(result)

    final_text = f"{header}\n{tf_msg}\n{grade_msg}\n{summary}"

    return {
        "ok": True,
        "analysis": result,
        "text": final_text,
        "entry_grade": result["entry_grade"],
        "global_score": result["global_score"],
    }


# =====================================================================
# 🔹 2. ANALIZAR UNA POSICIÓN ABIERTA (para monitoreo periódico)
# =====================================================================

async def analyze_open_position_signal(symbol: str, direction: str):
    """
    Llamado desde:
      - positions_controller
      - scheduler_service (cada ciclo)
    """

    logger.info(f"🔍 Analizando posición abierta: {symbol} ({direction})")

    result = await analyze_open_position(symbol, direction)

    if not result["ok"]:
        return {
            "ok": False,
            "error": result.get("reason", "Unknown"),
            "reversal": False,
        }

    # ------- Formato -------
    rev = result["reversal"]
    msg = f"🔎 Análisis {symbol}\n"
    msg += f"Reversal Detectado: {'❌ NO' if not rev else '🚨 SÍ — ALERTA'}"

    return {
        "ok": True,
        "analysis": result["analysis"],
        "reversal": rev,
        "text": msg,
    }


# =====================================================================
# 🔹 3. REACTIVACIÓN DE SEÑALES PENDIENTES
# =====================================================================

async def analyze_reactivation(symbol: str, direction: str):
    """
    Función que usan:
      - reactivation_controller
      - scheduler_service (cada ciclo)
    """

    logger.info(f"♻️ Analizando reactivación para {symbol} ({direction})")

    result = await evaluate_reactivation(symbol, direction)

    if "reactivate" not in result:
        return {
            "reactivate": False,
            "reason": "Invalid response",
            "text": f"⚠️ No se pudo evaluar reactivación para {symbol}."
        }

    can = result["reactivate"]
    grade = result["grade"]
    score = result["global_score"]

    text = (
        f"♻️ Reactivación {symbol}\n"
        f"➡️ Grade: {grade}\n"
        f"➡️ Score: {score:.2f}\n"
        f"➡️ ¿Reactiva? {'✔️ Sí' if can else '❌ No'}"
    )

    return {
        "reactivate": can,
        "grade": grade,
        "global_score": score,
        "analysis": result["analysis"],
        "text": text,
    }
