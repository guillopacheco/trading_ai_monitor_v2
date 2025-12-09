import logging
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


# ============================================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS
# ============================================================
async def analyze_symbol(symbol: str, direction: str) -> dict:
    """
    Ejecuta el motor técnico unificado para el símbolo solicitado.
    Devuelve un dict estándar para coordinadores y notificaciones.
    """
    try:
        logger.info(f"🔍 Ejecutando análisis técnico para {symbol} ({direction})...")
        result = await engine_analyze(symbol, direction)

        if not result:
            logger.error(f"❌ Motor devolvió None para {symbol}")
            return {"error": True, "msg": "Motor técnico no devolvió resultado"}

        # Normalizar campos que siempre deben existir
        result.setdefault("symbol", symbol)
        result.setdefault("direction", direction)
        result.setdefault("major_trend_label", "N/A")
        result.setdefault("smart_bias_code", "N/A")
        result.setdefault("confidence", 0)
        result.setdefault("grade", "N/A")
        result.setdefault("match_ratio", 0)
        result.setdefault("technical_score", 0)
        result.setdefault("decision", "unknown")
        result.setdefault("decision_reasons", [])
        result.setdefault("entry", {})

        return result

    except Exception as e:
        logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
        return {"error": True, "msg": str(e)}


# ============================================================
# FORMATEAR RESULTADO PARA TELEGRAM
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    """
    Convierte el dict del motor técnico en un bloque estético para Telegram.
    """

    if not result or result.get("error"):
        return "⚠️ *Error en análisis técnico.*"

    try:
        symbol = result.get("symbol")
        direction = result.get("direction")
        main_trend = result.get("major_trend_label")
        smart_bias = result.get("smart_bias_code")
        confidence = result.get("confidence")
        grade = result.get("grade")
        match_ratio = result.get("match_ratio")
        score = result.get("technical_score")
        decision = result.get("decision")
        reasons = result.get("decision_reasons", [])

        entry = result.get("entry", {})
        allowed = entry.get("allowed", False)
        mode = entry.get("entry_mode", "N/A")
        entry_score = entry.get("entry_score", 0)

        msg = (
            f"📊 *Análisis de {symbol} ({direction})*\n"
            f"• Tendencia mayor: *{main_trend}*\n"
            f"• Smart Bias: *{smart_bias}*\n"
            f"• Confianza global: *{confidence}%* (Grado {grade})\n"
            f"• Match técnico: *{match_ratio}%* | Score: *{score}*\n\n"
            f"🎯 *Smart Entry*\n"
            f"• Permitido: *{'Sí' if allowed else 'No'}* (modo: {mode})\n"
            f"• Score entrada: *{entry_score}*\n\n"
            f"📌 *Decisión final*\n"
            f"*{decision.upper()}* — confianza {confidence}%\n"
        )

        if reasons:
            msg += f"• Motivo principal: {reasons[0]}\n"

        return msg

    except Exception as e:
        logger.error(f"❌ Error formateando análisis: {e}")
        return "⚠️ *Error formateando análisis técnico.*"


# ============================================================
# CLASE PARA USO EN COORDINADORES
# ============================================================
class AnalysisService:

    async def analyze(self, symbol: str, direction: str):
        """
        Interface usada por coordinadores.
        """
        return await analyze_symbol(symbol, direction)

    def format(self, result: dict):
        """
        Interface para formateo Telegram.
        """
        return format_analysis_for_telegram(result)
