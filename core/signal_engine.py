"""
core/signal_engine.py
---------------------
Motor de análisis → Orquesta el Motor Técnico A+.

Este módulo NO se comunica con Telegram ni accede a la base de datos.
Se limita a:
    - Recibir objetos de señal / posición
    - Ejecutar run_unified_analysis()
    - Formatear parcialmente la respuesta
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
# 🟦 1) Análisis completo de señal NUEVA
# ==================================================================

def analyze_signal(signal_obj) -> Dict[str, Any]:
    """
    Analiza una señal nueva del canal VIP.
    Devuelve un dict estructurado.
    """

    try:
        result = run_unified_analysis(
            symbol=signal_obj.symbol,
            direction=signal_obj.direction,
            entry_price=signal_obj.entry,
            is_reactivation=False,
            is_position_check=False,
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_signal: {e}")
        return {
            "allowed": False,
            "reason": f"Error del motor técnico: {e}",
            "message": "❌ Error analizando la señal.",
            "raw": {},
        }

    # Formato del mensaje
    header = format_signal_intro(signal_obj)
    summary = format_analysis_summary(result)
    msg = f"{header}\n{summary}"

    return {
        "allowed": result.get("allowed", False),
        "reason": result.get("reason", "Sin motivo"),
        "raw": result,
        "message": msg,
    }


# ==================================================================
# 🟧 2) Análisis de REACTIVACIÓN
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
            is_reactivation=True,
            is_position_check=False,
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_signal_for_reactivation: {e}")
        return {
            "allowed": False,
            "reason": f"Error del motor técnico: {e}",
            "raw": {}
        }

    return result


# ==================================================================
# 🟨 3) Análisis para POSICIONES ABIERTAS (operaciones activas)
# ==================================================================

def analyze_open_position(position_obj) -> Dict[str, Any]:
    """
    Analiza una posición abierta utilizando el Motor Técnico A+.

    position_obj debe incluir:
        - symbol
        - side (BUY/SELL)
        - entryPrice
    """

    symbol = position_obj.get("symbol")
    side = position_obj.get("side", "").lower()
    entry_price = position_obj.get("entryPrice")

    direction = "long" if side == "buy" else "short"

    try:
        result = run_unified_analysis(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            is_reactivation=False,
            is_position_check=True,  # señalamos que es una operación activa
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_open_position: {e}")
        return {
            "reversal": False,
            "allowed": False,
            "reason": f"Error del motor técnico: {e}",
            "raw": {},
        }

    # Detecta reversión severa según motor A+
    reversal = result.get("reversal_detected", False)

    return {
        "reversal": reversal,
        "allowed": result.get("allowed", True),
        "reason": result.get("reason", "Sin motivo"),
        "raw": result
    }
