import logging
from services.application.analysis_service import analyze_symbol, format_analysis_for_telegram

logger = logging.getLogger("analysis_coordinator")


class AnalysisCoordinator:

    async def analyze(self, symbol: str, direction: str) -> str:
        """
        Coordinador de análisis bajo demanda (/analizar).
        Retorna el mensaje listo para Telegram.
        """
        logger.info(f"[Coordinator] Ejecutando análisis para {symbol} {direction}")

        result = await analyze_symbol(symbol, direction)
        msg = format_analysis_for_telegram(result)
        return msg
