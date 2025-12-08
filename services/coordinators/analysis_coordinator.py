# ===============================================================
#  Analysis Coordinator
#  Coordina cualquier tipo de análisis técnico
#  Fase 4 – Arquitectura Empresarial
# ===============================================================

import logging
from typing import Optional, Dict

from services.signals_service.signal_service import SignalService
from services.operation_service.operation_service import OperationService
from services.analysis_service.analysis_service import AnalysisService
from services.technical_engine.technical_engine import analyze as engine_analyze
from services.notifier_service.notifier import Notifier
from services.database_service.database import Database

logger = logging.getLogger("analysis_coordinator")


class AnalysisCoordinator:

    def __init__(
        self,
        signal_service: SignalService,
        operation_service: OperationService,
        analysis_service: AnalysisService,
        notifier: Notifier,
        database: Database
    ):
        self.signal_service = signal_service
        self.operation_service = operation_service
        self.analysis_service = analysis_service
        self.notifier = notifier
        self.db = database

    # ===========================================================
    # 1) Análisis manual (comando /analizar)
    # ===========================================================
    async def manual_analysis(self, symbol: str, direction: str):
        logger.info(f"📘 Análisis manual solicitado: {symbol} ({direction})")

        # Motor técnico
        result = await engine_analyze(symbol, direction, context="entry")

        # Construir mensaje
        msg = self.analysis_service.build_analysis_message(
            symbol=symbol,
            direction=direction,
            analysis=result,
            context="manual"
        )

        # Enviar resultado
        await self.notifier.send_message(msg)

        # Guardar análisis
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="manual"
        )

        return result

    # ===========================================================
    # 2) Análisis de reactivación (manual o automático)
    # ===========================================================
    async def analyze_reactivation(self, symbol: str):
        logger.info(f"♻️ Análisis para reactivación: {symbol}")

        direction = self.signal_service.get_direction(symbol)
        if not direction:
            await self.notifier.send_message(f"⚠️ No existe una señal previa para {symbol}.")
            return None

        result = await engine_analyze(symbol, direction, context="reactivation")

        msg = self.analysis_service.build_analysis_message(
            symbol=symbol,
            direction=direction,
            analysis=result,
            context="reactivation"
        )

        await self.notifier.send_message(msg)

        # Guardar log en DB
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="reactivation"
        )

        return result

    # ===========================================================
    # 3) Análisis de operación abierta (cuando se pide /estado o /operacion)
    # ===========================================================
    async def analyze_open_position(self, symbol: str):
        logger.info(f"📊 Análisis de operación abierta: {symbol}")

        position = self.operation_service.get_open_position(symbol)
        if not position:
            await self.notifier.send_message(f"ℹ️ No hay operación abierta en {symbol}.")
            return None

        direction = position.get("direction")
        loss_pct = position.get("loss_pct")

        result = await engine_analyze(symbol, direction, context="open")

        msg = self.analysis_service.build_open_position_message(
            symbol=symbol,
            direction=direction,
            analysis=result,
            loss_pct=loss_pct
        )

        await self.notifier.send_message(msg)

        # Guardar resultado
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="open_position"
        )

        return result

    # ===========================================================
    # 4) Análisis de reversión (inversion o cierre)
    # ===========================================================
    async def analyze_reversal(self, symbol: str):
        logger.info(f"🔄 Análisis de reversión solicitado para {symbol}")

        position = self.operation_service.get_open_position(symbol)
        if not position:
            await self.notifier.send_message(f"⚠️ No existe una operación activa en {symbol}.")
            return None

        direction = position["direction"]

        result = await engine_analyze(symbol, direction, context="reversal")

        msg = self.analysis_service.build_reversal_message(
            symbol=symbol,
            direction=direction,
            analysis=result
        )

        await self.notifier.send_message(msg)

        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="reversal"
        )

        return result

    # ===========================================================
    # 5) Análisis genérico para cualquier módulo
    # ===========================================================
    async def analyze(self, symbol: str, direction: str, context: str = "entry"):
        """
        Método genérico utilizado por otros servicios.
        Evita duplicación de código en otros módulos.
        """

        logger.info(f"🧩 Análisis genérico: {symbol} ({direction}) [ctx={context}]")

        result = await engine_analyze(symbol, direction, context=context)

        return result
