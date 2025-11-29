"""
services/scheduler_service.py
-----------------------------
Scheduler: tareas periódicas (reactivación + revisión de posiciones)
"""

from __future__ import annotations
import logging
import asyncio

from controllers.reactivation_controller import run_reactivation_cycle
from controllers.positions_controller import check_open_positions

logger = logging.getLogger("scheduler_service")


async def scheduler_loop():
    """
    Loop del scheduler ejecutado cada 60 segundos.
    """
    logger.info("🕒 Scheduler activo (reactivación + posiciones).")

    while True:
        try:
            logger.info("♻️ Ejecutando ciclo de reactivación…")
            run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        try:
            logger.info("🔍 Revisando posiciones abiertas…")
            await check_open_positions()
        except Exception as e:
            logger.error(f"❌ Error revisando posiciones: {e}")

        await asyncio.sleep(60)


def start_scheduler(loop: asyncio.AbstractEventLoop):
    """
    Registra el scheduler en el event loop principal.
    """
    loop.create_task(scheduler_loop())
    logger.info("🕒 Iniciando scheduler…")
