# services/coordinators/signal_coordinator.py

import logging
from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.telegram_service.notifier import Notifier

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina:
    • análisis manual de señales (/analizar)
    • registro y análisis de señales recibidas por Telegram
    • reactivación automática
    • reactivación manual
    """

    def __init__(self, signal_service: SignalService, analysis_service: AnalysisService, notifier: Notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.notifier = notifier

    # ============================================================
    # 1. ANÁLISIS MANUAL /analizar
    # ============================================================
    async def analyze_signal(self, symbol: str, direction: str):
        """
        Análisis técnico solicitado por usuario (bot).
        """
        analysis = await self.analysis_service.run(symbol, direction, context="entry")

        msg = self.analysis_service.format_for_telegram(
            symbol, direction, analysis,
            header="📊 Análisis técnico"
        )

        return msg

    # ============================================================
    # 2. PROCESAR SEÑAL RECIBIDA POR TELEGRAM
    # ============================================================
    async def process_telegram_signal(self, symbol: str, direction: str, raw_text: str):
        """
        Registrada desde telegram_reader cuando llega una nueva señal.
        """
        signal_id = self.signal_service.register_signal(symbol, direction, raw_text)

        # Analizar de inmediato
        analysis = await self.analysis_service.run(symbol, direction, context="entry")

        # Guardar log técnico de la entrada
        self.signal_service.save_analysis_log(signal_id, analysis, context="entry")

        # Respuesta para el canal del usuario
        msg = self.analysis_service.format_for_telegram(
            symbol, direction, analysis,
            header="📡 Señal recibida + análisis"
        )

        # Enviar notificación
        await self.notifier.send_message(msg)

        return msg

    # ============================================================
    # 3. REACTIVACIÓN AUTOMÁTICA (cada 60s)
    # ============================================================
    async def auto_reactivate(self):
        """
        Llamado por signal_reactivation_sync.
        """
        pending = self.signal_service.get_pending_signals()
        if not pending:
            logger.info("♻️ No hay señales pendientes para reactivación.")
            return

        logger.info(f"♻️ Reactivando {len(pending)} señales pendientes...")

        for signal in pending:
            try:
                await self._evaluate_reactivation(signal)
            except Exception as e:
                logger.error(f"❌ Error evaluando {signal['symbol']}: {e}", exc_info=True)

    # ============================================================
    # 4. Evaluar una señal para reactivación
    # ============================================================
    async def _evaluate_reactivation(self, record: dict):
        symbol = record["symbol"]
        direction = record["direction"]
        signal_id = record["id"]

        logger.info(f"🔎 Reactivación → {symbol} ({direction})")

        # Ejecutar análisis técnico
        analysis = await self.analysis_service.run(symbol, direction, context="reactivation")

        # Registrar análisis
        self.signal_service.save_analysis_log(signal_id, analysis, context="reactivation")

        # Preparar mensaje para Telegram
        msg = self.analysis_service.format_for_telegram(
            symbol, direction, analysis,
            header="♻️ Evaluación de reactivación"
        )
        await self.notifier.send_message(msg)

        # Motor indica reactivación
        if analysis.get("decision") == "reactivate":
            self.signal_service.mark_reactivated(signal_id)
            logger.info(f"⚡ Señal reactivada automáticamente: {symbol} {direction}")

        return msg

    # ============================================================
    # 5. REACTIVACIÓN MANUAL (/reactivar <symbol>)
    # ============================================================
    async def manual_reactivate(self, symbol: str):
        pending = self.signal_service.get_pending_signals()

        target = next((s for s in pending if s["symbol"].lower() == symbol.lower()), None)

        if not target:
            return f"⚠️ No hay señal pendiente para {symbol}."

        return await self._evaluate_reactivation(target)
