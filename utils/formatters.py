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
    