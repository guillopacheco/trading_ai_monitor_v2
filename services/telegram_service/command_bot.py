# services/telegram_service/command_bot.py

import logging
from telegram.ext import Application, CommandHandler
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger("command_bot")


# -------------------------------------------------------------
# Comandos
# -------------------------------------------------------------


async def cmd_start(update, context):
    await update.message.reply_text("🤖 Bot activo. Usa /analizar SYMBOL long|short")


async def cmd_analizar(update, context, app_layer):
    try:
        parts = update.message.text.split()
        if len(parts) != 3:
            return await update.message.reply_text("Formato: /analizar BTCUSDT long")

        symbol = parts[1].upper()
        direction = parts[2].lower()

        await app_layer.analysis.analyze_request(
            symbol, direction, update.message.chat_id
        )

    except Exception as e:
        logger.error(f"Error en /analizar: {e}", exc_info=True)
        await update.message.reply_text("❌ Error procesando análisis.")


# -------------------------------------------------------------
# Inicialización del bot
# -------------------------------------------------------------


async def start_command_bot(app_layer):
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ ApplicationLayer no tiene bot_token configurado.")
        return

    logger.info("🤖 Inicializando bot de comandos…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(
        CommandHandler("analizar", lambda u, c: cmd_analizar(u, c, app_layer))
    )

    # ---------------------------------------------------------
    # MODO ASÍNCRONO CORRECTO (no usar run_polling())
    # ---------------------------------------------------------

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logger.info("🤖 Bot listo. Iniciando polling…")

    # No bloquear loop: devolver app para apagar después si se desea
    return app
