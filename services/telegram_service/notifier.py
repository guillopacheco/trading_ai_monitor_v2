import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

logger = logging.getLogger("notifier")

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def clean_markdown(text: str) -> str:
    """
    Sanitiza texto para Markdown de Telegram.
    Evita errores por caracteres especiales.
    """
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
    """Divide mensajes largos en bloques seguros para Telegram."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:]
    parts.append(text)
    return parts

# ================================================================
# 🔧 Envío base (síncrono)
# ================================================================
def _post(text: str):
    """Envío seguro con sanitización y fragmentación automática."""
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

# ================================================================
# 📤 Envío público (síncrono compatible con asyncio.to_thread)
# ================================================================
def send_message(text: str):
    """
    Versión SÍNCRONA — diseñada para ejecutarse así:
        await asyncio.to_thread(send_message, texto)
    """
    return _post(text)


# ================================================================
# 📈 Notificación de análisis técnico
# ================================================================
def notify_analysis_result(result: dict):
    """
    Notificación simple basada en el motor técnico unificado.
    """
    symbol = result.get("symbol", "???")
    direction = result.get("direction_hint", "???")
    match_ratio = result.get("match_ratio", 0)
    decision = result.get("decision", "unknown")

    text = (
        f"📊 *Análisis de {symbol}*\n"
        f"🔹 Dirección: {direction}\n"
        f"🔹 Match: {match_ratio:.1f}%\n"
        f"📌 Decisión: *{decision.upper()}*"
    )

    _post(text)

# ================================================================
# 🚨 Notificación de alerta de operación
# ================================================================
def notify_operation_alert(symbol, direction, roi, pnl, loss_pct, decision, reasons):
    reason_lines = "\n - ".join(reasons) if reasons else "Sin detalles."

    msg = (
        f"🚨 *Reversión peligrosa detectada en {symbol}*\n"
        f"🔹 Dirección: {direction.upper()}\n"
        f"💵 ROI: {roi:.2f}%\n"
        f"📉 Pérdida real: {loss_pct:.2f}%\n"
        f"🧠 *Decisión:* {decision}\n"
        f"📝 *Motivos:* \n - {reason_lines}"
    )

    _post(msg)

def notify_profit_update(text_block: str):
    text = f"🎯 *Profit update detectado:*\n\n{text_block}"
    _post(text)

