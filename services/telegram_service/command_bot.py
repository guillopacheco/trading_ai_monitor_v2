# services/telegram_service/command_bot.py

import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram import Update

logger = logging.getLogger("command_bot")

# ============================================================
# FUNCIÓN PRINCIPAL - INICIALIZAR BOT
# ============================================================
async def start_command_bot(app_layer):
    """
    Inicializa el bot de Telegram usando ApplicationLayer como backend.
    No se importa ApplicationLayer para evitar importación circular.
    """
    try:
        token = app_layer.bot_token
    except AttributeError:
        logger.error("❌ ApplicationLayer no tiene bot_token configurado.")
        return

    logger.info("🤖 Cargando bot de comandos...")

    application = (
        ApplicationBuilder()
        .token(token)
        .build()
    )

    # Guardar referencia al app layer dentro del bot
    application.bot_data["app"] = app_layer

    # Registrar handlers
    application.add_handler(CommandHandler("analizar", cmd_analyze))
    application.add_handler(CommandHandler("reactivar", cmd_reactivate))
    application.add_handler(CommandHandler("cerrar", cmd_close))
    application.add_handler(CommandHandler("revertir", cmd_reverse))
    application.add_handler(CommandHandler("posiciones", cmd_positions))
    application.add_handler(CommandHandler("estado", cmd_status))

    logger.info("🤖 Bot cargado. Activando polling…")

    # Ejecutar polling en background
    application.run_polling(drop_pending_updates=True)


# ============================================================
# COMANDOS
# ============================================================

async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application.bot_data["app"]

    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "Uso: /analizar BTCUSDT long"
            )
            return

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
        await update.message.reply_text(f"🟪 Cierre forzado enviado para {symbol}")

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
        await update.message.reply_text("📊 Revisando posiciones abiertas...")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 El bot está en ejecución.\n"
        "Servicios activos:\n"
        " • Lector de señales\n"
        " • Bot de comandos\n"
        " • Motor técnico\n"
        " • Monitoreo de posiciones\n"
        " • Reactivación automática"
    )
