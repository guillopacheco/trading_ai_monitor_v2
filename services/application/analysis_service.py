import logging
from services.technical_engine.motor_wrapper import analyze as engine_analyze

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
        # ¡QUITAR AWAIT! engine_analyze es función normal
        result = engine_analyze(symbol, direction)

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
# FORMATEAR RESULTADO PARA TELEGRAM - CON MEJOR MANEJO DE ERRORES
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    """
    Convierte el dict del motor técnico en un bloque estético para Telegram.
    """

    if not result or result.get("error"):
        return "⚠️ *Error en análisis técnico.*"

    try:
        # Asegurarse de que symbol sea string
        symbol = str(result.get("symbol", "N/A")).upper()
        direction = str(result.get("direction", "N/A"))
        
        # Extraer valores con defaults seguros
        main_trend = str(result.get("major_trend_label", "N/A"))
        smart_bias = str(result.get("smart_bias_code", result.get("smart_bias", "N/A")))
        
        # Valores numéricos con conversión segura
        confidence = float(result.get("confidence", 0))
        match_ratio = float(result.get("match_ratio", 0))
        score = float(result.get("technical_score", 0))
        
        grade = str(result.get("grade", "N/A"))
        decision = str(result.get("decision", "unknown"))
        reasons = result.get("decision_reasons", [])
        
        entry = result.get("entry", {})
        if isinstance(entry, dict):
            allowed = entry.get("allowed", False)
            mode = entry.get("entry_mode", "N/A")
            entry_score = float(entry.get("entry_score", 0))
        else:
            allowed = False
            mode = "N/A"
            entry_score = 0

        msg = (
            f"📊 *Análisis de {symbol} ({direction})*\n"
            f"• Tendencia mayor: *{main_trend}*\n"
            f"• Smart Bias: *{smart_bias}*\n"
            f"• Confianza global: *{confidence:.1f}%* (Grado {grade})\n"
            f"• Match técnico: *{match_ratio:.1f}%* | Score: *{score:.1f}*\n\n"
            f"🎯 *Smart Entry*\n"
            f"• Permitido: *{'Sí' if allowed else 'No'}* (modo: {mode})\n"
            f"• Score entrada: *{entry_score:.1f}*\n\n"
            f"📌 *Decisión final*\n"
            f"*{decision.upper()}* — confianza {confidence:.1f}%\n"
        )

        if reasons and isinstance(reasons, list) and len(reasons) > 0:
            msg += f"• Motivo principal: {reasons[0]}\n"

        return msg

    except Exception as e:
        logger.error(f"❌ Error formateando análisis: {e}")
        return f"⚠️ *Error formateando análisis técnico: {str(e)[:50]}...*"

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
