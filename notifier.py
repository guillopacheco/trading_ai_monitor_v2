"""
notifier.py (versión estable)
------------------------------
Sistema de notificaciones síncronas para Telegram.
Compatibilidad total con signal_manager.py, operation_tracker.py y main.py.
"""

import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("notifier")

# ================================================================
# 📨 Enviar mensaje general
# ================================================================
def send_message(text: str):
    """
    Envía un mensaje simple a Telegram de forma síncrona.
    En modo SIMULATION_MODE=True, solo lo registra en logs.
    """
    try:
        if SIMULATION_MODE:
            logger.info(f"💬 [SIMULADO] {text}")
            return True

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_USER_ID, "text": text, "parse_mode": "Markdown"}

        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            logger.info("📨 Mensaje enviado correctamente")
            return True
        else:
            logger.error(f"❌ Error enviando mensaje: {r.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Error en send_message(): {e}")
        return False


# ================================================================
# 🚨 Enviar alerta de operación
# ================================================================
def notify_operation_alert(symbol, direction, roi, loss_level, volatility, suggestion):
    """
    Envía alerta de operación con formato visual claro.
    """
    try:
        text = (
            f"⚠️ *ALERTA DE OPERACIÓN*\n\n"
            f"🪙 *Par:* {symbol}\n"
            f"📈 *Dirección:* {direction.upper()}\n"
            f"💰 *ROI actual:* {roi:.2f}%\n"
            f"📊 *Nivel de pérdida:* {loss_level}%\n"
            f"🌡️ *Volatilidad:* {volatility.upper()}\n\n"
            f"📌 *Sugerencia:* {suggestion}"
        )
        send_message(text)
        logger.warning(f"🚨 Alerta de operación enviada: {symbol}")

    except Exception as e:
        logger.error(f"❌ Error enviando alerta de operación: {e}")


# ================================================================
# 📈 Notificación de análisis técnico
# ================================================================
def notify_analysis_result(symbol, direction, leverage, match_ratio, recommendation):
    """
    Envía un resumen del análisis técnico final.
    """
    try:
        text = (
            f"📊 *Análisis de {symbol}*\n"
            f"🔹 *Dirección:* {direction.upper()} (x{leverage})\n"
            f"🔹 *Coincidencia técnica:* {match_ratio:.2f}\n"
            f"📌 *Recomendación:* {recommendation}"
        )
        send_message(text)

    except Exception as e:
        logger.error(f"❌ Error enviando resultado de análisis: {e}")
