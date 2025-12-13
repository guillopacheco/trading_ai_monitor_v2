import logging
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("analysis_service")


# ============================================================
# MOTOR TÉCNICO (wrapper interno)
# ============================================================
async def analyze_symbol(symbol: str, direction: str, context: str = "entry") -> dict:
    """
    Ejecuta el motor técnico unificado en contexto dado.
    Esta función NO debe ser usada directamente por otros módulos.
    Usa siempre AnalysisService.
    """
    try:
        logger.info(
            f"🔍 Ejecutando análisis técnico para {symbol} ({direction}) "
            f"[context={context}]..."
        )

        # analyze(symbol, direction_hint=..., context=...)
        result = engine_analyze(
            symbol,
            direction_hint=direction,
            context=context,
        )

        if not result:
            return {"error": True, "msg": "Motor técnico no devolvió resultado"}

        # Normalizar contexto
        result.setdefault("symbol", symbol.upper())
        result.setdefault("direction", direction.lower())
        result.setdefault("context", context)

        return result

    except Exception as e:
        logger.exception(f"❌ Error crítico analizando {symbol}: {e}")
        return {"error": True, "msg": str(e)}


# ============================================================
# FORMATEO PARA TELEGRAM
# ============================================================
def format_analysis_for_telegram(
    symbol: str,
    direction: str,
    result: dict,
    context: str = "entry",
) -> str:
    """
    Formatea el resultado del motor técnico para mostrarlo en Telegram
    de forma clara y compacta.
    """

    if not result or result.get("error"):
        return f"⚠️ No se pudo completar el análisis técnico de {symbol}."

    # Campos base
    decision = (result.get("decision") or "unknown").lower()
    allowed = bool(result.get("allowed", False))

    confidence_raw = result.get("confidence")
    technical_score = result.get("technical_score")
    match_ratio = result.get("match_ratio")
    grade = result.get("grade", "N/D")
    reasons = result.get("decision_reasons") or []

    # Bloque snapshot
    trend_label = result.get("major_trend_label") or "-"
    smart_bias = result.get("smart_bias_code") or result.get("smart_bias") or "-"
    dominant_tf = None
    dominant_reason = None

    timeframes = result.get("timeframes") or []

    # 1️⃣ Si hay divergencias claras, usar ese TF
    for tf in timeframes:
        tf_label = tf.get("tf_label")
        if not tf_label:
            continue

        if tf.get("div_rsi") not in (None, "ninguna"):
            dominant_tf = tf_label
            dominant_reason = f"Divergencia RSI en {tf_label}"
            break

        if tf.get("div_macd") not in (None, "ninguna"):
            dominant_tf = tf_label
            dominant_reason = f"Divergencia MACD en {tf_label}"
            break

    # 2️⃣ Si no hubo divergencia, usar el TF mayor disponible
    if not dominant_tf and timeframes:
        dominant_tf = timeframes[0].get("tf_label")
        dominant_reason = "TF de mayor jerarquía"

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

    context_map = {
        "entry": "Entrada",
        "reactivation": "Reactivación",
        "reentry": "Reentrada",
        "open_position": "Posición abierta",
    }
    context_label = context_map.get(context, context.capitalize())

    direction_label = direction.upper()

    header = f"📊 *Análisis de {symbol.upper()}*"
    if direction_label in ("LONG", "SHORT"):
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

    if trend_label or smart_bias or dominant_tf:
        lines.append("")
        lines.append("📌 *Contexto de tendencia:*")
        if trend_label:
            lines.append(f"• Tendencia mayor: *{trend_label}*")
        if smart_bias:
            lines.append(f"• Smart Bias: `{smart_bias}`")
        if dominant_tf:
            extra = f" ({dominant_reason})" if dominant_reason else ""
            lines.append(f"• TF dominante: *{dominant_tf}*{extra}")

    # Razones de la decisión (si existen)
    if reasons:
        lines.append("")
        lines.append("📌 *Motivos:*")
        for r in reasons:
            lines.append(f"• {r}")

    return "\n".join(lines)


# ============================================================
# ✅ CLASE QUE USA ApplicationLayer y SignalCoordinator
# ============================================================
class AnalysisService:
    """
    Application Service estable para análisis técnico.
    Es el ÚNICO punto de entrada al motor técnico desde la app.
    """

    async def analyze_symbol(
        self,
        symbol: str,
        direction: str,
        context: str = "entry",
    ) -> dict:
        return await analyze_symbol(symbol, direction, context=context)

    async def analyze(
        self,
        symbol: str,
        direction: str,
        context: str = "entry",
    ) -> dict:
        """
        Alias de compatibilidad (por si algún módulo usa .analyze()).
        """
        return await analyze_symbol(symbol, direction, context=context)

    def format_for_telegram(
        self,
        symbol: str,
        direction: str,
        result: dict,
        context: str = "entry",
    ) -> str:
        return format_analysis_for_telegram(symbol, direction, result, context=context)
