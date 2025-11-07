import logging
import threading
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from database import get_signals, clear_old_records
from notifier import send_message
from operation_tracker import monitor_open_positions
from config import TELEGRAM_BOT_TOKEN, SIMULATION_MODE, TELEGRAM_USER_ID

logger = logging.getLogger("command_bot")

# Estado global del monitoreo
active_monitoring = {"running": False, "thread": None}


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
        "• /help → Mostrar esta ayuda nuevamente"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 🧭 /estado
# ================================================================
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


# ================================================================
# 🔄 /reanudar
# ================================================================
async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚙️ El monitoreo ya está activo.", parse_mode="Markdown")
        return

    await update.message.reply_text("🔁 Reiniciando monitoreo de operaciones...", parse_mode="Markdown")
    active_monitoring["running"] = True

    def run_monitor():
        try:
            positions = []  # Normalmente se obtendrían desde Bybit (simulado aquí)
            monitor_open_positions(positions)
        except Exception as e:
            logger.error(f"❌ Error en el hilo de monitoreo: {e}")
        finally:
            active_monitoring["running"] = False

    thread = threading.Thread(target=run_monitor, daemon=True)
    active_monitoring["thread"] = thread
    thread.start()

    await update.message.reply_text("🟢 Monitoreo iniciado correctamente.", parse_mode="Markdown")


# ================================================================
# 🛑 /detener
# ================================================================
async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.", parse_mode="Markdown")
        return

    active_monitoring["running"] = False
    await update.message.reply_text("🛑 Monitoreo detenido manualmente.", parse_mode="Markdown")


# ================================================================
# 📜 /historial
# ================================================================
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        signals = get_signals(limit=10)
        if not signals:
            await update.message.reply_text("📭 No hay señales registradas aún.", parse_mode="Markdown")
            return

        msg = "📜 *Últimas señales analizadas:*\n\n"
        for sig in signals:
            pair = sig.get("pair", "N/A")
            direction = sig.get("direction", "?").upper()
            leverage = sig.get("leverage", 0)
            rec = sig.get("recommendation", "Sin datos")
            ratio = float(sig.get("match_ratio", 0)) * 100
            ts = sig.get("timestamp", "Sin fecha")

            msg += (
                f"• {pair} ({direction}, {leverage}x)\n"
                f"  ➤ *{rec}* ({ratio:.1f}%)\n"
                f"  🕒 {ts}\n\n"
            )

        await update.message.reply_text(msg.strip(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error al mostrar historial: {e}")
        await update.message.reply_text("⚠️ Error al recuperar el historial de señales.")


# ================================================================
# 🧹 /limpiar
# ================================================================
async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clear_old_records(days=30)
        await update.message.reply_text("🧹 Registros antiguos eliminados correctamente.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error limpiando registros: {e}")
        await update.message.reply_text("⚠️ Error al limpiar registros antiguos.", parse_mode="Markdown")


# ================================================================
# ⚙️ /config
# ================================================================
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


# ================================================================
# 💬 /help
# ================================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ================================================================
# 🚀 Inicialización del bot (modo seguro para asyncio)
# ================================================================
async def start_command_bot():
    try:
        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .connect_timeout(30)
            .read_timeout(30)
            .build()
        )

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("reanudar", reanudar))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("historial", historial))
        app.add_handler(CommandHandler("limpiar", limpiar))
        app.add_handler(CommandHandler("config", config))
        app.add_handler(CommandHandler("help", help_command))

        logger.info("🤖 Bot de comandos inicializado correctamente (modo async, aislado del loop principal).")

        # ✅ Ejecutar el bot en un hilo separado para no bloquear Telethon ni main.py
        def run_bot_thread():
            try:
                asyncio.run(app.run_polling(drop_pending_updates=True, stop_signals=None, close_loop=False))
            except Exception as e:
                logger.error(f"❌ Error en el hilo del bot: {e}")

        bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
        bot_thread.start()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")
