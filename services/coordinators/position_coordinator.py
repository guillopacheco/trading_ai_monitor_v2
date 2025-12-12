import logging

logger = logging.getLogger("position_coordinator")


class PositionCoordinator:
    """
    Coordina el monitoreo continuo de operaciones abiertas.
    """

    def __init__(self, position_service, position_monitor, notifier):
        self.position_service = position_service
        self.position_monitor = position_monitor
        self.notifier = notifier

        logger.info("🔧 PositionCoordinator inicializado correctamente.")

    # ---------------------------------------------------------
    # CONTROL DEL MONITOR
    # ---------------------------------------------------------
    async def start_monitor(self):
        logger.info("▶️ Iniciando monitoreo de posiciones abiertas...")
        await self.notifier.safe_send("📡 Monitoreo de operaciones abierto.")
        self.position_monitor.start()

    async def stop_monitor(self):
        logger.info("⏹ Deteniendo monitoreo de posiciones abiertas...")
        self.position_monitor.stop()
        await self.notifier.safe_send("🛑 Monitoreo de operaciones detenido.")

    # ---------------------------------------------------------
    # EVALUACIÓN BAJO DEMANDA
    # ---------------------------------------------------------
    async def evaluate_now(self):
        """
        Evalúa inmediatamente todas las posiciones abiertas.
        """
        logger.info("🔍 Evaluación bajo demanda de posiciones abiertas...")

        positions = self.position_service.get_open_positions()

        if not positions:
            await self.notifier.safe_send("ℹ️ No hay posiciones abiertas.")
            return

        for pos in positions:
            evaluation = await self.position_monitor.evaluate_position(pos)
            await self.notifier.safe_send(evaluation.to_telegram_message())
