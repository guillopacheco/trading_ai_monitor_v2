# ===============================================================
#  Position Coordinator
#  Coordina decisiones basadas en operaciones abiertas.
#
#  Fase 4 – Arquitectura Empresarial de trading_ai_monitor_v2
# ===============================================================

import logging
from typing import Dict, Optional

from services.operation_service.operation_service import OperationService
from services.analysis_service.analysis_service import AnalysisService
from services.technical_engine.technical_engine import analyze as engine_analyze
from services.notifier_service.notifier import Notifier
from services.database_service.database import Database
from services.signals_service.signal_service import SignalService

logger = logging.getLogger("position_coordinator")


class PositionCoordinator:

    LOSS_LEVELS = [30, 50, 70, 90]

    def __init__(
        self,
        operation_service: OperationService,
        analysis_service: AnalysisService,
        notifier: Notifier,
        database: Database,
        signal_service: SignalService
    ):
        self.op_service = operation_service
        self.analysis_service = analysis_service
        self.notifier = notifier
        self.db = database
        self.signal_service = signal_service

    # ===========================================================
    # 1) Evaluación estándar (comando /estado o /posicion)
    # ===========================================================
    async def evaluate_position(self, symbol: str):
        logger.info(f"📘 Evaluando operación abierta: {symbol}")

        position = self.op_service.get_open_position(symbol)
        if not position:
            await self.notifier.send_message(f"ℹ️ No existe operación abierta en {symbol}.")
            return None

        direction = position["direction"]
        loss_pct = abs(position.get("loss_pct", 0))

        # Ejecutar motor técnico:
        engine_result = await engine_analyze(symbol, direction, context="open")

        # Construir mensaje profesional
        msg = self.analysis_service.build_open_position_message(
            symbol=symbol,
            direction=direction,
            analysis=engine_result,
            loss_pct=loss_pct
        )

        await self.notifier.send_message(msg)

        # Registrar análisis en DB
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=engine_result.get("match_ratio"),
            technical_score=engine_result.get("technical_score"),
            grade=engine_result.get("grade"),
            context="open_position"
        )

        return engine_result

    # ===========================================================
    # 2) Evaluación automática por umbrales (-30, -50, -70, -90)
    # ===========================================================
    async def auto_loss_check(self, symbol: str):
        """
        Utilizado por bucles automáticos (si lo deseas en el futuro)
        o por la lógica del bot de reactivación.
        """

        position = self.op_service.get_open_position(symbol)
        if not position:
            return None

        direction = position["direction"]
        loss_pct = abs(position.get("loss_pct", 0))

        logger.info(f"📉 Auto-loss-check: {symbol} pérdida={loss_pct}%")

        # Si la pérdida no supera ningún nivel → no se hace nada
        triggered_levels = [lvl for lvl in self.LOSS_LEVELS if loss_pct >= lvl]
        if not triggered_levels:
            return None

        highest = max(triggered_levels)
        logger.info(f"⚠️ Nivel activado: -{highest}%")

        # Ejecutar motor técnico
        result = await engine_analyze(symbol, direction, context="loss_check")

        msg = self.analysis_service.build_loss_warning_message(
            symbol=symbol,
            direction=direction,
            loss_pct=loss_pct,
            analysis=result,
            level=highest
        )

        await self.notifier.send_message(msg)

        # Guardar registro
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context=f"loss_{highest}"
        )

        return result

    # ===========================================================
    # 3) Comando /reversion → evaluar e indicar inversion o cierre
    # ===========================================================
    async def evaluate_reversal(self, symbol: str):
        logger.info(f"🔄 Evaluando reversión: {symbol}")

        position = self.op_service.get_open_position(symbol)
        if not position:
            await self.notifier.send_message(f"⚠️ No existe operación activa en {symbol}.")
            return None

        direction = position["direction"]

        # Ejecutar motor con contexto “reversal”
        result = await engine_analyze(symbol, direction, context="reversal")

        msg = self.analysis_service.build_reversal_message(
            symbol=symbol,
            direction=direction,
            analysis=result
        )

        await self.notifier.send_message(msg)

        # Registrar en DB
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
    # 4) Decisión automática para cerrar o invertir (opcional)
    # ===========================================================
    async def auto_reversal_trigger(self, symbol: str):
        """
        Este módulo permite revertir o cerrar automáticamente
        si implementas órdenes automáticas más adelante.
        """

        position = self.op_service.get_open_position(symbol)
        if not position:
            return None

        loss_pct = abs(position.get("loss_pct", 0))
        direction = position["direction"]

        # Solo revisar si la pérdida ya es crítica:
        if loss_pct < 70:
            return None

        logger.info(f"🚨 Auto-reversal-check: {symbol} con pérdida crítica {loss_pct}%")

        result = await engine_analyze(symbol, direction, context="auto_reversal")

        msg = self.analysis_service.build_auto_reversal_decision(
            symbol=symbol,
            direction=direction,
            analysis=result,
            loss_pct=loss_pct
        )

        await self.notifier.send_message(msg)

        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="auto_reversal"
        )

        return result
