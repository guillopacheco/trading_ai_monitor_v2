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

        # Asegurar que el resultado tiene la estructura esperada
        # El motor devuelve varios niveles: snapshot, decision, etc.
        return result

    except Exception as e:
        logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
        return {"error": True, "msg": str(e)}

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
# FORMATEAR RESULTADO PARA TELEGRAM - CORREGIDO
# ============================================================
def format_analysis_for_telegram(result: dict) -> str:
    """
    Convierte el dict del motor técnico en un bloque estético para Telegram.
    AHORA maneja la estructura anidada del motor unificado.
    """
    if not result or result.get("error"):
        return "⚠️ *Error en análisis técnico.*"

    try:
        # El motor devuelve estructura anidada:
        # {
        #   "symbol": "...",
        #   "snapshot": {...},
        #   "decision": {...},
        #   "smart_entry": {...}
        # }
        
        # Extraer valores de SNAPSHOT
        snapshot = result.get("snapshot", {})
        symbol = snapshot.get("symbol", result.get("symbol", "N/A"))
        direction_hint = result.get("direction_hint", "N/A")
        
        # Valores principales del snapshot
        major_trend = snapshot.get("major_trend_label", snapshot.get("major_trend", "N/A"))
        smart_bias = snapshot.get("smart_bias_code", snapshot.get("smart_bias", "N/A"))
        match_ratio = float(snapshot.get("match_ratio", 0))
        technical_score = float(snapshot.get("technical_score", 0))
        grade = snapshot.get("grade", "N/A")
        confidence = float(snapshot.get("confidence", 0))
        
        # Extraer valores de DECISION
        decision_block = result.get("decision", {})
        decision = decision_block.get("decision", "unknown")
        decision_reasons = decision_block.get("decision_reasons", [])
        allowed = decision_block.get("allowed", False)
        
        # Extraer valores de SMART ENTRY
        entry_block = result.get("smart_entry", {})
        entry_allowed = entry_block.get("entry_allowed", False)
        entry_mode = entry_block.get("entry_mode", "N/A")
        entry_score = float(entry_block.get("entry_score", 0))
        entry_grade = entry_block.get("entry_grade", "N/A")

        # Formatear mensaje
        msg = (
            f"📊 *Análisis de {symbol} ({direction_hint})*\n"
            f"• Tendencia mayor: *{major_trend}*\n"
            f"• Smart Bias: *{smart_bias}*\n"
            f"• Confianza global: *{confidence*100:.1f}%* (Grado {grade})\n"
            f"• Match técnico: *{match_ratio:.1f}%* | Score: *{technical_score:.1f}*\n\n"
            f"🎯 *Smart Entry*\n"
            f"• Permitido: *{'Sí' if entry_allowed else 'No'}* (modo: {entry_mode})\n"
            f"• Score entrada: *{entry_score:.1f}* (Grado {entry_grade})\n\n"
            f"📌 *Decisión final*\n"
            f"*{decision.upper()}* — permitido: {'Sí' if allowed else 'No'}\n"
        )

        if decision_reasons and isinstance(decision_reasons, list) and len(decision_reasons) > 0:
            msg += f"• Motivo: {decision_reasons[0]}\n"
            if len(decision_reasons) > 1:
                msg += f"• Razón adicional: {decision_reasons[1]}\n"

        return msg

    except Exception as e:
        logger.error(f"❌ Error formateando análisis: {e}", exc_info=True)
        # Fallback simple
        return f"📊 *Análisis técnico completado*\n• Símbolo: {result.get('symbol', 'N/A')}\n• Decisión: {result.get('decision', {}).get('decision', 'N/A')}"


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
