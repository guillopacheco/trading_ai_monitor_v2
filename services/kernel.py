# services/kernel.py
import logging
from config import TELEGRAM_CHANNEL_ID
from services.telegram_service.notifier import Notifier

logger = logging.getLogger("kernel")


class Kernel:
    """
    Kernel = contenedor de dependencias.
    Construye servicios/coordinators/engines con un contrato estable.
    """

    def __init__(self, bot):
        self.bot = bot

        # Instancias (se llenan en build)
        self.notifier = None
        self.reactivation_engine = None

        self.analysis_service = None
        self.signal_service = None
        self.operation_service = None

        self.signal_coordinator = None

        self.open_position_engine = None

    def build(self):
        """
        Construye todo con imports locales para evitar ciclos.
        """
        # --- Notifier (requiere bot)
        from services.telegram_service.notifier import Notifier

        self.notifier = Notifier(bot=self.bot, chat_id=TELEGRAM_CHANNEL_ID)

        # --- ReactivationEngine (NO pasar notifier por keyword; tu clase no lo acepta)
        from services.reactivation_engine.reactivation_engine import ReactivationEngine

        self.reactivation_engine = ReactivationEngine()

        # --- Servicios de aplicación
        from services.application.analysis_service import AnalysisService
        from services.application.signal_service import SignalService
        from services.application.operation_service import OperationService

        # OJO: OperationService en tu proyecto requiere notifier en __init__
        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()
        self.operation_service = OperationService(self.notifier)

        # --- Coordinators
        from services.coordinators.signal_coordinator import SignalCoordinator

        self.signal_coordinator = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        # --- Open position engine
        from services.open_position_engine.open_position_engine import (
            OpenPositionEngine,
        )

        self.open_position_engine = OpenPositionEngine(notifier=self.notifier)

        logger.info("✅ Kernel build() completado correctamente.")
        return self
