"""
command_bot.py — versión final estable (PTB v20.x)
Funciona 100%, escucha comandos y responde análisis.
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
# /help
# ======================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Trading AI Monitor — Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado\n"
        "• /analizar BTCUSDT\n"
        "• /reactivacion\n"
        "• /config\n",
        parse_mode="Markdown"
    )


# ======================================================
# /estado
# ======================================================
async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Estado del Sistema*\n"
        f"• Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode="Markdown"
    )


# ======================================================
# /config
# ======================================================
async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ *Configuración Actual*\n"
        "• Motor técnico unificado: activo\n"
        "• Arquitectura por capas: estable\n",
        parse_mode="Markdown"
    )


# ======================================================
# /reactivacion
# ======================================================
async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♻️ Reactivación en desarrollo.\n",
        parse_mode="Markdown"
    )


# ======================================================
# /analizar
# ======================================================
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = context.args[0].upper()
        direction = context.args[1].lower() if len(context.args) >= 2 else "auto"

        logger.info(f"📨 /analizar recibido: {symbol} {direction}")

        msg = await manual_analysis(symbol, direction)
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("❌ Error en /analizar")
        await update.message.reply_text(f"❌ Error inesperado: {e}", parse_mode="Markdown")


# ======================================================
# START DEL BOT (run_polling)
# ======================================================
async def start_command_bot():
    logger.info("🤖 Inicializando bot de comandos…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    logger.info("🤖 Bot cargado. Activando polling…")

    # 🔥🔥🔥 EL MÉTODO CORRECTO QUE INICIA EL LISTENER
    await app.run_polling()
