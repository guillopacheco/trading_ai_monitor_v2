import logging
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


# ============================================================
# FUNCIÓN INTERNA (motor técnico)
# ============================================================
async def analyze_symbol(symbol: str, direction: str) -> dict:
    """
    Ejecuta el motor técnico unificado.
    Esta función NO debe ser usada directamente por otros módulos.
    """
    try:
        logger.info(f"🔍 Ejecutando análisis técnico para {symbol} ({direction})...")
        result = await engine_analyze(symbol, direction)

        if not result:
            return {"error": True, "msg": "Motor técnico no devolvió resultado"}

        return result

    except Exception as e:
        logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
        return {"error": True, "msg": str(e)}


# ============================================================
# FORMATEO PARA TELEGRAM
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    if not result or result.get("error"):
        return "⚠️ Error en análisis técnico."

    try:
        symbol = result.get("symbol", "N/A")
        decision = result.get("decision", "N/A")
        confidence = result.get("confidence", 0)

        return (
            f"📊 *Análisis de {symbol}*\n"
            f"📌 Decisión: *{decision}*\n"
            f"🔎 Confianza: *{confidence}%*"
        )

    except Exception as e:
        logger.error(f"❌ Error formateando análisis: {e}")
        return "⚠️ Error formateando análisis."


# ============================================================
# ✅ CLASE QUE ESPERA ApplicationLayer
# ============================================================
class AnalysisService:
    """
    Application Service estable para análisis técnico.
    Es el ÚNICO punto de entrada al motor técnico.
    """

    async def analyze(self, symbol: str, direction: str) -> dict:
        return await analyze_symbol(symbol, direction)

    def format(self, result: dict) -> str:
        return format_analysis_for_telegram(result)
