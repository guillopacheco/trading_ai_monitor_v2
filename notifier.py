import logging
import requests
import asyncio
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("notifier")

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


# ================================================================
# 🔧 Envío base
# ================================================================
def _post(text: str):
    """Envío seguro de mensajes a Telegram."""
    if SIMULATION_MODE:
        logger.info(f"💬 [SIMULADO] {text}")
        return True

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no configurados.")
        return False

    try:
        r = requests.post(
            API_URL,
            data={
                "chat_id": TELEGRAM_USER_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        if r.status_code == 200:
            logger.info("📨 Mensaje enviado correctamente")
            return True

        logger.error(f"❌ Error enviando mensaje Telegram: {r.text}")
        return False

    except Exception as e:
        logger.error(f"❌ Error en _post Telegram: {e}")
        return False


# ================================================================
# 📤 Mensajes públicos
# ================================================================
async def send_message(text: str):
    """Envía un mensaje al chat principal usando asyncio.
    Se integra con el loop async sin bloquearlo."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _post, text)


# ================================================================
# 📈 Notificación de análisis técnico
# ================================================================
def notify_analysis_result(symbol, direction, leverage, match_ratio, recommendation):
    text = (
        f"📊 *Análisis de {symbol}*\n"
        f"🔹 *Dirección:* {direction.upper()} (x{leverage})\n"
        f"🔹 *Coincidencia técnica:* {match_ratio:.2f}%\n"
        f"📌 *Recomendación:* {recommendation}"
    )
    _post(text)


# ================================================================
# 🚨 Notificación de alerta de operación (operation_tracker)
# ================================================================
def notify_operation_alert(symbol, direction, roi, pnl, loss_level, volatility, suggestion):
    msg = (
        f"🚨 *Alerta en operación abierta*\n"
        f"📊 Par: {symbol}\n"
        f"🎯 Dirección: {direction.upper()}\n"
        f"💰 ROI: {roi:.2f}%\n"
        f"📉 PnL: {pnl:.4f} USDT\n"
        f"🔥 Nivel de pérdida alcanzado: {loss_level}%\n"
        f"🌡️ Volatilidad: {volatility}\n"
        f"🧠 Recomendación: {suggestion}"
    )
    _post(msg)


# ================================================================
# 🎯 Notificación de mensajes TP/profit del canal de señales
# ================================================================
def notify_profit_update(text_block: str):
    cleaned = text_block[:1000]
    text = f"🎯 *Profit update detectado:*\n\n{cleaned}"
    _post(text)
