# notifier.py (versión estable y completa — actualizado con soporte PnL)
import logging
import requests
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

    try:
        r = requests.post(
            API_URL,
            data={
                "chat_id": TELEGRAM_USER_ID,
                "text": text,
                "parse_mode": "Markdown"
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
def send_message(text: str):
    """Mensaje libre a Telegram."""
    return _post(text)


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
# ⚠️ Notificación de operación en riesgo (AHORA CON PnL)
# ================================================================
def notify_operation_alert(symbol, direction, roi, pnl, loss_level, volatility, suggestion):
    """
    Alerta crítica sobre operación abierta.
    Ahora incluye PnL en USDT y ROI, para tomar decisiones reales.
    """
    text = (
        f"⚠️ *ALERTA DE OPERACIÓN*\n\n"
        f"🪙 *Par:* {symbol}\n"
        f"📈 *Dirección:* {direction.upper()}\n"
        f"💰 *ROI actual:* {roi:.2f}%\n"
        f"💵 *P&L:* {pnl:.4f} USDT\n"
        f"📊 *Nivel de pérdida:* {loss_level}%\n"
        f"🌡️ *Volatilidad:* {volatility.upper()}\n\n"
        f"📌 *Sugerencia técnica:* {suggestion}"
    )
    _post(text)


# ================================================================
# 🎯 Notificación de mensajes TP/profit del canal de señales
# ================================================================
def notify_profit_update(text_block: str):
    """
    Notifica cuando el canal de señales envía un mensaje tipo:
    #PIPPIN/USDT (Short📉)
    ✅ Price - 0.0289
    """
    cleaned = text_block[:1000]
    text = f"🎯 *Profit update detectado:*\n\n{cleaned}"
    _post(text)
