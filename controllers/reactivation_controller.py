"""
controllers/reactivation_controller.py
--------------------------------------
Controlador de reactivación de señales pendientes.

Este módulo NO accede directamente a Telegram ni a Bybit.
Sólo orquesta:
    db_service   → obtener señales pendientes
    signal_engine → analizar si debe reactivarse
    db_service   → actualizar estado
    telegram_service (safe_send) → notificar
"""

from __future__ import annotations

import logging
from typing import Optional

from services.db_service import (
    get_pending_signals,
    set_signal_reactivated,
)

from core.signal_engine import analyze_signal_for_reactivation

logger = logging.getLogger("reactivation_controller")


# ============================================================
# 📡 Bridge seguro a telegram_service (evita import circular)
# ============================================================

def safe_send(msg: str):
    try:
        from services.telegram_service import send_message  # import diferido
        send_message(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje desde reactivation_controller: {e}")


# ============================================================
# ♻️ Ciclo de reactivación — llamado por scheduler_service
# ============================================================

def run_reactivation_cycle() -> None:
    """
    Revisa todas las señales pendientes y decide si deben reactivarse.
    """
    logger.info("♻️ Revisando señales pendientes para reactivación…")

    signals = get_pending_signals()

    if not signals:
        logger.info("📭 No hay señales pendientes para reactivar.")
        return

    for sig in signals:
        symbol = sig.symbol
        direction = sig.direction

        logger.info(f"🔍 Revisando señal pendiente: {symbol} ({direction}).")

        try:
            # Motor técnico A+
            result = analyze_signal_for_reactivation(sig)
        except Exception as e:
            logger.error(f"❌ Error analizando {symbol}: {e}")
            continue

        if not result:
            logger.warning(f"⚠️ Motor no devolvió resultado para {symbol}.")
            continue

        allowed = result.get("allowed", False)
        reason = result.get("reason", "Sin motivo especificado")

        if not allowed:
            logger.info(f"⏳ Señal {symbol} NO reactivada: {reason}.")
            continue

        # Si el motor la permite → marcamos como reactivada
        set_signal_reactivated(sig.id)

        logger.info(f"✔ Señal REACTIVADA: {symbol}")

        # Notificación limpia
        safe_send(
            f"♻️ *Reactivación de señal*\n\n"
            f"Par: *{symbol}*\n"
            f"Dirección: *{direction.upper()}*\n"
            f"Motivo técnico: {reason}"
        )
