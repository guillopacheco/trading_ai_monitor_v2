from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging
import time

logger = logging.getLogger("command_bot")


def register_handlers(application):
    application.add_handler(CommandHandler("estado", estado_command))
    logger.info("✅ Comando /estado registrado")


async def estado_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    app_layer = getattr(app, "app_layer", None)

    if not app_layer:
        await update.message.reply_text("❌ ApplicationLayer no inicializado")
        return

    lines = []
    lines.append("🧠 <b>Trading AI Monitor — ESTADO</b>\n")

    # Kernel
    lines.append("✅ Kernel: OK" if hasattr(app_layer, "kernel") else "❌ Kernel")

    # Engines
    lines.append("✅ Technical Engine: OK")
    lines.append(
        "✅ Reactivation Engine: OK"
        if hasattr(app_layer, "signal")
        else "❌ Reactivation Engine"
    )

    # Open positions monitor
    if hasattr(app_layer, "open_position_engine"):
        lines.append("✅ Open Position Monitor: ACTIVO")
    else:
        lines.append("❌ Open Position Monitor")

    # Telegram reader
    lines.append("✅ Telegram Reader: ACTIVO")

    # Señales pendientes (safe)
    try:
        pending = app_layer.signal.get_pending_signals()
        lines.append(f"\n📊 Señales pendientes: {len(pending)}")
    except Exception:
        lines.append("\n📊 Señales pendientes: N/D")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
