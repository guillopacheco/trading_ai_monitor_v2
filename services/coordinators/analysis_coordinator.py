import logging
from services.application.analysis_service import analyze_symbol, format_analysis_for_telegram

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
    async def analyze_request(self, symbol: str, direction: str, chat_id: int):
        try:
            result = await self.analysis_service.analyze(symbol, direction)
            text = format_analysis_for_telegram(result)

            await self.notifier.safe_send(chat_id, text)

        except Exception as e:
            logger.error(f"❌ Error en análisis bajo demanda para {symbol}: {e}")
            await self.notifier.safe_send(chat_id, f"❌ Error analizando {symbol}")
