"""
reactivation_controller.py
--------------------------
Controlador oficial para reactivación automática de señales.

• Lee señales pendientes en la DB
• Revalida técnicamente cada una con el Motor A+
• Marca reactivadas cuando aplica
• Notifica por Telegram
"""

import logging

from services.db_service import (
    get_pending_signals,
    set_signal_reactivated,
    add_reactivation_record,
)
from core.signal_engine import analyze_reactivation
from services.telegram_service import safe_send


log = logging.getLogger("reactivation_controller")


# ===================================================================
# 🔄 CICLO PRINCIPAL DE REACTIVACIÓN
# ===================================================================
async def run_reactivation_cycle():
    """Revisa todas las señales pendientes y evalúa si deben reactivarse."""
    log.info("♻️  Revisando señales pendientes para reactivación…")

    # --------------------------------------------------------------
    # 1. Cargar señales pendientes desde DB
    # --------------------------------------------------------------
    try:
        signals = get_pending_signals()
    except Exception as e:
        log.error(f"❌ Error leyendo señales pendientes desde DB: {e}")
        return

    if not signals:
        log.info("📭 No hay señales pendientes para reactivar.")
        return

    # --------------------------------------------------------------
    # 2. Evaluar cada señal con Motor A+
    # --------------------------------------------------------------
    for sig in signals:
        signal_id = sig["id"]
        symbol = sig["symbol"]
        direction = sig["direction"]
        entry_price = sig["entry_price"]

        log.info(f"🔎 Evaluando reactivación para {symbol} ({direction})…")

        try:
            result = await analyze_reactivation(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
            )
        except Exception as e:
            log.error(f"❌ Error analizando reactivación para {symbol}: {e}")
            continue

        # ----------------------------------------------------------
        # 3. Validación del motor — Motor A+ retorna:
        #       { allowed: True/False, score: X, reason: "...", ... }
        # ----------------------------------------------------------
        if not result or not result.get("allowed"):
            log.info(f"⏳ Señal {symbol}: aún no apta para reactivación.")
            continue

        # ----------------------------------------------------------
        # 4. Marcar REACTIVADA en la DB
        # ----------------------------------------------------------
        try:
            set_signal_reactivated(signal_id)
            add_reactivation_record(signal_id, "Reactivación confirmada")
        except Exception as e:
            log.error(f"⚠️ No se pudo guardar reactivación para {symbol}: {e}")
            continue

        # ----------------------------------------------------------
        # 5. Notificar al usuario
        # ----------------------------------------------------------
        msg = (
            f"♻️ **REACTIVACIÓN AUTOMÁTICA DETECTADA**\n\n"
            f"📌 *{symbol}* ({direction.upper()})\n"
            f"💠 El Motor A+ detectó condiciones nuevamente favorables.\n"
            f"🔥 *Recomendación: evaluar entrada inmediata.*\n"
        )

        try:
            await safe_send(msg)
        except Exception as e:
            log.error(f"⚠️ No se pudo enviar mensaje de reactivación: {e}")

    log.info("♻️  Ciclo de reactivación completado.")
