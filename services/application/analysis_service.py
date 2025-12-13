# services/application/analysis_service.py
import logging
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


class AnalysisService:
    async def analyze_symbol(
        self, symbol: str, direction: str, context: str = "entry"
    ) -> dict:
        try:
            # Compatibilidad: algunos motores esperan direction (posicional),
            # otros esperan direction_hint (kw). Probamos primero kw y hacemos fallback.
            try:
                result = engine_analyze(
                    symbol=symbol, direction_hint=direction, context=context
                )
            except TypeError:
                result = engine_analyze(symbol, direction, context=context)

            # Normalizar: si el motor devuelve un dict “final decision” o un “unified dict”
            # lo devolvemos tal cual (CommandBot ya soporta ambos)
            return result

        except Exception as e:
            logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "decision": {"decision": "error"},
            }
