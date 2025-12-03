"""
command_bot.py — versión final integrada con trend_system_final
-----------------------------------------------------------------------
Centro de control del Trading AI Monitor vía comandos de Telegram.

Incluye:
✔ /analizar → Análisis técnico oficial (trend_system_final)
✔ /reactivacion → Fuerza reactivación de señales en espera
✔ /reversion → Analiza reversiones en posiciones abiertas
✔ /historial → Últimas señales guardadas
✔ /reanudar /detener → Control del monitoreo de operaciones
✔ /estado → Estado general del sistema
✔ /config → Config actual del bot
-----------------------------------------------------------------------
"""

import logging
import asyncio
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, SIMULATION_MODE


from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from services.technical_engine.motor_wrapper import (
    analyze,
    analyze_and_format,
)

from services.signals_service.signal_reactivation_sync import start_reactivation_monitor, run_reactivation_cycle
from services.positions_service.operation_tracker import start_operation_tracker
from services.positions_service.position_reversal_monitor import start_reversal_monitor

from services.telegram_service.notifier import send_message
from core.helpers import normalize_symbol, normalize_direction


logger = logging.getLogger("command_bot")


# ============================================================
# 🔄 Estado global del monitoreo de operaciones
# ============================================================

active_monitoring = {"running": False, "task": None}


# ============================================================
# 🟢 /start — Ayuda general
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor — Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado del sistema\n"
        "• /analizar BTCUSDT → Análisis técnico manual\n"
        "• /reactivacion → Revisar señales pendientes\n"
        "• /reversion → Detectar reversiones de operaciones\n"
        "• /historial → Últimas señales registradas\n"
        "• /reanudar → Activar monitoreo de operaciones\n"
        "• /detener → Detener monitoreo\n"
        "• /limpiar → Limpia señales antiguas\n"
        "• /config → Ver configuración del sistema\n"
        "• /help → Mostrar esta ayuda"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🧭 /estado
# ============================================================

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "🟢 Activo" if active_monitoring["running"] else "🔴 Inactivo"
    sim = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"

    # Estado de reactivación
    re = get_reactivation_status()
    re_state = "🟢 Activado" if re.get("running") else "⚪ Inactivo"

    msg = (
        "📊 *Estado del Sistema*\n"
        f"• Bot (operaciones): {status}\n"
        f"• Modo de Trading: {sim}\n"
        f"• Hora actual: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        "♻️ *Reactivación automática*\n"
        f"• Estado: {re_state}\n"
        f"• Último ciclo: {re.get('last_run', 'Nunca')}\n"
        f"• Señales revisadas: {re.get('monitored_signals', 0)}\n"
        f"• Total reactivadas: {re.get('reactivated_count', 0)}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🔁 /reanudar — Inicio de monitoreo de operaciones
# ============================================================

async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚠️ El monitoreo ya está activo.")
        return

    await update.message.reply_text("🔁 Activando monitoreo de operaciones...")
    active_monitoring["running"] = True

    async def _task():
        try:
            while active_monitoring["running"]:
                await monitor_open_positions()
                await asyncio.sleep(20)   # cada 20–30 segundos
        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions: {e}")
        finally:
            active_monitoring["running"] = False

    active_monitoring["task"] = asyncio.create_task(_task())
    await update.message.reply_text("🟢 Monitoreo iniciado.")


# ============================================================
# 🛑 /detener
# ============================================================

async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.")
        return

    active_monitoring["running"] = False
    task = active_monitoring.get("task")

    if task and not task.done():
        task.cancel()

    await update.message.reply_text("🛑 Monitoreo detenido.")


# ============================================================
# ♻️ /reactivacion — Fuerza ciclo manual
# ============================================================

async def reactivacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("♻️ Revisando señales pendientes...")

    try:
        stats = await run_reactivation_cycle()
        msg = (
            f"♻️ *Revisión completada*\n"
            f"• Señales revisadas: {stats.get('checked', 0)}\n"
            f"• Reactivadas: {stats.get('reactivated', 0)}\n"
            f"• Hora: {datetime.now():%Y-%m-%d %H:%M:%S}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Error en /reactivacion: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

# ============================================================
# 🔍 /analizar <par> [long|short]
# ============================================================

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Uso correcto:\n`/analizar BTCUSDT`\n`/analizar BTCUSDT long`",
            parse_mode="Markdown"
        )
        return

    symbol = normalize_symbol(context.args[0])
    direction = None

    if len(context.args) > 1:
        d = normalize_direction(context.args[1])
        if d in ["long", "short"]:
            direction = d

    try:
        # motor único vía trend_system_final
        tech_msg = analyze_and_format(symbol, direction)

        await update.message.reply_text(tech_msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Error en /analizar: {e}")
        await update.message.reply_text(f"❌ Error analizando {symbol}: {e}")


# ============================================================
# 🔄 /reversion — Revisar reversión técnica
# ============================================================

async def reversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Revisando posibles reversiones...")
    try:
        await monitor_reversals(run_once=True)
        await update.message.reply_text("✅ Revisión completada.")
    except Exception as e:
        logger.error(f"❌ Error en /reversion: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


# ============================================================
# 📜 /historial
# ============================================================

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = get_signals(limit=15)

    if not signals:
        await update.message.reply_text("📭 No hay señales registradas.")
        return

    msg = "📜 *Últimas señales registradas:*\n\n"

    for s in signals:
        msg += (
            f"• {s['symbol']} ({s['direction'].upper()} x{s['leverage']})\n"
            f"  ➤ {s['recommendation']} ({s['match_ratio']:.1f}%)\n"
            f"  🕒 {s['created_at']}\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🧹 /limpiar
# ============================================================

async def limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_old_records(days=30)
    await update.message.reply_text("🧹 Registros antiguos eliminados.")


# ============================================================
# ⚙️ /config
# ============================================================

async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"
    msg = (
        "⚙️ *Configuración actual:*\n"
        f"• Modo: {sim}\n"
        f"• Bot Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"• Usuario permitido: {TELEGRAM_USER_ID}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🚀 Inicialización del bot
# ============================================================

async def start_command_bot():
    try:
        logger.info("🤖 Iniciando bot de comandos...")

        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        # Registrar comandos
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("reanudar", reanudar))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("historial", historial))
        app.add_handler(CommandHandler("limpiar", limpiar))
        app.add_handler(CommandHandler("config", config_cmd))
        app.add_handler(CommandHandler("help", start))
        app.add_handler(CommandHandler("analizar", cmd_analizar))
        app.add_handler(CommandHandler("reactivacion", reactivacion))
        app.add_handler(CommandHandler("reversion", reversion))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        logger.info("🤖 Bot de comandos listo.")
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")
