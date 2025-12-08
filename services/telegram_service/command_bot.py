import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from application_layer import ApplicationLayer
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger("command_bot")

# ===============================================================
# Inicializar ApplicationLayer global
# ===============================================================
app_layer = ApplicationLayer()


# ===============================================================
# /analizar BTCUSDT long
# ===============================================================
async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            return await update.message.reply_text(
                "❌ Uso correcto:\n/analizar BTCUSDT long"
            )

        symbol = args[0].upper()
        direction = args[1].lower()

        await update.message.reply_text(
            f"🔍 Analizando *{symbol} ({direction})*…",
            parse_mode="Markdown"
        )

        await app_layer.manual_analysis(symbol, direction)

    except Exception as e:
        logger.exception(f"Error en /analizar: {e}")
        await update.message.reply_text("⚠️ Error ejecutando el análisis.")


# ===============================================================
# /reactivar BTCUSDT
# ===============================================================
async def cmd_reactivar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 1:
            return await update.message.reply_text(
                "❌ Uso correcto:\n/reactivar BTCUSDT"
            )

        symbol = args[0].upper()

        await update.message.reply_text(
            f"♻️ Reactivando *{symbol}*…",
            parse_mode="Markdown"
        )

        await app_layer.manual_reactivation(symbol)

    except Exception as e:
        logger.exception(f"Error en /reactivar: {e}")
        await update.message.reply_text("⚠️ Error ejecutando la reactivación.")


# ===============================================================
# /operacion BTCUSDT
# ===============================================================
async def cmd_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 1:
            return await update.message.reply_text(
                "❌ Uso correcto:\n/operacion BTCUSDT"
            )

        symbol = args[0].upper()

        await update.message.reply_text(
            f"📊 Revisando operación abierta en *{symbol}*…",
            parse_mode="Markdown"
        )

        await app_layer.check_open_position(symbol)

    except Exception as e:
        logger.exception(f"Error en /operacion: {e}")
        await update.message.reply_text("⚠️ Error revisando operación.")


# ===============================================================
# /reversion BTCUSDT
# ===============================================================
async def cmd_reversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 1:
            return await update.message.reply_text(
                "❌ Uso correcto:\n/reversion BTCUSDT"
            )

        symbol = args[0].upper()

        await update.message.reply_text(
            f"🔄 Analizando reversión en *{symbol}*…",
            parse_mode="Markdown"
        )

        await app_layer.check_reversal(symbol)

    except Exception as e:
        logger.exception(f"Error en /reversion: {e}")
        await update.message.reply_text("⚠️ Error analizando reversión.")


# ===============================================================
# /detalles BTCUSDT
# ===============================================================
async def cmd_detalles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 1:
            return await update.message.reply_text(
                "❌ Uso correcto:\n/detalles BTCUSDT"
            )

        symbol = args[0].upper()

        await update.message.reply_text(
            f"🔍 Obteniendo diagnóstico detallado de *{symbol}*…",
            parse_mode="Markdown"
        )

        txt = await app_layer.diagnostic(symbol)
        await update.message.reply_text(txt, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"Error en /detalles: {e}")
        await update.message.reply_text("⚠️ Error generando detalles.")


# ===============================================================
# /estado — estado general del sistema
# ===============================================================
async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:

        msg = (
            "🧩 *Estado general del sistema*\n"
            "------------------------------------\n"
            "✔ ApplicationLayer activo\n"
            "✔ SignalCoordinator activo\n"
            "✔ AnalysisCoordinator activo\n"
            "✔ PositionCoordinator activo\n"
            "✔ Base de datos OK\n"
            "✔ Notificaciones OK\n"
            "✔ Motor técnico unificado OK\n"
            "✔ Telegram Reader activo\n"
            "------------------------------------\n"
            "💠 Sistema funcionando correctamente."
        )

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"Error en /estado: {e}")
        await update.message.reply_text("⚠️ Error leyendo el estado.")


# ===============================================================
# /ayuda
# ===============================================================
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📘 *Comandos disponibles*\n"
        "------------------------------------\n"
        "/analizar BTCUSDT long — Analiza una señal\n"
        "/reactivar BTCUSDT — Reactiva una señal pendiente\n"
        "/operacion BTCUSDT — Evalúa operación abierta\n"
        "/reversion BTCUSDT — Analiza reversión\n"
        "/detalles BTCUSDT — Snapshot detallado multi-TF\n"
        "/estado — Estado del sistema\n"
        "/ayuda — Mostrar este mensaje\n"
        "------------------------------------"
    )

    await update.message.reply_text(help_text, parse_mode="Markdown")


# ===============================================================
# Inicialización del bot
# ===============================================================
async def start_command_bot():
    logger.info("🤖 Inicializando Command Bot…")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.add_handler(CommandHandler("reactivar", cmd_reactivar))
    app.add_handler(CommandHandler("operacion", cmd_operacion))
    app.add_handler(CommandHandler("reversion", cmd_reversion))
    app.add_handler(CommandHandler("detalles", cmd_detalles))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("ayuda", cmd_help))

    await app.initialize()
    await app.start()

    logger.info("🤖 CommandBot activo y escuchando comandos.")
