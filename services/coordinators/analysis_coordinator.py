import logging
from services.application.analysis_service import (
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
            # 1️⃣ Ejecutar análisis real
            result = await self.analysis_service.analyze(symbol, direction)

            # 2️⃣ Formatear usando función EXISTENTE
            text = format_analysis_for_telegram(result)

            # 3️⃣ Enviar usando método REAL del notifier
            await self.notifier.send(text)

        except Exception as e:
            logger.error(
                f"❌ Error en análisis bajo demanda para {symbol}: {e}", exc_info=True
            )
            await self.notifier.send(f"❌ Error analizando {symbol}")
