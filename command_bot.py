import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import get_signals, clear_old_records
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("command_bot")

# Estado global del monitoreo
active_monitoring = {"running": False}

# ======================== Comandos ===============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor - Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado actual del bot\n"
        "• /reanudar → Reiniciar monitoreo de operaciones\n"
        "• /detener → Detener monitoreo actual\n"
        "• /historial → Ver últimas señales analizadas\n"
        "• /limpiar → Borrar señales antiguas de la base de datos\n"
        "• /config → Mostrar configuración activa\n"
        "• /help → Mostrar esta ayuda nuevamente"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "🟢 Activo" if active_monitoring["running"] else "🔴 Inactivo"
    sim_mode = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"
    msg = (
        f"📊 *Estado actual del sistema:*\n"
        f"🧠 Estado: {status}\n"
        f"⚙️ Modo: {sim_mode}\n"
        f"⏱️ Última actualización: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚙️ El monitoreo ya está en ejecución.", parse_mode="Markdown")
        return
    await update.message.reply_text("🔁 Reiniciando monitoreo de operaciones...", parse_mode="Markdown")
    active_monitoring["running"] = True
    try:
        positions = get_open_positions()
        if not positions:
            await update.message.reply_text("ℹ️ No hay posiciones abiertas actualmente.", parse_mode="Markdown")
            active_monitoring["running"] = False
            return
        monitor_open_positions(positions)
        await update.message.reply_text("🟢 Monitoreo iniciado correctamente.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error en el monitoreo: {e}")
        await update.message.reply_text(f"❌ Error iniciando monitoreo: {e}", parse_mode="Markdown")
        active_monitoring["running"] = False

async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.", parse_mode="Markdown")
        return
    active_monitoring["running"] = False
    await update.message.reply_text("🛑 Monitoreo detenido manualmente.", parse_mode="Markdown")
    logger.info("🛑 Monitoreo detenido por el usuario.")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = get_signals(limit=10)
    if not signals:
        await update.message.reply_text("📭 No hay señales registradas aún.", parse_mode="Markdown")
        return
    msg = "📜 *Últimas señales analizadas:*\n\n"
    for sig in signals:
        msg += (
            f"• {sig['pair']} ({sig['direction'].upper()}, {sig['leverage']}x)\n"
            f"  ➤ {sig['recommendation']} ({sig['match_ratio']*100:.1f}%)\n"
            f"  🕒 {sig['timestamp']}\n\n"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_old_records(days=30)
    await update.message.reply_text("🧹 Registros antiguos eliminados correctamente.", parse_mode="Markdown")
    logger.info("🧹 Limpieza de base de datos completada.")

async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim_mode = "🧪 Simulación" if SIMULATION_MODE else "💹 Real"
    msg = (
        "⚙️ *Configuración activa:*\n"
        f"Modo: {sim_mode}\n"
        f"Bot Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"User ID: {'OK' if TELEGRAM_USER_ID else '❌'}\n"
        f"Logging: activo"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ======================= Lanzador (bloqueante) ===================

def start_command_bot_blocking():
    """
    Ejecuta el bot en un hilo dedicado con su propio event loop.
    Importante: stop_signals=None para evitar set_wakeup_fd en hilos.
    """
    import asyncio
    from telegram.ext import Application

    async def _run():
        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("reanudar", reanudar))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("historial", historial))
        app.add_handler(CommandHandler("limpiar", limpiar))
        app.add_handler(CommandHandler("config", config))
        app.add_handler(CommandHandler("help", help_command))

        # Asegura que no hay webhook y que se descartan updates viejos
        try:
            await app.bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo borrar webhook: {e}")

        logger.info("🤖 Bot de comandos (thread) — iniciando polling...")
        await app.run_polling(stop_signals=None, close_loop=False, allowed_updates=Update.ALL_TYPES)

    asyncio.run(_run())
