"""
Bot de comandos de control del sistema Trading AI Monitor.
Compatible con python-telegram-bot v20+ y asyncio.
"""

import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from notifier import send_message
from database import get_signals, clear_old_records
from operation_tracker import monitor_open_positions
from bybit_client import get_open_positions
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("command_bot")

# ================================================================
# 🧭 Estado global del monitoreo
# ================================================================
active_monitoring = {"running": False}


# ================================================================
# 🟢 /start
# ================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor — Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado actual del bot\n"
        "• /reanudar → Reiniciar monitoreo de operaciones\n"
        "• /detener → Detener monitoreo actual\n"
        "• /historial → Ver últimas señales analizadas\n"
        "• /limpiar → Borrar señales antiguas de la base de datos\n"
        "• /config → Mostrar configuración activa\n"
        "• /help → Mostrar esta ayuda"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 🧠 /estado
# ================================================================
async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "🟢 Activo" if active_monitoring["running"] else "🔴 Inactivo"
    sim_mode = "🧪 Simulación" if SIMULATION_MODE else "💹 Real"
    msg = (
        f"📊 *Estado actual del sistema:*\n"
        f"🧠 Estado: {status}\n"
        f"⚙️ Modo: {sim_mode}\n"
        f"⏱️ Última actualización: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 🔁 /reanudar
# ================================================================
async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚙️ El monitoreo ya está en ejecución.", parse_mode="Markdown")
        return

    await update.message.reply_text("🔁 Reiniciando monitoreo de operaciones...", parse_mode="Markdown")
    active_monitoring["running"] = True

    async def monitor_task():
        try:
            positions = get_open_positions()
            if positions:
                logger.info(f"📈 {len(positions)} posiciones activas detectadas.")
                await asyncio.to_thread(monitor_open_positions, positions)
            else:
                await update.message.reply_text("📭 No hay posiciones abiertas actualmente.", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"❌ Error en monitoreo: {e}")
        finally:
            active_monitoring["running"] = False

    asyncio.create_task(monitor_task())
    await update.message.reply_text("🟢 Monitoreo iniciado correctamente.", parse_mode="Markdown")


# ================================================================
# 🛑 /detener
# ================================================================
async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.", parse_mode="Markdown")
        return
    active_monitoring["running"] = False
    await update.message.reply_text("🛑 Monitoreo detenido manual­mente.", parse_mode="Markdown")


# ================================================================
# 📜 /historial
# ================================================================
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


# ================================================================
# 🧹 /limpiar
# ================================================================
async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_old_records(days=30)
    await update.message.reply_text("🧹 Registros antiguos eliminados correctamente.", parse_mode="Markdown")


# ================================================================
# ⚙️ /config
# ================================================================
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim_mode = "🧪 Simulación" if SIMULATION_MODE else "💹 Real"
    msg = (
        "⚙️ *Configuración activa:*\n"
        f"Modo: {sim_mode}\n"
        f"Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"User ID: {'OK' if TELEGRAM_USER_ID else '❌'}\n"
        f"Logging: Activo"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 💬 /help
# ================================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ================================================================
# 🚀 INICIALIZACIÓN ASÍNCRONA DEL BOT
# ================================================================
async def start_command_bot():
    """
    Inicializa el bot de comandos dentro del event loop principal,
    evitando conflictos con asyncio.run() y Telethon.
    """
    try:
        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .connect_timeout(15)
            .build()
        )

        # Registrar comandos
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("reanudar", reanudar))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("historial", historial))
        app.add_handler(CommandHandler("limpiar", limpiar))
        app.add_handler(CommandHandler("config", config))
        app.add_handler(CommandHandler("help", help_command))

        # Asegurar que no haya webhook activo
        await app.bot.delete_webhook(drop_pending_updates=True)

        logger.info("🤖 Bot de comandos inicializado correctamente (modo async).")
        await app.initialize()
        await app.start()

        # Confirmar por mensaje directo
        await send_message("✅ Bot de comandos iniciado correctamente. Comandos disponibles con /start")

        # Procesar actualizaciones sin cerrar el loop
        while True:
            update = await app.update_queue.get()
            try:
                await app.process_update(update)
            except Exception as e:
                logger.error(f"❌ Error procesando update: {e}")

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")
