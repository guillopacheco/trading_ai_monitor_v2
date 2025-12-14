from services.telegram_service.notifier import Notifier
from services.application.operation_service import OperationService
from services.coordinators.signal_coordinator import SignalCoordinator
from services.reactivation_engine.reactivation_engine import ReactivationEngine


class ApplicationLayer:
    def __init__(self, bot):
        # 🔔 Notificador único con bot real
        self.notifier = Notifier(bot)

        # 📡 Coordinadores / servicios
        self.signal = SignalCoordinator(notifier=self.notifier)
        self.operation = OperationService(notifier=self.notifier)

        # ♻️ Reactivación
        self.reactivation_engine = ReactivationEngine(notifier=self.notifier)
