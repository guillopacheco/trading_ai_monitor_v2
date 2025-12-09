import logging

# ahora importamos SOLO la función init_db
from database import init_db

from services.telegram_service.notifier import Notifier

from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator


logger = logging.getLogger("application_layer")


class ApplicationLayer:

    def __init__(self):

        logger.info("⚙️ Inicializando ApplicationLayer...")

        # =====================================================
        # 1. INICIALIZAR BASE DE DATOS (sin clase)
        # =====================================================
        init_db()

        # =====================================================
        # 2. NOTIFICADOR GLOBAL
        # =====================================================
        self.notifier = Notifier()

        # =====================================================
        # 3. APPLICATION SERVICES
        # =====================================================
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_service = OperationService(self.notifier)

        # =====================================================
        # 4. COORDINADORES
        # =====================================================
        self.signal = SignalCoordinator(self.signal_service, self.analysis_service, self.notifier)
        self.analysis = AnalysisCoordinator(self.analysis_service, self.notifier)
        self.position = PositionCoordinator(self.operation_service, self.analysis_service, self.notifier)

        logger.info("✅ ApplicationLayer inicializado correctamente.")
