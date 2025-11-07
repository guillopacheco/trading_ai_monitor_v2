import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bot_test")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Test Activo*\n\n"
        "Comandos:\n"
        "• /estado → Ver estado\n"
        "• /help → Mostrar ayuda",
        parse_mode="Markdown",
    )


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Estado del bot: OK*\n🕒 {datetime.utcnow():%Y-%m-%d %H:%M:%S UTC}",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def main():
    logger.info("🤖 Iniciando bot de prueba (modo estable, sin cierre de loop)…")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("help", help_command))

    # Inicialización manual (sin cerrar el loop existente)
    await app.initialize()
    await app.start()
    logger.info("✅ Bot de prueba conectado. Envía /start o /estado en Telegram.")
    await app.updater.start_polling()
    await asyncio.Event().wait()  # Mantiene vivo el proceso sin cerrar el loop


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Bot detenido manualmente.")
