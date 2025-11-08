import logging
from datetime import datetime
import asyncio
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("notifier")

# ================================================================
# 🤖 Inicialización del bot
# ================================================================
try:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    logger.info("✅ Conexión con Telegram establecida")
except Exception as e:
    bot = None
    logger.error(f"❌ Error conectando con Telegram: {e}")


# ================================================================
# ✉️ Envío seguro de mensajes
# ================================================================
def send_message(text: str):
    """
    Envío seguro de mensajes Telegram.
    Compatible con entornos sincrónicos (test, main, signal_manager).
    """
    try:
        if SIMULATION_MODE:
            logger.info(f"💬 [SIMULADO] {text}")
            return True

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
            logger.warning("⚠️ Token o USER_ID no configurados.")
            return False

        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        # Si hay un loop activo (como con Telethon), usa create_task
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(bot.send_message(chat_id=TELEGRAM_USER_ID, text=text, parse_mode="Markdown"))
        except RuntimeError:
            # Si no hay loop activo (modo normal)
            asyncio.run(bot.send_message(chat_id=TELEGRAM_USER_ID, text=text, parse_mode="Markdown"))

        logger.info("📨 Mensaje enviado correctamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error enviando mensaje Telegram: {e}")
        return False

# ================================================================
# 📊 Resultados de señales
# ================================================================
def notify_signal_result(symbol: str, message: str):
    """
    Notifica el resultado del análisis técnico inicial.
    """
    try:
        header = f"🧠 *ANÁLISIS COMPLETADO* — {symbol}\n\n"
        send_message(header + message)
        logger.info(f"✅ Notificación de análisis enviada para {symbol}")
    except Exception as e:
        logger.error(f"❌ Error notificando resultado de {symbol}: {e}")

# ================================================================
# ♻️ Reactivaciones técnicas
# ================================================================
def notify_reactivation(symbol: str, message: str):
    """
    Notifica una reactivación técnica antes del precio de entrada.
    """
    try:
        header = f"♻️ *REACTIVACIÓN TÉCNICA DETECTADA* — {symbol}\n\n"
        send_message(header + message)
        logger.info(f"✅ Reactivación notificada para {symbol}")
    except Exception as e:
        logger.error(f"❌ Error notificando reactivación de {symbol}: {e}")


# ================================================================
# ⚠️ Alertas de operaciones abiertas
# ================================================================
def notify_operation_alert(symbol: str, message: str):
    """
    Envía una alerta de pérdida progresiva o recomendación técnica
    mientras la operación está abierta.
    """
    try:
        header = f"⚠️ *ALERTA DE OPERACIÓN* — {symbol}\n\n"
        send_message(header + message)
        logger.warning(f"🚨 Alerta de operación enviada: {symbol}")
    except Exception as e:
        logger.error(f"❌ Error notificando alerta de {symbol}: {e}")


# ================================================================
# 🧾 Historial o informes
# ================================================================
def notify_summary_report(summary: str):
    """
    Envía un resumen general o informe diario/semanal.
    """
    try:
        header = f"📋 *REPORTE DE ESTADO* — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        send_message(header + summary)
        logger.info("✅ Reporte de estado enviado")
    except Exception as e:
        logger.error(f"❌ Error enviando reporte: {e}")
