# application_layer.py

import logging

from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.telegram_service.notifier import Notifier
from services.telegram_service.command_bot import start_command_bot
from services.telegram_service.telegram_reader import start_telegram_reader
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Punto de orquestación general de toda la aplicación.
    Ejecuta:
    ✔ lector de señales
    ✔ bot de comandos
    ✔ monitores automáticos
    ✔ análisis bajo demanda (coordinators)
    """

    def __init__(self):

        # Notificador central
        self.notifier = Notifier()

        # Coordinadores (capa de negocio)
        self.analysis = AnalysisCoordinator()
        self.signal = SignalCoordinator()
        self.positions = PositionCoordinator(self.notifier)

    # ============================================================
    # INICIO COMPLETO DEL SISTEMA
    # ============================================================
    async def start(self):
        logger.info("🚀 ApplicationLayer → Iniciando sistema...")

        # 1) Bot de comandos
        logger.info("🤖 Iniciando bot de comandos…")
        await start_command_bot(self)

        # 2) Lector de señales VIP
        logger.info("📡 Iniciando lector de Telegram…")
        await start_telegram_reader(self)

        # 3) Monitor de reactivación automática
        logger.info("♻️ Iniciando monitor de reactivación…")
        start_reactivation_monitor(self)

        logger.info("✅ ApplicationLayer → Servicios iniciados correctamente.")

    # ============================================================
    # Manejo desde CommandBot
    # ============================================================

    async def analyze(self, symbol: str, direction: str):
        """Bot → analiza un par bajo demanda."""
        return await self.analysis.analyze(symbol, direction)

    async def manual_reactivate(self, symbol: str):
        """Bot → fuerza reactivar una señal."""
        return await self.signal.manual_reactivate(symbol)

    async def manual_close(self, symbol: str):
        """Bot → cierre manual de posición."""
        return await self.positions.manual_close(symbol)

    async def manual_reverse(self, symbol: str, side: str):
        """Bot → reversión manual de posición."""
        return await self.positions.manual_reverse(symbol, side)

    async def monitor_positions(self):
        """Bot → revisar todas las posiciones abiertas."""
        return await self.positions.monitor_positions()
