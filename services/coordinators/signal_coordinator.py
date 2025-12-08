# ===============================================================
#  Signal Coordinator
#  Coordina la recepción, análisis y almacenamiento de señales
#  Fase 4 – Arquitectura Empresarial
# ===============================================================

import logging
from typing import Dict, Optional

from services.signals_service.signal_service import SignalService
from services.technical_engine.technical_engine import analyze as engine_analyze
from services.analysis_service.analysis_service import AnalysisService
from services.notifier_service.notifier import Notifier
from services.database_service.database import Database

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:

    def __init__(
        self,
        signal_service: SignalService,
        analysis_service: AnalysisService,
        notifier: Notifier,
        database: Database
    ):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.notifier = notifier
        self.db = database

    # ===========================================================
    # 1) Entrada principal desde TelegramReader
    # ===========================================================
    async def process_raw_signal(self, signal: Dict):
        """
        Recibe una señal cruda desde telegram_reader, la valida,
        la guarda y ejecuta el análisis automático.
        """

        logger.info(f"📩 Coordinador recibió señal: {signal}")

        # -------------------------------------------------------
        # Normalizar + Guardar señal
        # -------------------------------------------------------
        saved = self.signal_service.save_signal(signal)

        if not saved:
            logger.warning("❌ No se pudo guardar la señal. Abortando flujo.")
            return

        symbol = saved["symbol"]
        direction = saved["direction"]

        # -------------------------------------------------------
        # Análisis técnico automático
        # -------------------------------------------------------
        logger.info(f"🔍 Ejecutando análisis técnico inicial para {symbol} ({direction})...")
        engine_result = await engine_analyze(symbol, direction, context="entry")

        # -------------------------------------------------------
        # Construir mensaje final para Telegram
        # -------------------------------------------------------
        msg = self.analysis_service.build_analysis_message(
            symbol=symbol,
            direction=direction,
            analysis=engine_result,
            context="entry"
        )

        # -------------------------------------------------------
        # Enviar notificación
        # -------------------------------------------------------
        await self.notifier.send_message(msg)

        # -------------------------------------------------------
        # Registrar en DB el análisis inicial
        # -------------------------------------------------------
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=engine_result.get("match_ratio"),
            technical_score=engine_result.get("technical_score"),
            grade=engine_result.get("grade"),
            context="entry"
        )

        # -------------------------------------------------------
        # Activar reactivación automática si aplica
        # -------------------------------------------------------
        if not engine_result.get("allowed", False):
            logger.info(f"⏳ Señal {symbol} pendiente → entrando a cola de reactivación.")
            self.signal_service.mark_pending(symbol)
        else:
            logger.info(f"✅ Señal {symbol} ya validada: entrada sólida → no requiere reactivación.")

    # ===========================================================
    # 2) Para reactivación manual (desde /reactivar)
    # ===========================================================
    async def manual_reactivation(self, symbol: str):
        """
        Permite reactivar una señal por comando del usuario.
        """

        logger.info(f"♻️ Reactivación manual solicitada para {symbol}")

        direction = self.signal_service.get_direction(symbol)
        if not direction:
            await self.notifier.send_message(f"⚠️ No existe señal previa para {symbol}.")
            return

        # Ejecutar motor técnico
        result = await engine_analyze(symbol, direction, context="reactivation")

        # Construir mensaje
        msg = self.analysis_service.build_analysis_message(
            symbol=symbol,
            direction=direction,
            analysis=result,
            context="reactivation"
        )

        # Enviar feedback
        await self.notifier.send_message(msg)

        # Actualizar DB
        self.db.save_analysis_record(
            symbol=symbol,
            direction=direction,
            match_ratio=result.get("match_ratio"),
            technical_score=result.get("technical_score"),
            grade=result.get("grade"),
            context="reactivation"
        )

        # Actualizar estado
        if result.get("allowed"):
            self.signal_service.mark_activated(symbol)
            await self.notifier.send_message(f"✅ {symbol} reactivada exitosamente.")
        else:
            self.signal_service.mark_pending(symbol)
            await self.notifier.send_message(f"⏳ {symbol} sigue pendiente para reactivación.")

