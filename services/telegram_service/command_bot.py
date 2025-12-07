"""
command_bot.py — FIX 2025-12-07
Corrige el error silencioso de /analizar y garantiza logs detallados.
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

# Application Layer
from services.application_layer import manual_analysis


logger = logging.getLogger("command_bot")


# ======================================================
# /help
# ======================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Trading AI Monitor — Panel de Control (LITE)*\n\n"
        "Comandos:\n"
        "• /estado\n"
        "• /analizar BTCUSDT\n"
        "• /reactivacion\n"
        "• /config\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# /estado
# ======================================================
async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Estado del Sistema (LITE)*\n"
        f"• Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# /config
# ======================================================
async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ *Configuración del sistema*\n"
        "• Motor técnico unificado: activo\n"
        "• Arquitectura por capas: transición Fase 1.2\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# /reactivacion
# ======================================================
async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♻️ Reactivación LITE\n\nPróxima actualización integrará Application Layer.",
        parse_mode="Markdown"
    )


# ======================================================
# /analizar  — FIX COMPLETO
# ======================================================
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = context.args[0].upper()
        direction = context.args[1].lower() if len(context.args) >= 2 else "auto"

        logger.info(f"📨 /analizar recibido → symbol={symbol}, direction={direction}")

        # 🔥 llamado seguro al Application Layer
        result = await manual_analysis(symbol, direction)

        # 🔥 respuesta garantizada
        await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"❌ EXCEPCIÓN en /analizar para {locals().get('symbol','UNKNOWN')}: {e}")

        await update.message.reply_text(
            f"❌ Error inesperado en /analizar: {e}",
            parse_mode="Markdown"
        )


# ======================================================
# Inicialización
# ======================================================
async def start_command_bot():
    logger.info("🤖 Iniciando bot de comandos (LITE)…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    await app.initialize()
    await app.start()

    logger.info("🤖 Bot de comandos listo.")
    return app
