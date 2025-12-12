import logging

logger = logging.getLogger("position_coordinator")


class PositionCoordinator:
    """
    Coordina el monitoreo de operaciones abiertas.

    Funciones:
      • Iniciar monitor de posiciones (/reanudar)
      • Detener monitor (/detener)
      • Mostrar estado (/estado)
    """

    def __init__(self, position_monitor, notifier):
        self.position_monitor = position_monitor
        self.notifier = notifier

    # ---------------------------------------------------------
    # INICIAR MONITOR
    # ---------------------------------------------------------
    async def start_monitor(self):
        """
        Llamado desde /reanudar.
        """
        try:
            await self.position_monitor.start()
            await self.notifier.safe_send("📡 *Monitor de operaciones iniciado*.")
        except Exception as e:
            logger.error(
                f"❌ Error iniciando monitor de posiciones: {e}", exc_info=True
            )
            await self.notifier.safe_send("❌ Error iniciando monitor de posiciones.")

    # ---------------------------------------------------------
    # DETENER MONITOR
    # ---------------------------------------------------------
    async def stop_monitor(self):
        """
        Llamado desde /detener.
        """
        try:
            self.position_monitor.stop()
            await self.notifier.safe_send("⏹ *Monitor de operaciones detenido*.")
        except Exception as e:
            logger.error(
                f"❌ Error deteniendo monitor de posiciones: {e}", exc_info=True
            )
            await self.notifier.safe_send("❌ Error deteniendo monitor de posiciones.")

    # ---------------------------------------------------------
    # ESTADO ACTUAL
    # ---------------------------------------------------------
    def get_status(self) -> dict:
        """
        Usado por /estado para reportar si el monitor está corriendo.
        """
        return {
            "running": (
                self.position_monitor.is_running()
                if hasattr(self.position_monitor, "is_running")
                else False
            )
        }
