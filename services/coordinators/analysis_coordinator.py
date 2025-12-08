# services/coordinators/analysis_coordinator.py

import logging
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService

logger = logging.getLogger("analysis_coordinator")


class AnalysisCoordinator:
    """
    Coordina el análisis técnico completo:
    - validación
    - ejecución del motor técnico
    - formateo del mensaje
    """

    def __init__(self):
        self.analysis = AnalysisService()
        self.signals = SignalService()

    # ============================================================
    # Coordinación del análisis
    # ============================================================

    async def analyze(self, symbol: str, direction: str):
        """
        Ejecuta análisis técnico completo en un solo flujo.
        """
        logger.info(f"🧠 AnalysisCoordinator → Analizando {symbol} ({direction})...")

        # 1) Ejecutar análisis técnico
        result = await self.analysis.analyze_symbol(symbol, direction)

        # 2) Formatear respuesta lista para Telegram
        reply = await self.analysis.format_analysis_for_telegram(result)

        return reply
