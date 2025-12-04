import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("notifier")

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def clean_markdown(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
            .replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
    )


def split_message(text: str, limit: int = 4000):
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:]
    parts.append(text)
    return parts


def _post(text: str):
    if SIMULATION_MODE:
        logger.info(f"💬 [SIMULADO] {text}")
        return True

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no configurados.")
        return False

    try:
        text = clean_markdown(text)
        parts = split_message(text)

        ok = True
        for part in parts:
            r = requests.post(
                API_URL,
                data={
                    "chat_id": TELEGRAM_USER_ID,
                    "text": part,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=10
            )
            if r.status_code != 200:
                ok = False
                logger.error(f"❌ Error Telegram: {r.text}")

        return ok

    except Exception as e:
        logger.error(f"❌ Error en _post Telegram: {e}")
        return False


def send_message(text: str):
    return _post(text)


# ================================================================
# 🧠 NUEVO: Notificación final para operaciones abiertas
# ================================================================
def notify_operation_recommendation(data: dict):
    """
    Envía una notificación clara con la recomendación:
    🟢 Mantener | 🔴 Cerrar | ⚠️ Revertir | 🟡 Evaluar
    """
    symbol = data["symbol"]
    direction = data["direction"]
    roi = data["roi"]
    pnl = data["pnl"]
    loss_level = data["loss_level"]
    match_ratio = data["match_ratio"]
    major_trend = data["major_trend"]
    bias = data["smart_bias"]
    suggestion = data["suggestion"]
    reasons = data["reasons"]

    reason_text = "\n - ".join(reasons) if reasons else "Sin razones adicionales."

    msg = f"""
🚨 *Alerta de operación: {symbol}*
📌 Dirección: *{direction.upper()}*
💵 ROI: `{roi:.2f}%`
💰 PnL: `{pnl}`
📉 Nivel de pérdida: {loss_level}%
📊 Match técnico: {match_ratio:.1f}%
🧭 Tendencia mayor: *{major_trend}*
🔮 Sesgo smart: *{bias}*
🧠 *Recomendación:* {suggestion}

📝 *Motivos:*
 - {reason_text}
"""

    _post(msg.strip())
