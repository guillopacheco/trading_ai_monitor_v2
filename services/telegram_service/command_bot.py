import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logger = logging.getLogger("command_bot")


class CommandBot:
    """
    Bot de comandos Telegram para Trading AI Monitor.
    Se conecta a ApplicationLayer sin lógica de negocio interna.
    """

    def __init__(self, app_layer, application: Application):
        self.app_layer = app_layer
        self.application = application

        # Registrar comandos
        self._register_handlers()

    # ----------------------------------------------------------------------
    # Registrar comandos oficiales
    # ----------------------------------------------------------------------
    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("estado", self.cmd_estado))

        self.application.add_handler(CommandHandler("analizar", self.cmd_analizar))
        self.application.add_handler(CommandHandler("reactivar", self.cmd_reactivar))

        self.application.add_handler(CommandHandler("reanudar", self.cmd_reanudar))
        self.application.add_handler(CommandHandler("detener", self.cmd_detener))

        # Captura de texto no reconocido
        self.application.add_handler(MessageHandler(filters.TEXT, self.cmd_unknown))

    # ----------------------------------------------------------------------
    # Comandos
    # ----------------------------------------------------------------------

    async def cmd_start(self, update, context):
        await update.message.reply_text(
            "🤖 *Trading AI Monitor activo*\n"
            "Usa /help para ver los comandos disponibles.",
            parse_mode="Markdown",
        )

    async def cmd_help(self, update, context):
        text = (
            "📘 *Comandos disponibles*\n\n"
            "• /analizar SYMBOL long|short — Análisis inmediato\n"
            "• /reactivar ID — Fuerza reactivación de una señal\n"
            "• /estado — Estado del sistema\n"
            "• /reanudar — Iniciar monitoreo de posiciones\n"
            "• /detener — Detener monitoreo de posiciones\n"
            "• /help — Ayuda\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_estado(self, update, context):
        status = self.app_layer.get_status()

        text = (
            "📊 *Estado del sistema*\n\n"
            f"• Reactivación activa: `{status['reactivation_running']}`\n"
            f"• Monitoreo de posiciones: `{status['position_monitor_running']}`\n"
            f"• Usuario: `{status['telegram_user']}`\n"
        )

        await update.message.reply_text(text, parse_mode="Markdown")

    # ----------------------------------------------------------------------
    # Análisis bajo demanda
    # ----------------------------------------------------------------------
    async def cmd_analizar(self, update, context):
        try:
            parts = update.message.text.split()

            if len(parts) < 3:
                return await update.message.reply_text(
                    "Uso correcto:\n/analizar SYMBOL long|short"
                )

            symbol = parts[1].upper()
            direction = parts[2].lower()
            chat_id = update.message.chat_id

            await self.app_layer.analyze_symbol(symbol, direction, chat_id)

        except Exception as e:
            logger.error(f"Error en /analizar: {e}", exc_info=True)
            await update.message.reply_text("❌ Error procesando análisis.")

    # ----------------------------------------------------------------------
    # Reactivación manual
    # ----------------------------------------------------------------------
    async def cmd_reactivar(self, update, context):
        try:
            parts = update.message.text.split()
            if len(parts) < 2:
                return await update.message.reply_text("Uso: /reactivar ID")

            signal_id = int(parts[1])
            await self.app_layer.evaluate_reactivation(signal_id)

        except Exception as e:
            logger.error(f"Error en /reactivar: {e}", exc_info=True)
            await update.message.reply_text("❌ Error procesando reactivación.")

    # ----------------------------------------------------------------------
    # Monitoreo de posiciones abiertas
    # ----------------------------------------------------------------------
    async def cmd_reanudar(self, update, context):
        try:
            await self.app_layer.start_position_monitor()
            await update.message.reply_text("▶️ *Monitoreo de posiciones reanudado*")
        except Exception as e:
            logger.error(f"Error en /reanudar: {e}", exc_info=True)
            await update.message.reply_text("❌ No se pudo iniciar monitoreo.")

    async def cmd_detener(self, update, context):
        try:
            await self.app_layer.stop_position_monitor()
            await update.message.reply_text("⏹ *Monitoreo detenido*")
        except Exception as e:
            logger.error(f"Error en /detener: {e}", exc_info=True)
            await update.message.reply_text("❌ No se pudo detener monitoreo.")

    # ----------------------------------------------------------------------
    # Captura de texto desconocido
    # ----------------------------------------------------------------------
    async def cmd_unknown(self, update, context):
        await update.message.reply_text(
            "❓ No entiendo ese comando. Usa /help para ver opciones."
        )
