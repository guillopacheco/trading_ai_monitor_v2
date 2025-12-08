# services/coordinators/analysis_coordinator.py

import logging
from services.application.analysis_service import AnalysisService

logger = logging.getLogger("analysis_coordinator")


class AnalysisCoordinator:
    """
    Coordina el análisis técnico completo:
    - ejecución del motor técnico
    - formateo de mensaje
    - opcional: retorno del análisis crudo
    """

    def __init__(self):
        self.analysis = AnalysisService()

    # ============================================================
    # 1. Análisis completo (texto para Telegram)
    # ============================================================
    async def analyze(self, symbol: str, direction: str):
        """
        Ejecuta análisis técnico y devuelve texto listo para Telegram.
        """
        logger.info(f"🧠 AnalysisCoordinator → Analizando {symbol} ({direction})...")

        result = await self.analysis.analyze_symbol(symbol, direction)
        formatted = await self.analysis.format_analysis_for_telegram(result)

        return formatted

    # ============================================================
    # 2. Análisis crudo (útil para reactivaciones y monitoreo)
    # ============================================================
    async def analyze_raw(self, symbol: str, direction: str):
        """
        Devuelve el JSON completo generado por el motor técnico.
        """
        logger.info(f"🧠 AnalysisCoordinator → Análisis RAW {symbol} ({direction})...")

        return await self.analysis.analyze_symbol(symbol, direction)
