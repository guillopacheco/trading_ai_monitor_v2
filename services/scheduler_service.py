"""
services/scheduler_service.py
-----------------------------
Ejecutor periódico de dos tareas:
    1) Reactivación de señales pendientes
    2) Revisión de posiciones abiertas
"""

from __future__ import annotations
import logging
import asyncio

from controllers.reactivation_controller import run_reactivation_cycle
from controllers.positions_controller import check_open_positions  # ✔ nombre correcto

logger = logging.getLogger("scheduler_service")


# ============================================================
# ⏳ LOOP PRINCIPAL DEL SCHEDULER
# ============================================================

async def scheduler_loop():
    """
    Ejecuta cada 60 segundos:
        - ciclo de reactivación
        - revisión de posiciones abiertas
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


# ============================================================
# ▶️ INICIO DEL SCHEDULER (llamado desde main.py)
# ============================================================

def start_scheduler(loop: asyncio.AbstractEventLoop):
    """
    Registra el scheduler en el event loop principal.
    """
    loop.create_task(scheduler_loop())
    logger.info("🕒 Iniciando scheduler…")
