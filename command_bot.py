"""
command_bot.py
------------------------------------------------------------
Bot de comandos de Telegram (modo asincrónico)
para controlar el sistema Trading AI Monitor.
------------------------------------------------------------
"""

import logging
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from config import TELEGRAM_BOT_TOKEN, SIMULATION_MODE
from operation_tracker import monitor_open_positions
from database import get_signals, clear_old_records

logger = logging.getLogger("command_bot")

# ================================================================
# 🌐 Estado global del monitoreo
# ================================================================
active_monitoring = {"running": False, "thread": None}


# ================================================================
# 🟢 /start — bienvenida
# ================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor - Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado actual del sistema\n"
        "• /reanudar → Reiniciar monitoreo de operaciones\n"
        "• /detener → Detener monitoreo actual\n"
        "• /historial → Ver últimas señales analizadas\n"
        "• /limpiar → Borrar señales antiguas\n"
        "• /config → Mostrar configuración activa\n"
        "• /help → Mostrar esta ayuda nuevamente"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 📊 /estado — estado actual del sistema
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
# 🔁 /reanudar — iniciar monitoreo en hilo separado
# ================================================================
async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚙️ El monitoreo ya está en ejecución.", parse_mode="Markdown")
        return

    await update.message.reply_text("🔁 Reiniciando monitoreo de operaciones...", parse_mode="Markdown")
    active_monitoring["running"] = True

    def run_monitor():
        try:
            positions = []  # Aquí se obtendrían desde Bybit o BD
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
# 🛑 /detener — detener monitoreo
# ================================================================
async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.", parse_mode="Markdown")
        return

    active_monitoring["running"] = False
    await update.message.reply_text("🛑 Monitoreo detenido manualmente.", parse_mode="Markdown")


# ================================================================
# 📜 /historial — mostrar señales registradas
# ================================================================
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra las últimas señales analizadas, formateadas con match_ratio y recomendación.
    """
    try:
        signals = get_signals(limit=10)
        if not signals:
            await update.message.reply_text("📭 No hay señales registradas aún.", parse_mode="Markdown")
            return

        msg_lines = ["📜 *Últimas señales analizadas:*\n"]
        for sig in signals:
            symbol = sig.get("symbol", "N/A")
            direction = sig.get("direction", "?").upper()
            leverage = sig.get("leverage", 0)
            match_ratio = sig.get("match_ratio", 0)
            recommendation = sig.get("recommendation") or "Sin análisis"
            timestamp = sig.get("timestamp", "—").split(" ")[0]

            ratio_str = f"{match_ratio*100:.1f}%" if isinstance(match_ratio, (float, int)) else "—"

            icon = "✅" if recommendation.startswith("ENTRADA") else (
                "⚠️" if recommendation == "ESPERAR" else "❌"
            )

            msg_lines.append(
                f"{icon} *{symbol}* ({direction}, {leverage}x)\n"
                f"  ├ 🎯 *Confianza:* {ratio_str}\n"
                f"  ├ 🧭 *Recomendación:* {recommendation}\n"
                f"  └ 🕒 {timestamp}\n"
            )

        msg_text = "\n".join(msg_lines)
        await update.message.reply_text(msg_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Error mostrando historial: {e}")
        await update.message.reply_text("⚠️ Error al recuperar el historial de señales.", parse_mode="Markdown")


# ================================================================
# 🧹 /limpiar — eliminar registros antiguos
# ================================================================
async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clear_old_records(days=30)
        await update.message.reply_text("🧹 Registros antiguos eliminados correctamente.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error limpiando base de datos: {e}")
        await update.message.reply_text("⚠️ No se pudo limpiar la base de datos.", parse_mode="Markdown")


# ================================================================
# ⚙️ /config — configuración actual
# ================================================================
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim_mode = "🧪 Simulación" if SIMULATION_MODE else "💹 Real"
    msg = (
        "⚙️ *Configuración activa:*\n"
        f"Modo: {sim_mode}\n"
        f"Token: {'✅ OK' if TELEGRAM_BOT_TOKEN else '❌ Falta TOKEN'}\n"
        f"Logging: Activo"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ================================================================
# 💬 /help — mostrar ayuda
# ================================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ================================================================
# 🚀 Inicialización principal del bot de comandos
# ================================================================
async def start_command_bot():
    """
    Lanza el bot de comandos en modo asincrónico.
    """
    try:
        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .concurrent_updates(True)
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

        logger.info("🤖 Bot de comandos inicializado correctamente (modo async).")
        await app.initialize()
        await app.start()
        logger.info("💬 Bot de comandos escuchando mensajes en tiempo real...")
        await app.updater.start_polling()
        await app.updater.idle()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")
