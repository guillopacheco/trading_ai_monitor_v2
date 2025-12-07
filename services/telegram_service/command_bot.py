"""
command_bot.py — FIX: activar polling real del bot
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN
from services.application_layer import manual_analysis

logger = logging.getLogger("command_bot")


# ======================================================
# Handlers
# ======================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Trading AI Monitor*\n\nComandos:\n"
        "• /estado\n• /analizar BTCUSDT\n• /reactivacion\n• /config",
        parse_mode="Markdown"
    )


async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 Sistema activo\n",
        parse_mode="Markdown"
    )


async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ Motor técnico activo\n",
        parse_mode="Markdown"
    )


async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♻️ Reactivación LITE…", parse_mode="Markdown"
    )


# ======================================================
# /analizar  — FIX EXCEPCIONES
# ======================================================
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = context.args[0].upper()
        direction = context.args[1].lower() if len(context.args) >= 2 else "auto"

        logger.info(f"📨 /analizar recibido: {symbol} {direction}")

        result = await manual_analysis(symbol, direction)
        await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.exception("❌ Error en /analizar")
        await update.message.reply_text(
            f"❌ Error inesperado ejecutando /analizar: {e}",
            parse_mode="Markdown"
        )


# ======================================================
# Inicio REAL del bot
# ======================================================
async def start_command_bot():
    logger.info("🤖 Iniciando bot de comandos…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    logger.info("🤖 Bot cargado. Activando polling…")

    # 🔥🔥🔥 FIX: este método inicia el listener y es BLOQUEANTE
    await app.run_polling()
