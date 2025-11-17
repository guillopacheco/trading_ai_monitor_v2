"""
command_bot.py — Bot de control del Trading AI Monitor
-------------------------------------------------------
- Procesa comandos como /analizar, /estado, /historial, etc.
- Conecta con trend_system_final para análisis manual
- Controla monitoreo de posiciones y reactivaciones
- Totalmente alineado con el nuevo ecosistema
"""

import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

from trend_system_final import analyze_and_format
from database import get_signals, clear_old_records
from notifier import send_message
from operation_tracker import monitor_open_positions
from position_reversal_monitor import monitor_reversals
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE

logger = logging.getLogger("command_bot")


# ------------------------------------------------------------
# Estado global del monitoreo
# ------------------------------------------------------------
active_monitoring = {"running": False, "task": None}


# ============================================================
# 🟢 /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor — Panel de Control*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado del sistema\n"
        "• /analizar BTCUSDT → Análisis técnico manual\n"
        "• /reactivacion → Forzar revisión de señales pendientes\n"
        "• /reversion → Analizar reversiones en operaciones abiertas\n"
        "• /historial → Últimos análisis registrados\n"
        "• /reanudar → Activar monitoreo\n"
        "• /detener → Detener monitoreo\n"
        "• /limpiar → Borrar señales antiguas\n"
        "• /config → Mostrar configuración actual\n"
        "• /help → Mostrar esta misma ayuda"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🧭 /estado
# ============================================================
async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from signal_reactivation_sync import get_reactivation_status

    status = "🟢 Activo" if active_monitoring["running"] else "🔴 Inactivo"
    sim = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"

    re_state = get_reactivation_status()
    re_running = "🟢 Activado" if re_state.get("running") else "⚪ Inactivo"
    re_last = re_state.get("last_run", "Nunca")
    re_count = re_state.get("monitored_signals", 0)

    msg = (
        f"📊 *Estado del sistema*\n"
        f"• Bot: {status}\n"
        f"• Modo: {sim}\n"
        f"• Hora: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        f"♻️ *Reactivación automática*\n"
        f"• Estado: {re_running}\n"
        f"• Último ciclo: {re_last}\n"
        f"• Señales vigiladas: {re_count}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🔁 /reanudar
# ============================================================
async def reanudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if active_monitoring["running"]:
        await update.message.reply_text("⚠️ El monitoreo ya está activo.")
        return

    await update.message.reply_text("🔁 Activando monitoreo de operaciones...")
    active_monitoring["running"] = True

    async def _monitor_task():
        try:
            await asyncio.to_thread(monitor_open_positions)
        except Exception as e:
            logger.error(f"❌ Error monitor_open_positions: {e}")
        finally:
            active_monitoring["running"] = False

    active_monitoring["task"] = asyncio.create_task(_monitor_task())
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
        logger.info("🛑 Monitoreo cancelado manualmente.")

    await update.message.reply_text("🛑 Monitoreo detenido.")


# ============================================================
# ♻️ /reactivacion — Fuerza revisión manual
# ============================================================
async def reactivacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from signal_reactivation_sync import check_reactivation
    signals = get_signals(limit=50)

    await update.message.reply_text("♻️ Revisando señales pendientes...")

    revisadas = 0
    reactivadas = 0

    for s in signals:
        rec = s.get("recommendation", "").lower()
        if "esperar" in rec or "descartar" in rec:
            revisadas += 1
            r = check_reactivation(
                s["pair"],
                s["direction"],
                s["leverage"],
                s.get("entry")
            )
            if r and r.get("status") == "reactivada":
                reactivadas += 1

    msg = (
        f"♻️ *Revisión completada*\n"
        f"• Señales revisadas: {revisadas}\n"
        f"• Reactivadas: {reactivadas}\n"
        f"• Hora: {datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


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

    symbol = context.args[0].upper().replace("/", "").replace("-", "")

    direction_hint = None
    if len(context.args) > 1:
        d = context.args[1].lower()
        if d in ["long", "short"]:
            direction_hint = d

    try:
        result, report = analyze_and_format(symbol, direction_hint=direction_hint)
        await asyncio.to_thread(send_message, report)
    except Exception as e:
        logger.error(f"❌ Error en /analizar: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


# ============================================================
# 🔄 /reversion
# ============================================================
async def reversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando señales de reversión...")
    try:
        await monitor_reversals(run_once=True)
        await update.message.reply_text("✅ Revisión completada.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ============================================================
# 📜 /historial
# ============================================================
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = get_signals(limit=10)

    if not signals:
        await update.message.reply_text("📭 No hay señales registradas.")
        return

    msg = "📜 *Últimas señales:*\n\n"

    for s in signals:
        msg += (
            f"• {s['pair']} ({s['direction'].upper()} x{s['leverage']})\n"
            f"  ➤ {s['recommendation']} ({s['match_ratio']*100:.1f}%)\n"
            f"  🕒 {s.get('timestamp','')}\n\n"
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
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim = "🧪 Simulación" if SIMULATION_MODE else "💹 Real"
    msg = (
        "⚙️ *Configuración Actual:*\n"
        f"• Modo: {sim}\n"
        f"• Bot Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"• Usuario autorizado: {TELEGRAM_USER_ID}\n"
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
        app.add_handler(CommandHandler("config", config))
        app.add_handler(CommandHandler("help", start))
        app.add_handler(CommandHandler("analizar", cmd_analizar))
        app.add_handler(CommandHandler("reactivacion", reactivacion))
        app.add_handler(CommandHandler("reversion", reversion))

        # Activar menú de comandos
        try:
            await app.bot.set_my_commands([
                ("analizar", "Analiza un par (ej: /analizar BTCUSDT)"),
                ("estado", "Ver estado del sistema"),
                ("historial", "Últimos análisis"),
                ("reactivacion", "Revisar señales en espera"),
                ("reversion", "Buscar reversiones técnicas"),
                ("reanudar", "Activar monitoreo"),
                ("detener", "Detener monitoreo"),
                ("limit_ar", "Limpiar señales antiguas"),
                ("config", "Mostrar configuración"),
                ("help", "Ayuda general")
            ])
        except:
            pass

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        logger.info("🤖 Bot de comandos listo y funcionando.")
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")
