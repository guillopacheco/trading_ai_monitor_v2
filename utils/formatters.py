"""
utils/formatters.py
--------------------
Formato estándar de mensajes para Telegram (entradas, análisis, alertas, etc.)
"""

from typing import List


# ============================================================
# 🟢 Mensaje de entrada recomendada
# ============================================================
def format_entry_message(symbol: str, direction: str, match: float, grade: str) -> str:
    return (
        f"🟢 **Entrada recomendada**\n\n"
        f"**Par:** {symbol}\n"
        f"**Dirección:** {direction}\n"
        f"**Match Ratio:** {match}%\n"
        f"**Grado:** {grade}\n\n"
        f"📊 El mercado está alineado y confirma la entrada."
    )


# ============================================================
# 🟡 Mensaje de seguimiento
# ============================================================
def format_followup_message(symbol: str, direction: str, match: float, grade: str) -> str:
    return (
        f"🟡 **Señal en seguimiento**\n\n"
        f"Par: {symbol}\n"
        f"Dirección: {direction}\n"
        f"Match Ratio: {match}%\n"
        f"Grado: {grade}\n\n"
        f"⏳ El mercado aún no muestra fuerza suficiente."
    )


# ============================================================
# 🔴 Mensaje de rechazo
# ============================================================
def format_reject_message(symbol: str, direction: str, match: float, grade: str, reason: str) -> str:
    return (
        f"🔴 **Señal no viable por ahora**\n\n"
        f"Par: {symbol}\n"
        f"Dirección: {direction}\n"
        f"Razón: {reason}\n\n"
        f"Match Ratio: {match}%\n"
        f"Grado: {grade}\n"
        f"⚠ Tendencias no alineadas o riesgo elevado."
    )


# ============================================================
# ♻️ Reactivación exitosa
# ============================================================
def format_reactivation_message(symbol: str, direction: str, match: float, grade: str) -> str:
    return (
        f"🟢 **Reactivación exitosa**\n\n"
        f"Par: {symbol}\n"
        f"Dirección: {direction}\n"
        f"Match Ratio:** {match}%**\n"
        f"Grado:** {grade}\n"
        f"✔ Las condiciones ahora son óptimas para entrar."
    )


# ============================================================
# 💀 Reactivación rechazada
# ============================================================
def format_reactivation_reject(symbol: str, direction: str, match: float, grade: str) -> str:
    return (
        f"🔴 **Reactivación rechazada por riesgo de reversión**\n\n"
        f"Par: {symbol}\n"
        f"Dirección: {direction}\n"
        f"Match Ratio:** {match}%**\n"
        f"Grado:** {grade}\n"
        f"⚠ Tendencia en contra."
    )


# ============================================================
# 📉 Mensajes de pérdida progresiva (30/50/70/90%)
# ============================================================
def format_loss_warning(symbol: str, pnl_pct: float, level: int) -> str:
    icons = {
        30: "🟡",
        50: "🟠",
        70: "🔴",
        90: "⚫"
    }
    return (
        f"{icons[level]} **Alerta de pérdida {level}%**\n\n"
        f"{symbol} está en {pnl_pct}%.\n"
        f"Se analizará la tendencia para determinar si cerrar o mantener."
    )


# ============================================================
# 🔄 Mensaje de análisis de reversión
# ============================================================
def format_reversal_analysis(symbol: str, direction: str, match: float, grade: str, decision: str) -> str:
    return (
        f"📉 **Análisis de reversión — {symbol}**\n\n"
        f"Dirección: {direction}\n"
        f"Match Ratio: {match}%\n"
        f"Grado: {grade}\n"
        f"Decisión: {decision}\n"
    )

"""
utils/formatters.py
-------------------
Formateadores de texto usados por el motor técnico y los controllers.
"""

# ============================================================
# 🔵 Format: match ratio
# ============================================================

def format_match_ratio_text(match_ratio: float) -> str:
    """
    Devuelve texto formateado del match ratio, con emoji según fuerza.
    """
    ratio = round(match_ratio, 2)

    if ratio >= 80:
        emoji = "🟢"
    elif ratio >= 65:
        emoji = "🟡"
    elif ratio >= 50:
        emoji = "🟠"
    else:
        emoji = "🔴"

    return f"{emoji} *Match Ratio:* `{ratio}%`"


# ============================================================
# 🔵 Format: recommendation
# ============================================================

def format_recommendation_text(rec: dict) -> str:
    """
    Formatea recomendación:
        { allowed: bool, quality: "A/B/C/D", reason: "..."}
    """
    allowed = rec.get("allowed", False)
    quality = rec.get("quality", "?")
    reason = rec.get("reason", "")

    if allowed:
        status_emoji = "✅"
    else:
        status_emoji = "⚠️"

    return (
        f"{status_emoji} *Recomendación:* `{quality}`\n"
        f"└ {reason}"
    )
    
# ============================================================
# 🔵 Format: mensaje introductorio de nueva señal
# ============================================================

def format_signal_intro(symbol: str, direction: str) -> str:
    """
    Formato para cuando llega una nueva señal del canal VIP.
    """
    direction_arrow = "📈" if direction == "long" else "📉"

    return (
        f"📩 *Nueva señal detectada*\n"
        f"▪ *Par:* `{symbol}`\n"
        f"▪ *Dirección:* {direction_arrow} `{direction.upper()}`\n"
    )


# ============================================================
# 🔵 Format: datos del parser de señal
# ============================================================

def format_parsed_signal(parsed: dict) -> str:
    """
    Muestra lo que se pudo extraer del texto crudo.
    """
    symbol = parsed.get("symbol")
    direction = parsed.get("direction")
    entry = parsed.get("entry")
    tp_list = parsed.get("tp_list", [])
    sl = parsed.get("sl")

    tps_formatted = ", ".join([str(tp) for tp in tp_list]) if tp_list else "N/A"
    sl_formatted = sl if sl else "N/A"

    return (
        f"📝 *Detalles de la señal:*\n"
        f"▪ Par: `{symbol}`\n"
        f"▪ Dirección: `{direction}`\n"
        f"▪ Entrada: `{entry}`\n"
        f"▪ TPs: `{tps_formatted}`\n"
        f"▪ SL: `{sl_formatted}`"
    )

# ============================================================
# 📌 FORMATO DE ENCABEZADO DE SEÑAL
# ============================================================

def format_signal_intro(symbol: str, direction: str) -> str:
    arrow = "📈 LONG" if direction.lower() == "long" else "📉 SHORT"
    return f"📌 *Señal detectada* — {symbol}\n{arrow}"


# ============================================================
# 📌 RESUMEN PREMIUM DEL ANÁLISIS TÉCNICO
# ============================================================

def format_analysis_summary(
    symbol: str,
    direction: str,
    match_ratio: float,
    technical_score: float,
    grade: str,
    decision: str,
    emoji: str,
) -> str:
    """
    Resumen estándar para enviar a Telegram.
    """
    dir_txt = "LONG 📈" if direction.lower() == "long" else "SHORT 📉"

    return (
        f"🎯 *Análisis de {symbol}*\n"
        f"Dirección: *{dir_txt}*\n\n"
        f"📊 *Match Ratio:* {match_ratio:.1f}%\n"
        f"📈 *Puntaje Técnico:* {technical_score:.1f}/100\n"
        f"💠 *Calificación:* {grade}\n\n"
        f"🔎 *Decisión:* {decision.upper()} {emoji}\n"
    )
