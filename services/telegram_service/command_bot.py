# services/telegram_service/command_bot.py
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger("command_bot")


def register_handlers(application, app_layer):
    """
    ÚNICA función pública que main.py debe importar.
    """
    application.bot_data["app_layer"] = app_layer

    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("estado", cmd_estado))
    application.add_handler(CommandHandler("posiciones", cmd_posiciones))
    application.add_handler(CommandHandler("revisar", cmd_revisar))
    application.add_handler(CommandHandler("detener", cmd_detener))

    logger.info("✅ Handlers registrados correctamente (command_bot).")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🤖 Trading AI Monitor\n\n"
        "Comandos:\n"
        "/estado - estado general\n"
        "/posiciones - resumen posiciones abiertas\n"
        "/revisar - inicia monitoreo posiciones (si aplica)\n"
        "/detener - detiene monitoreo (si aplica)\n"
    )
    await update.message.reply_text(txt)


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app_layer = context.application.bot_data.get("app_layer")
    if not app_layer:
        return await update.message.reply_text("⚠️ app_layer no disponible.")

    await update.message.reply_text("✅ Bot activo. Servicios cargados correctamente.")


async def cmd_posiciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app_layer = context.application.bot_data.get("app_layer")
    if not app_layer:
        return await update.message.reply_text("⚠️ app_layer no disponible.")

    # Llamada segura a OperationService sin asumir un método único
    op = getattr(app_layer, "operation", None)
    if not op:
        return await update.message.reply_text("⚠️ OperationService no disponible.")

    try:
        # intenta métodos comunes
        if hasattr(op, "get_open_positions_summary"):
            summary = await op.get_open_positions_summary()
            return await update.message.reply_text(str(summary))

        if hasattr(op, "list_open_positions"):
            positions = await op.list_open_positions()
            return await update.message.reply_text(str(positions))

        await update.message.reply_text(
            "ℹ️ OperationService no expone método de resumen aún."
        )
    except Exception as e:
        logger.exception("Error en /posiciones")
        await update.message.reply_text(f"❌ Error leyendo posiciones: {e}")


async def cmd_revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mantengo el comando vivo aunque tu lógica final esté en otro módulo
    await update.message.reply_text(
        "✅ /revisar recibido. (Monitor automático corre en background si está habilitado.)"
    )


async def cmd_detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ /detener recibido. (Si tu monitor soporta stop, lo conectamos luego.)"
    )
