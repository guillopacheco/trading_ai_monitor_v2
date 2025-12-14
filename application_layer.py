from services.telegram_service.notifier import Notifier
from services.application.operation_service import OperationService
from services.coordinators.signal_coordinator import SignalCoordinator
from services.reactivation_engine.reactivation_engine import ReactivationEngine


class ApplicationLayer:
    def __init__(self):
        # 🔔 Notificador único
        self.notifier = Notifier()

        # 📡 Coordinadores / servicios
        self.signal = SignalCoordinator(notifier=self.notifier)
        self.operation = OperationService(notifier=self.notifier)

        # ♻️ Motor de reactivación
        self.reactivation_engine = ReactivationEngine(notifier=self.notifier)
