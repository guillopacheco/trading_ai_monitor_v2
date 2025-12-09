import logging
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


# ============================================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS
# ============================================================
async def analyze_symbol(symbol: str, direction: str) -> dict:
    """
    Ejecuta el motor técnico unificado para el símbolo solicitado.
    """
    logger.info(f"🔍 Ejecutando análisis técnico para {symbol} ({direction})...")
    result = await engine_analyze(symbol, direction)
    return result


# ============================================================
# FORMATEAR RESULTADO PARA TELEGRAM
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    """
    Convierte el dict del motor técnico en un mensaje legible para Telegram.
    """

    if not result:
        return "⚠️ Error: Sin resultados de análisis."

    try:
        symbol = result.get("symbol", "N/A")
        direction = result.get("direction", "N/A")
        main_trend = result.get("major_trend_label", "N/A")
        smart_bias = result.get("smart_bias_code", "N/A")
        confidence = result.get("confidence", 0)
        grade = result.get("grade", "N/A")
        match_ratio = result.get("match_ratio", 0)
        score = result.get("technical_score", 0)
        decision = result.get("decision", "N/A")
        decision_reasons = result.get("decision_reasons", [])
        entry = result.get("entry", {}) or {}
        entry_allowed = entry.get("allowed", False)
        entry_mode = entry.get("entry_mode", "N/A")
        entry_score = entry.get("entry_score", 0)

        analysis = (
            f"📊 *Análisis de {symbol} ({direction})*\n"
            f"• Tendencia mayor: *{main_trend}*\n"
            f"• Smart Bias: *{smart_bias}*\n"
            f"• Confianza global: *{confidence}* (Grado {grade})\n"
            f"• Match técnico: *{match_ratio}%* | Score: *{score}*\n\n"
            f"🎯 *Smart Entry*\n"
            f"• Permitido: *{'Sí' if entry_allowed else 'No'}* "
            f"(modo: {entry_mode})\n"
            f"• Score entrada: *{entry_score}*\n\n"
            f"📌 *Decisión final del motor*\n"
            f"• Decisión: *{decision}* ({confidence} confianza)\n"
        )

        if decision_reasons:
            analysis += "• Motivo principal: " + decision_reasons[0]

        return analysis

    except Exception as e:
        logger.error(f"❌ Error formateando análisis: {e}")
        return "⚠️ Error formateando análisis técnico."


# ============================================================
# CLASE OPCIONAL PARA USO DESDE COORDINADORES
# ============================================================
class AnalysisService:

    async def analyze(self, symbol: str, direction: str):
        return await analyze_symbol(symbol, direction)

    def format(self, result: dict):
        return format_analysis_for_telegram(result)
