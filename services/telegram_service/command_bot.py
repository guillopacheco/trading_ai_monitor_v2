# services/telegram_service/command_bot.py
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger("command_bot")


def register_handlers(app, app_layer):
    # handlers básicos que NO rompen nada
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("reanudar", cmd_reanudar))
    app.add_handler(CommandHandler("detener", cmd_detener))
    logger.info("✅ register_handlers(): comandos cargados")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong ✅")


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # estado simple para confirmar que el bot responde
    await update.message.reply_text(
        "✅ Trading AI Monitor activo.\nUsa /ping para probar."
    )


async def cmd_reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # placeholder: evita “no funciona” aunque aún no tengas lógica
    await update.message.reply_text(
        "🟢 OK. (Pendiente: conectar lógica real de reanudación)"
    )


async def cmd_detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛑 OK. (Pendiente: conectar lógica real de detener)"
    )
