# services/application/analysis_service.py
import logging
import inspect

from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


class AnalysisService:
    async def analyze_symbol(
        self, symbol: str, direction: str, context: str = "entry"
    ) -> dict:
        """
        Ejecuta el motor técnico y siempre retorna dict (nunca coroutine).
        """
        try:
            logger.info(
                f"🔍 Ejecutando análisis técnico para {symbol} ({direction})..."
            )

            result = engine_analyze(symbol=symbol, direction=direction, context=context)

            # ✅ Compatibilidad total: si el motor es async, lo await; si es sync, lo dejo.
            if inspect.isawaitable(result):
                result = await result

            if not isinstance(result, dict):
                raise TypeError(
                    f"technical_engine.analyze devolvió {type(result)} (se esperaba dict)"
                )

            return result

        except Exception as e:
            logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
            return {
                "allowed": False,
                "decision": "error",
                "decision_reasons": [f"Error crítico analizando {symbol}: {e}"],
                "symbol": symbol,
                "direction_hint": direction,
                "context": context,
                "confidence": 0.0,
                "match_ratio": 0.0,
                "technical_score": 0.0,
                "grade": "D",
            }
