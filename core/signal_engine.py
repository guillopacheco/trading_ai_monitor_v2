"""
core/signal_engine.py
---------------------
Motor de análisis de señales → Orquesta el Motor Técnico A+

Este módulo NO habla directamente con Telegram.
Tampoco accede a la DB.

Flujo:
    signal_controller     → analyze_signal()
    reactivation_controller → analyze_signal_for_reactivation()
    technical_brain_unified → motor técnico A+
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from core.technical_brain_unified import run_unified_analysis

from utils.formatters import (
    format_signal_intro,
    format_analysis_summary,
)

logger = logging.getLogger("signal_engine")


# ==================================================================
# 🟦 1) Análisis completo de señal nueva
# ==================================================================

def analyze_signal(signal_obj) -> Dict[str, Any]:
    """
    Analiza una nueva señal recibida del canal VIP.
    Retorna un dict estructurado listo para enviar a Telegram.
    """

    try:
        result = run_unified_analysis(
            symbol=signal_obj.symbol,
            direction=signal_obj.direction,
            entry_price=signal_obj.entry,
            is_reactivation=False
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_signal: {e}")
        return {
            "allowed": False,
            "reason": f"Error del motor técnico: {e}",
            "message": "❌ Error analizando la señal."
        }

    # Formateo final
    header = format_signal_intro(signal_obj)
    summary = format_analysis_summary(result)

    final_msg = f"{header}\n{summary}"

    return {
        "allowed": result.get("allowed", False),
        "reason": result.get("reason", "Sin motivo"),
        "raw": result,
        "message": final_msg,
    }


# ==================================================================
# 🟧 2) Análisis específico para REACTIVACIÓN
# ==================================================================

def analyze_signal_for_reactivation(signal_obj) -> Dict[str, Any]:
    """
    Analiza una señal previamente rechazada para evaluar si debe reactivarse.
    """

    try:
        result = run_unified_analysis(
            symbol=signal_obj.symbol,
            direction=signal_obj.direction,
            entry_price=signal_obj.entry,
            is_reactivation=True
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_signal_for_reactivation: {e}")
        return {
            "allowed": False,
            "reason": f"Error del motor técnico: {e}",
        }

    return result

