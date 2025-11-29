"""
controllers/signal_controller.py
Controlador que maneja señales después del parser
"""

import logging
from core.signal_engine import (
    analyze_signal,
    analyze_reactivation,
    analyze_open_position,
)
from services.db_service import (
    save_new_signal,
    save_analysis_result,
)
# ============================================================
# SAFE SEND BRIDGE — evita ciclos de importación
# ============================================================
def safe_send(msg: str):
    try:
        from services.telegram_service import send_message
        send_message(msg)
    except Exception:
        pass

logger = logging.getLogger("signal_controller")


# ============================================================
# PROCESAR SEÑAL NUEVA
# ============================================================

def process_new_signal(signal_obj):
    """Procesa una señal nueva del canal VIP."""
    save_new_signal(signal_obj)

    result = analyze_signal(signal_obj)

    # guardar log técnico
    save_analysis_result(signal_obj.symbol, result["analysis"])

    # enviar mensaje al usuario
    safe_send(result["summary"])

    return result


# ============================================================
# REACTIVACIÓN
# ============================================================

def process_reactivation(signal_obj):
    """Evalúa si una señal pendiente debe reactivarse."""
    result = analyze_reactivation(signal_obj)

    save_analysis_result(signal_obj.symbol, result["analysis"])

    safe_send(result["summary"])

    return result


# ============================================================
# POSICIÓN ABIERTA
# ============================================================

def process_open_position(symbol, direction, loss_pct):
    result = analyze_open_position(symbol, direction)

    save_analysis_result(symbol, result["analysis"])

    # enviar resumen
    safe_send(result["summary"])

    return result
