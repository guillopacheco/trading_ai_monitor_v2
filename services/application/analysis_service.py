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
        result = engine_analyze(symbol, direction)

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
    """
    Formatea el resultado del motor técnico para mostrarlo en Telegram
    de forma clara y compacta.
    """
    if not result or result.get("error"):
        return "⚠️ No se pudo completar el análisis técnico."

    # Campos base
    symbol = result.get("symbol", "N/D")
    direction = result.get("direction", "").upper()
    context = result.get("context", "entry")

    decision = (result.get("decision") or "unknown").lower()
    allowed = bool(result.get("allowed", False))

    confidence_raw = result.get("confidence")
    technical_score = result.get("technical_score")
    match_ratio = result.get("match_ratio")
    grade = result.get("grade", "N/D")
    reasons = result.get("decision_reasons") or []

    # Normalizar confianza (0.6 → 60 %)
    if confidence_raw is None:
        confidence_str = "N/D"
    else:
        try:
            val = float(confidence_raw)
            if val <= 1:
                val *= 100.0
            confidence_str = f"{val:.0f} %"
        except Exception:
            confidence_str = str(confidence_raw)

    # Normalizar score
    if technical_score is None:
        score_str = "N/D"
    else:
        try:
            score_str = f"{float(technical_score):.0f} / 100"
        except Exception:
            score_str = str(technical_score)

    # Normalizar match_ratio
    if match_ratio is None:
        match_str = "N/D"
    else:
        try:
            m = float(match_ratio)
            if m <= 1:
                m *= 100.0
            match_str = f"{m:.0f} %"
        except Exception:
            match_str = str(match_ratio)

    # Mapear decisión a icono + texto
    if allowed and decision in ("enter", "long", "short", "reenter", "reactivate"):
        decision_icon = "🟢"
        decision_label = "Escenario favorable"
    elif decision in ("hold", "monitor"):
        decision_icon = "🟡"
        decision_label = "Observar / mantener"
    elif decision in ("close", "exit", "reverse"):
        decision_icon = "🟠"
        decision_label = "Riesgo alto – considerar salida"
    elif decision == "skip":
        decision_icon = "🔴"
        decision_label = "Evitar entrada"
    else:
        decision_icon = "⚪"
        decision_label = decision.upper()

    # Contexto legible
    context_map = {
        "entry": "Entrada",
        "reactivation": "Reactivación",
        "reentry": "Reentrada",
        "open_position": "Posición abierta",
    }
    context_label = context_map.get(context, context.capitalize())

    # Dirección legible
    if direction in ("LONG", "SHORT"):
        direction_label = direction
    else:
        direction_label = "N/D"

    # Construir texto principal
    header = f"📊 *Análisis de {symbol}*"
    if direction_label != "N/D":
        header += f" ({direction_label})"

    lines = [
        header,
        f"🧭 Contexto: *{context_label}*",
        "",
        f"{decision_icon} *Decisión:* `{decision}` — {decision_label}",
        f"📈 *Score técnico:* {score_str}",
        f"🎯 *Match técnico:* {match_str}",
        f"🔎 *Confianza:* {confidence_str}",
        f"🏅 *Grade:* {grade}",
    ]

    # Razones de la decisión (si existen)
    if reasons:
        lines.append("")
        lines.append("📌 *Motivos:*")
        for r in reasons:
            lines.append(f"• {r}")

    return "\n".join(lines)


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
