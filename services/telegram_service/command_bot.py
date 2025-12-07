"""
command_bot.py — Bot de comandos Telegram (LITE)
Arquitectura limpia: UI → Application Layer → Motor Técnico
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

# ======================================================
# 📘 Application Layer (interface entre Bot y Motor)
# ======================================================
from services.application_layer import manual_analysis


logger = logging.getLogger("command_bot")


# ======================================================
# 🟦 Comando: /help
# ======================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Trading AI Monitor — Panel de Control (LITE)*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado básico del sistema\n"
        "• /analizar BTCUSDT → Análisis técnico manual\n"
        "• /reactivacion → Revisar señales pendientes\n"
        "• /config → Ver configuración básica del sistema\n\n"
        "_Versión LITE — comandos avanzados en desarrollo._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# 🟦 Comando: /estado
# ======================================================
async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Estado del Sistema (LITE)*\n"
        f"• Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "♻️ Reactivación automática:\n"
        "• Manejada por el motor técnico único en segundo plano.\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# 🟦 Comando: /config
# ======================================================
async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ *Configuración del sistema (LITE)*\n"
        "• Motor técnico unificado activo\n"
        "• Arquitectura por capas en fase de transición\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ======================================================
# 🟦 Comando: /reactivacion (placeholder)
# ======================================================
async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "♻️ Revisando señales pendientes...\n\n⚠️ Versión LITE aún no usa Application Layer completo."
    await update.message.reply_text(msg)


# ======================================================
# 🟦 Comando PRINCIPAL: /analizar
# ======================================================
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = context.args[0].upper()
        direction = None

        if len(context.args) >= 2:
            direction = context.args[1].lower()

        logger.info(f"📨 Comando recibido: /analizar {symbol} {direction}")

        # Llamada al Application Layer
        result = await manual_analysis(symbol, direction or "auto")

        await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.exception("❌ Error en /analizar")
        await update.message.reply_text(f"❌ Error analizando {symbol}: {e}")


# ======================================================
# 🟦 Inicializador del Bot (No threads, 100% async)
# ======================================================
async def start_command_bot():
    logger.info("🤖 Iniciando bot de comandos (LITE)...")

    # Crear aplicación Telegram
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("analizar", analizar))   # <-- FIX
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    # Iniciar polling SIN bloquear el event loop
    await app.initialize()
    await app.start()
    logger.info("🤖 Bot de comandos listo.")
    return app
