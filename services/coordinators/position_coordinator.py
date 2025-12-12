import logging

logger = logging.getLogger("position_coordinator")


class PositionCoordinator:
    """
    Coordina todo lo relacionado con posiciones abiertas:
    - Iniciar/detener el monitor async
    - Solicitar evaluación inmediata
    - Enviar notificaciones
    """

    def __init__(self, monitor, tracker, notifier):
        self.monitor = monitor
        self.tracker = tracker
        self.notifier = notifier

    # --------------------------------------------------------
    # Control del monitor
    # --------------------------------------------------------
    async def start_monitor(self):
        await self.monitor.start()

    async def stop_monitor(self):
        self.monitor.stop()

    def is_running(self) -> bool:
        return self.monitor.is_running()

    # --------------------------------------------------------
    # Evaluación manual inmediata (comando /evaluar por ejemplo)
    # --------------------------------------------------------
    async def evaluate_now(self):
        try:
            result = await self.monitor.evaluate_once()
            await self.notifier.safe_send("📊 Evaluación manual completada.")
            return result
        except Exception as e:
            logger.exception(f"❌ Error evaluando posiciones manualmente: {e}")
            await self.notifier.safe_send("❌ Error evaluando posiciones.")
            return None
