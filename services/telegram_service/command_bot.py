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


class CommandBot:
    def __init__(self, app_layer, application):
        self.app = app_layer
        self.application = application

        self.application.add_handler(CommandHandler("analizar", self.cmd_analizar))

    async def cmd_analizar(self, update, context):
        symbol = context.args[0].upper()
        direction = context.args[1].lower()

        await self.app.analysis.analyze_request(
            symbol, direction, update.effective_chat.id
        )

    def run(self):
        self.application.run_polling()


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

    self.notifier.configure(self.bot, DEFAULT_CHAT_ID)

    # ---------------------------------------------------------
    # MODO ASÍNCRONO CORRECTO (no usar run_polling())
    # ---------------------------------------------------------

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logger.info("🤖 Bot listo. Iniciando polling…")

    # No bloquear loop: devolver app para apagar después si se desea
    return app
