# application_layer.py
import logging
from services.kernel import Kernel

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Fachada de la app. NO construye piezas sueltas.
    Todo se construye desde Kernel para evitar wiring circular.
    """

    def __init__(self, bot):
        self.kernel = Kernel(bot).build()

        # Exponer módulos principales con nombres estables (lo que tu app espera)
        self.notifier = self.kernel.notifier

        self.analysis = self.kernel.analysis_service
        self.signal_service = self.kernel.signal_service
        self.operation = self.kernel.operation_service

        self.signal = self.kernel.signal_coordinator
        self.open_position_engine = self.kernel.open_position_engine

        logger.info("✅ ApplicationLayer inicializado correctamente.")
