"""
application_layer.py — Fase 4 (2025)
Capa orquestadora principal que coordina SignalCoordinator,
AnalysisCoordinator y PositionCoordinator.
"""

import logging
from typing import Optional, Dict

# Coordinadores
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

# Servicios
from services.application.signal_service import SignalService
from services.operation_service.operation_service import OperationService
from services.analysis_service.analysis_service import AnalysisService
from services.notifier_service.notifier import Notifier
from services.database_service.database import Database

logger = logging.getLogger("application_layer")


# ===============================================================
# Inicialización Global – Capa de Aplicación
# ===============================================================

class ApplicationLayer:

    def __init__(self):
        logger.info("🧠 Inicializando ApplicationLayer...")

        # Servicios base
        self.signal_service = SignalService()
        self.operation_service = OperationService()
        self.analysis_service = AnalysisService()
        self.notifier = Notifier()
        self.database = Database()

        # Coordinadores
        self.signal_coord = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
            database=self.database
        )

        self.analysis_coord = AnalysisCoordinator(
            signal_service=self.signal_service,
            operation_service=self.operation_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
            database=self.database
        )

        self.position_coord = PositionCoordinator(
            operation_service=self.operation_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
            database=self.database,
            signal_service=self.signal_service
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ===========================================================
    # ✉️ Procesar señales entrantes desde Telegram VIP
    # ===========================================================
    async def process_incoming_signal(self, symbol: str, direction: str):
        """
        Usado por telegram_reader.py cuando una señal es capturada del canal VIP.
        """
        logger.info(f"📥 ApplicationLayer → Procesando señal nueva: {symbol} ({direction})")

        signal = {
            "symbol": symbol.upper(),
            "direction": direction.lower()
        }

        return await self.signal_coord.process_raw_signal(signal)

    # ===========================================================
    # 🤖 Comando /analizar
    # ===========================================================
    async def manual_analysis(self, symbol: str, direction: str):
        logger.info(f"📘 ApplicationLayer → manual_analysis: {symbol} {direction}")
        return await self.analysis_coord.manual_analysis(symbol, direction)

    # ===========================================================
    # 🔍 Comando /detalles
    # ===========================================================
    async def diagnostic(self, symbol: str):
        logger.info(f"🔍 ApplicationLayer → diagnostic: {symbol}")
        return await self.analysis_service.build_detailed_snapshot(symbol)

    # ===========================================================
    # ♻️ Comando /reactivar (reactivación manual)
    # ===========================================================
    async def manual_reactivation(self, symbol: str):
        logger.info(f"♻️ ApplicationLayer → manual_reactivation: {symbol}")
        return await self.signal_coord.manual_reactivation(symbol)

    # ===========================================================
    # 📈 Comando /estado o /operacion — revisar operación abierta
    # ===========================================================
    async def check_open_position(self, symbol: str):
        logger.info(f"📊 ApplicationLayer → check_open_position: {symbol}")
        return await self.position_coord.evaluate_position(symbol)

    # ===========================================================
    # 🔄 Comando /reversion
    # ===========================================================
    async def check_reversal(self, symbol: str):
        logger.info(f"🔄 ApplicationLayer → check_reversal: {symbol}")
        return await self.position_coord.evaluate_reversal(symbol)

    # ===========================================================
    # 🚨 Evaluación automática de pérdidas (para -30, -50, -70)
    # ===========================================================
    async def auto_loss_check(self, symbol: str):
        logger.info(f"⚠️ ApplicationLayer → auto_loss_check: {symbol}")
        return await self.position_coord.auto_loss_check(symbol)

    # ===========================================================
    # 🚨 Reversión automática (si config futura lo permite)
    # ===========================================================
    async def auto_reversal_trigger(self, symbol: str):
        logger.info(f"🚨 ApplicationLayer → auto_reversal_trigger: {symbol}")
        return await self.position_coord.auto_reversal_trigger(symbol)

