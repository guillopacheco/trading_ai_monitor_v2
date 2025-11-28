"""
scheduler_service.py
--------------------
Orquestador general de tareas asíncronas en Trading AI Monitor v2.

Responsabilidades:
- Gestionar monitores (posiciones, reactivaciones, etc.)
- Encender/apagar tareas de forma segura
- Centralizar el control de ciclos periódicos
- Evitar que main.py se vuelva inmanejable
"""

import asyncio
import logging

from controllers.positions_controller import PositionsMonitor
# En el futuro: from controllers.reactivation_controller import ReactivationMonitor

logger = logging.getLogger("scheduler_service")


# ============================================================
# 🔵 ESTRUCTURA DE ESTADO GLOBAL
# ============================================================
class SchedulerService:
    def __init__(self):
        self.tasks = {}           # {"positions": task_obj, ...}
        self.monitors = {}        # {"positions": monitor_instance}

        # Instancias de monitores
        self.monitors["positions"] = PositionsMonitor()

        # FUTURO:
        # self.monitors["reactivations"] = ReactivationMonitor()

    # ========================================================
    # 🔵 INICIAR UN MONITOR
    # ========================================================
    async def start_monitor(self, name: str):
        if name not in self.monitors:
            logger.error(f"❌ Monitor desconocido: {name}")
            return False

        if name in self.tasks:
            logger.warning(f"⚠️ Monitor {name} ya está activo.")
            return True

        monitor = self.monitors[name]

        logger.info(f"▶️ Iniciando monitor: {name}")
        await monitor.start()

        # Guardar la tarea para poder detenerla
        async def runner():
            try:
                await monitor.task
            except asyncio.CancelledError:
                logger.info(f"🛑 Monitor {name} cancelado correctamente.")

        self.tasks[name] = asyncio.create_task(runner())
        return True

    # ========================================================
    # 🔵 DETENER UN MONITOR
    # ========================================================
    async def stop_monitor(self, name: str):
        if name not in self.monitors:
            logger.error(f"❌ Monitor desconocido: {name}")
            return False

        if name not in self.tasks:
            logger.warning(f"⚠️ Monitor {name} ya está detenido.")
            return False

        logger.info(f"🛑 Deteniendo monitor: {name}")

        monitor = self.monitors[name]
        await monitor.stop()

        # Cancelar la task asociada
        task = self.tasks.pop(name)
        task.cancel()

        return True

    # ========================================================
    # 🔵 DETENER TODOS LOS MONITORES
    # ========================================================
    async def stop_all(self):
        logger.info("🛑 Deteniendo todos los monitores…")

        for name in list(self.tasks.keys()):
            await self.stop_monitor(name)

    # ========================================================
    # 🔵 LISTA DE MONITORES ACTIVOS
    # ========================================================
    def get_status(self):
        status = {}
        for name, monitor in self.monitors.items():
            status[name] = "ON" if name in self.tasks else "OFF"
        return status


# ============================================================
# 🔵 INSTANCIA GLOBAL
# ============================================================
scheduler = SchedulerService()
