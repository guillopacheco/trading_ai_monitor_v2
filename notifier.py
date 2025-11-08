# notifier.py (versión estable y completa)
import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("notifier")

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def _post(text: str):
    if SIMULATION_MODE:
        logger.info(f"💬 [SIMULADO] {text}")
        return True
    try:
        r = requests.post(API_URL, data={
            "chat_id": TELEGRAM_USER_ID,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
        if r.status_code == 200:
            logger.info("📨 Mensaje enviado correctamente")
            return True
        logger.error(f"❌ Error enviando mensaje: {r.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Error en envío Telegram: {e}")
        return False

# ---------------------------
# Públicos
# ---------------------------

def send_message(text: str):
    """Mensaje libre."""
    return _post(text)

def notify_analysis_result(symbol, direction, leverage, match_ratio, recommendation):
    """Resumen del análisis técnico."""
    text = (
        f"📊 *Análisis de {symbol}*\n"
        f"🔹 *Dirección:* {direction.upper()} (x{leverage})\n"
        f"🔹 *Coincidencia técnica:* {match_ratio:.2f}\n"
        f"📌 *Recomendación:* {recommendation}"
    )
    _post(text)

def notify_operation_alert(symbol, direction, roi, loss_level, volatility, suggestion):
    """Alerta de operación abierta en riesgo."""
    text = (
        f"⚠️ *ALERTA DE OPERACIÓN*\n\n"
        f"🪙 *Par:* {symbol}\n"
        f"📈 *Dirección:* {direction.upper()}\n"
        f"💰 *ROI actual:* {roi:.2f}%\n"
        f"📊 *Nivel de pérdida:* {loss_level}%\n"
        f"🌡️ *Volatilidad:* {volatility.upper()}\n\n"
        f"📌 *Sugerencia:* {suggestion}"
    )
    _post(text)

def notify_profit_update(text_block: str):
    """Notifica que llegó un mensaje de TP/Profit (sin gatillar análisis)."""
    text = "🎯 *Profit update detectado del canal:*\n\n" + "```\n" + text_block[:1000] + "\n```"
    # Telegram no permite Markdown dentro de Markdown con triples backticks sin 'MarkdownV2';
    # enviamos sin bloque de código para simplicidad:
    text = "🎯 *Profit update detectado del canal:*\n\n" + text_block[:1000]
    _post(text)
