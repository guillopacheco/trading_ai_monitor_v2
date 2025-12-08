"""
signal_reactivation_sync.py — FASE 2 (2025)
Sistema de reactivación automática de señales.
Totalmente integrado con:
 - signal_service
 - application_layer
 - technical_engine
 - DB actual
"""

import asyncio
import logging

from database import db_get_pending_signals, db_update_signal_status
from services.application.signal_service import evaluate_pending_signal

logger = logging.getLogger("signal_reactivation_sync")

# Intervalo de revisión automática (segundos)
REACTIVATION_INTERVAL = 60


# ============================================================
# 🔄 PROCESAR TODAS LAS SEÑALES PENDIENTES
# ============================================================

async def run_reactivation_cycle() -> str:
    """
    Ejecuta un ciclo único:
    - Obtiene señales 'pending' de la DB
    - Evalúa cada señal usando el motor técnico
    - Decide si REACTIVAR o SEGUIR PENDIENTE
    - Devuelve un texto para Telegram (si se usa manualmente)
    """

    pending = db_get_pending_signals()

    if not pending:
        logger.info("♻️ No hay señales pendientes para reactivación.")
        return "♻️ No hay señales pendientes."

    logger.info(f"♻️ Revisando {len(pending)} señales pendientes…")

    lines = ["♻️ *Resumen de reactivación:*"]

    for s in pending:
        try:
            symbol, msg = await evaluate_pending_signal(s)

            # evaluate_pending_signal retorna mensaje ya listo para Telegram
            # msg contiene resumen + motivos

            # Actualizar DB según el resultado
            if "REACTIVADA" in msg:
                db_update_signal_status(symbol, "reactivated")
            else:
                # La dejamos pendiente para futuros ciclos
                db_update_signal_status(symbol, "pending")

            lines.append(f"• {symbol} → {msg}")

        except Exception as e:
            logger.exception(f"❌ Error procesando señal {s.get('symbol')}: {e}")
            lines.append(f"• {s.get('symbol')} → ❌ Error: {e}")

    return "\n".join(lines)


# ============================================================
# 🔁 MONITOR AUTOMÁTICO EN BACKGROUND
# ============================================================

async def start_reactivation_monitor():
    """
    Bucle infinito que ejecuta un ciclo de reactivación
    cada REACTIVATION_INTERVAL segundos.
    """

    logger.info(f"♻️ Monitor de reactivación automática iniciado (intervalo={REACTIVATION_INTERVAL}s).")

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as e:
            logger.exception(f"❌ Error en ciclo automático de reactivación: {e}")

        await asyncio.sleep(REACTIVATION_INTERVAL)
