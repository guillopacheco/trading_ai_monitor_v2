import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

# ================================================================
# 🧱 Configuración básica del logger
# ================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bot_test")


# ================================================================
# 🔹 Comandos de prueba
# ================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Test Activo*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado del bot\n"
        "• /help → Mostrar esta ayuda",
        parse_mode="Markdown"
    )


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📊 *Estado del Bot:*\n"
        f"🧠 OK — Conectado correctamente.\n"
        f"🕒 Hora del servidor: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ================================================================
# 🚀 Inicializador del bot
# ================================================================
async def main():
    logger.info("🤖 Iniciando bot de prueba...")
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("✅ Bot de prueba conectado. Envia /start o /estado en Telegram.")
    await app.run_polling(drop_pending_updates=True)


# ================================================================
# 🏁 Ejecución
# ================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Prueba detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error crítico en bot_test: {e}")
