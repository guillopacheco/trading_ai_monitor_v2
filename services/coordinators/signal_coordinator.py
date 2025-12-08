import logging
from services.application.signal_service import SignalService

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:

    def __init__(self):
        self.service = SignalService()

    # ---------------------------------------------------------
    # 📌 Procesar señal recibida desde Telegram VIP
    # ---------------------------------------------------------
    async def handle_new_signal(self, symbol: str, direction: str, entry=None):
        logger.info(f"[Coordinator] Procesando nueva señal: {symbol} {direction}")
        return await self.service.process_new(symbol, direction, entry)

    # ---------------------------------------------------------
    # ♻️ Evaluar una señal pendiente (para reactivación)
    # ---------------------------------------------------------
    async def evaluate_single_pending(self, signal_row: dict):
        return await self.service.evaluate_pending(signal_row)

    # ---------------------------------------------------------
    # ♻️ Evaluar TODAS las señales pendientes
    # ---------------------------------------------------------
    async def evaluate_all_pending(self):
        return await self.service.evaluate_all_pending()
