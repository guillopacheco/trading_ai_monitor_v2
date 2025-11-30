"""
reactivation_controller.py
---------------------------
Controlador para reactivación de señales pendientes.
"""

import logging
from services.db_service import (
    get_pending_signals,
    set_signal_reactivated,    # ✔ nombre correcto
    add_reactivation_record,   # ✔ existe
)
from core.signal_engine import analyze_signal_for_reactivation
from services.telegram_service import safe_send

log = logging.getLogger("reactivation_controller")


# ===================================================================
# 🔄 REVISAR TODAS LAS PENDIENTES
# ===================================================================
async def run_reactivation_cycle():
    log.info("♻️  Revisando señales pendientes para reactivación…")

    try:
        signals = get_pending_signals()
    except Exception as e:
        log.error(f"❌ Error leyendo señales pendientes desde DB: {e}")
        return

    if not signals:
        log.info("📭 No hay señales pendientes para reactivar.")
        return

    for sig in signals:
        signal_id = sig["id"]
        symbol = sig["symbol"]
        direction = sig["direction"]
        entry_price = sig["entry_price"]

        log.info(f"🔎 Evaluando reactivación: {symbol} ({direction})")

        try:
            result = await analyze_signal_for_reactivation(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
            )
        except Exception as e:
            log.error(f"❌ Error analizando reactivación para {symbol}: {e}")
            continue

        if not result or not result.get("allowed"):
            log.info(f"⏳ Señal {symbol} aún no apta para reactivación.")
            continue

        # ===========================================================
        # 🔥 Señal reactivada
        # ===========================================================
        set_signal_reactivated(signal_id)                 # ✔ función real
        add_reactivation_record(signal_id, "OK para reactivar")  # ✔ función real

        msg = (
            f"♻️ **REACTIVACIÓN AUTOMÁTICA**\n\n"
            f"📌 *{symbol}* ({direction.upper()})\n"
            f"💠 Condiciones técnicas ahora favorables.\n"
            f"🔥 *Recomendación: evaluar entrada inmediata.*\n"
        )

        try:
            await safe_send(msg)
        except Exception as e:
            log.error(f"⚠️ No se pudo enviar mensaje de reactivación: {e}")

    log.info("♻️  Ciclo de reactivación completado.")
