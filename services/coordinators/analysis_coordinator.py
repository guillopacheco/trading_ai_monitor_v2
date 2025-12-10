import logging
from services.application.analysis_service import (
    analyze_symbol,
    format_analysis_for_telegram,
)

logger = logging.getLogger("analysis_coordinator")


class AnalysisCoordinator:
    """
    Responsable de coordinar análisis bajo demanda de símbolos.
    """

    def __init__(self, analysis_service, notifier):
        self.analysis_service = analysis_service
        self.notifier = notifier

    # -----------------------------------------------------------
    # Análisis bajo demanda desde comandos
    # -----------------------------------------------------------
    async def analyze_request(self, symbol, direction, chat_id):
        try:
            result = await self.analysis_service.analyze(symbol, direction)

            text = self._format_analysis(result)
            await self.notifier.send_message(text)

        except Exception as e:
            logger.error(f"❌ Error en análisis bajo demanda para {symbol}: {e}")
            await self.notifier.send_message(f"❌ Error analizando {symbol}")
