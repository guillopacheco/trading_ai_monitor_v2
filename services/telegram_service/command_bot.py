# services/telegram_service/command_bot.py

import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram import Update

logger = logging.getLogger("command_bot")


async def start_command_bot(app_layer):
    """
    Inicializa el bot de comandos SIN importar ApplicationLayer.
    """
    token = getattr(app_layer, "bot_token", None)

    if not token:
        logger.error("❌ ApplicationLayer no tiene bot_token configurado.")
        return

    logger.info("🤖 Inicializando bot de comandos…")

    app = (
        ApplicationBuilder()
        .token(token)
        .build()
    )

    # Guardar referencia al ApplicationLayer
    app.bot_data["app"] = app_layer

    # Registrar comandos
    app.add_handler(CommandHandler("analizar", cmd_analyze))
    app.add_handler(CommandHandler("reactivar", cmd_reactivate))
    app.add_handler(CommandHandler("cerrar", cmd_close))
    app.add_handler(CommandHandler("revertir", cmd_reverse))
    app.add_handler(CommandHandler("posiciones", cmd_positions))
    app.add_handler(CommandHandler("estado", cmd_status))

    logger.info("🤖 Bot listo. Iniciando polling…")

    app.run_polling(drop_pending_updates=True)


# ============================================================
# COMANDOS
# ============================================================

async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        if len(context.args) < 2:
            return await update.message.reply_text("Uso: /analizar BTCUSDT long")

        symbol = context.args[0].upper()
        direction = context.args[1].lower()

        result = await app.analyze(symbol, direction)
        await update.message.reply_text(result)

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_reactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        symbol = context.args[0].upper()
        result = await app.manual_reactivate(symbol)
        await update.message.reply_text(result)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        symbol = context.args[0].upper()
        await app.manual_close(symbol)
        await update.message.reply_text(f"🟪 Cierre enviado para {symbol}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_reverse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        symbol = context.args[0].upper()
        side = context.args[1].lower()

        await app.manual_reverse(symbol, side)
        await update.message.reply_text(f"🔄 Reversión enviada para {symbol}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        await app.monitor_positions()
        await update.message.reply_text("📊 Revisando posiciones...")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 Bot funcionando\n"
        "• Lector de señales\n"
        "• Bot de comandos\n"
        "• Motor técnico\n"
        "• Monitoreo de posiciones\n"
        "• Reactivación automática"
    )
