"""
command_bot.py — MODO EMBEBIDO para python-telegram-bot 20.x
Compatible con asyncio.run(main()) y múltiples tasks.
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN
from services.application_layer import manual_analysis

logger = logging.getLogger("command_bot")

app: Application = None  # instancia global


# ======================================================
# Handlers
# ======================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Trading AI Monitor*\n"
        "Comandos:\n"
        "• /estado\n"
        "• /analizar BTCUSDT\n"
        "• /reactivacion\n"
        "• /config",
        parse_mode="Markdown"
    )


async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Sistema activo", parse_mode="Markdown")


async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ Config cargada", parse_mode="Markdown")


async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("♻️ Reactivación LITE")


async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = context.args[0].upper()
        direction = context.args[1] if len(context.args) >= 2 else "auto"

        logger.info(f"📨 /analizar {symbol} {direction}")

        msg = await manual_analysis(symbol, direction)
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("❌ Error en /analizar")
        await update.message.reply_text(f"❌ Error inesperado: {e}")


# ======================================================
# Iniciar bot *sin cerrar loop*
# ======================================================
async def start_command_bot():
    global app

    logger.info("🤖 Inicializando bot de comandos (MODO EMBEBIDO)…")

    # Crear la aplicación (NO run_polling)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    # 🔥 MODO CORRECTO PARA EVENT LOOP YA EXISTENTE:
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logger.info("🤖 Bot de comandos listo y escuchando mensajes.")
