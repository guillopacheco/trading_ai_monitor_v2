"""
services/scheduler_service.py
------------------------------
Servicio encargado de ejecutar ciclos periódicos:
 - Reactivación de señales
 - Monitoreo de posiciones abiertas

Usa asyncio.create_task para correr loops en paralelo.
"""

import asyncio
import logging

from controllers.reactivation_controller import run_reactivation_cycle
from controllers.positions_controller import check_positions  # ✔ FIX

logger = logging.getLogger("scheduler_service")


# ============================================================
# 🔹 LOOP: ciclo de reactivación
# ============================================================

async def _reactivation_loop():
    while True:
        try:
            logger.info("♻️ Ejecutando ciclo de reactivación…")
            await run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")
        await asyncio.sleep(60)  # cada 60 segundos


# ============================================================
# 🔹 LOOP: ciclo de revisión de posiciones
# ============================================================

async def _positions_loop():
    while True:
        try:
            logger.info("🔍 Revisando posiciones abiertas…")
            await check_positions()
        except Exception as e:
            logger.error(f"❌ Error revisando posiciones: {e}")
        await asyncio.sleep(45)  # cada 45 segundos


# ============================================================
# 🔹 FUNCIÓN PRINCIPAL
# ============================================================

async def start_scheduler(loop: asyncio.AbstractEventLoop):
    """
    Registra ambos loops como tareas en segundo plano.
    """
    logger.info("🕒 Iniciando scheduler…")

    loop.create_task(_reactivation_loop())
    loop.create_task(_positions_loop())

    logger.info("🕒 Scheduler activo (reactivación + posiciones).")
