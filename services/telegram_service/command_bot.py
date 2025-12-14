# services/telegram_service/command_bot.py

import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger("command_bot")


class CommandBot:
    def __init__(self, application, app_layer):
        self.application = application
        self.app_layer = app_layer
        self._register_handlers()
        logger.info("✅ CommandBot handlers registrados.")

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("analizar", self.cmd_analizar))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 Trading AI Monitor activo.\n"
            "Comandos:\n"
            "/analizar SYMBOL DIRECTION\n"
            "Ej: /analizar YALAUSDT short"
        )

    async def cmd_analizar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if len(context.args) < 2:
                await update.message.reply_text("Uso: /analizar SYMBOL DIRECTION")
                return

            symbol = context.args[0].upper().strip()
            direction = context.args[1].lower().strip()

            if direction not in ("long", "short"):
                await update.message.reply_text("Direction debe ser: long | short")
                return

            await self.app_layer.signal.manual_analyze_request(symbol, direction)

        except Exception as e:
            logger.exception(f"❌ Error en /analizar: {e}")
            await update.message.reply_text("❌ Error ejecutando /analizar.")

    # services/telegram_service/command_bot.py

    def register_handlers(app, app_layer):
        """
        Punto único de registro de comandos.
        NO cambia lógica existente.
        """
        # Si ya tienes handlers creados arriba, solo añádelos aquí
        # Ejemplo:
        # app.add_handler(CommandHandler("estado", estado_command))
        # app.add_handler(CommandHandler("revisar", revisar_command))

        pass
