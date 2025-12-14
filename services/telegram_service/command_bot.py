from telegram.ext import CommandHandler
import logging

logger = logging.getLogger("command_bot")


def register_handlers(application, app_layer):
    application.add_handler(
        CommandHandler("estado", lambda u, c: estado_command(u, c, app_layer))
    )
    logger.info("✅ register_handlers(): comandos cargados")


async def estado_command(update, context, app_layer):
    try:
        status = app_layer.get_status()

        text = (
            "🤖 *Trading AI Monitor*\n"
            f"📡 Señales pendientes: {status['pending_signals']}\n"
            f"♻️ Reactivación: {'ACTIVA' if status['reactivation_active'] else 'PAUSADA'}\n"
            f"📌 Posiciones abiertas: {status['open_positions']}\n"
            f"🧠 Motor técnico: {status['engine']}\n"
        )

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.exception("❌ Error en /estado")
        await update.message.reply_text("❌ Error obteniendo estado del sistema")
