"""
services/scheduler_service.py
-----------------------------
Scheduler central de tareas periódicas.

✔ Ciclo de reactivación de señales
✔ Ciclo de monitoreo de posiciones
"""

import logging
import asyncio

from controllers.reactivation_controller import run_reactivation_cycle
from controllers.positions_controller import check_positions

logger = logging.getLogger("scheduler_service")


# ============================================================
# 🔁 CICLO DE REACTIVACIÓN
# ============================================================

async def reactivation_loop():
    """
    Corre cada 15 minutos.
    """
    while True:
        try:
            logger.info("♻️ Ejecutando ciclo de reactivación…")
            await run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        await asyncio.sleep(900)   # 15 min


# ============================================================
# 🔁 CICLO DE POSICIONES
# ============================================================

async def positions_loop():
    """
    Corre cada 5 minutos.
    """
    while True:
        try:
            logger.info("🔍 Revisando posiciones abiertas…")
            await check_positions()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de posiciones: {e}")

        await asyncio.sleep(300)   # 5 min


# ============================================================
# ▶ INICIO DEL SCHEDULER
# ============================================================

async def start_scheduler():
    """
    Inicia ambos loops en paralelo.
    """
    logger.info("🕒 Iniciando scheduler…")

    asyncio.create_task(reactivation_loop())
    asyncio.create_task(positions_loop())

    logger.info("🕒 Scheduler activo (reactivación + posiciones).")
