"""
command_bot.py — versión LITE estable
-------------------------------------
Panel de control simplificado del Trading AI Monitor.

Incluye (FUNCIONANDO):
✔ /start, /help          → Ayuda
✔ /analizar <par> [dir]  → Análisis técnico manual (motor_wrapper.analyze_and_format)
✔ /reactivacion          → Fuerza ciclo de reactivación con motor técnico único
✔ /estado                → Estado básico del sistema
✔ /config                → Configuración básica

Comandos en construcción (no rompen nada):
• /reanudar, /detener, /reversion, /historial, /limpiar
  → Responden con mensaje “no disponible aún” para evitar errores.
"""

import logging
import asyncio
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, SIMULATION_MODE, TELEGRAM_USER_ID

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from services.technical_engine.motor_wrapper import analyze_and_format
from services.signals_service.signal_reactivation_sync import run_reactivation_cycle
from core.helpers import normalize_symbol, normalize_direction

logger = logging.getLogger("command_bot")

# ============================================================
# 🟢 /start — Ayuda general
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Trading AI Monitor — Panel de Control (LITE)*\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado básico del sistema\n"
        "• /analizar BTCUSDT → Análisis técnico manual\n"
        "• /reactivacion → Revisar señales pendientes (motor técnico único)\n"
        "• /config → Ver configuración básica del sistema\n\n"
        "_Los comandos /reanudar, /detener, /reversion, /historial y /limpiar_ "
        "_están en construcción en esta versión LITE._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🧭 /estado — Estado básico del sistema
# ============================================================

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"

    msg = (
        "📊 *Estado del Sistema (LITE)*\n"
        f"• Modo de Trading: {sim}\n"
        f"• Hora actual: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        "♻️ *Reactivación automática*\n"
        "• Gestión: Motor técnico único activo en segundo plano.\n"
        "• Control detallado por comandos: _pendiente de integración_"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🔍 /analizar <par> [long|short]
# ============================================================

async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso correcto:\n"
            "`/analizar BTCUSDT`\n"
            "`/analizar BTCUSDT long`\n"
            "`/analizar BTCUSDT short`",
            parse_mode="Markdown",
        )
        return

    raw_symbol = context.args[0]
    symbol = normalize_symbol(raw_symbol)

    direction = None
    if len(context.args) > 1:
        d = normalize_direction(context.args[1])
        if d in ("long", "short"):
            direction = d

    try:
        logger.info(f"🧠 /analizar solicitado para {symbol} ({direction or 'auto'})")
        # 🔥 Usa el motor_wrapper que ya formatea el mensaje listo para Telegram
        tech_msg = analyze_and_format(symbol, direction)
        # Por seguridad, si algo raro devuelve un dict u otro tipo, casteamos a str
        if not isinstance(tech_msg, str):
            tech_msg = str(tech_msg)

        await update.message.reply_text(tech_msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Error en /analizar para {symbol}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error analizando {symbol}: {e}")


# ============================================================
# ♻️ /reactivacion — Fuerza ciclo manual
# ============================================================

async def reactivacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("♻️ Revisando señales pendientes con el motor técnico único...")

    try:
        stats = await run_reactivation_cycle()
        total = stats.get("total", 0)
        reactivated = stats.get("reactivated", 0)

        msg = (
            f"♻️ *Revisión completada*\n"
            f"• Señales revisadas: {total}\n"
            f"• Reactivadas: {reactivated}\n"
            f"• Hora: {datetime.now():%Y-%m-%d %H:%M:%S}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ Error en /reactivacion: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error en reactivación: {e}")


# ============================================================
# 🧹 Comandos en construcción (no rompen nada)
# ============================================================

async def not_implemented(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0]
    await update.message.reply_text(
        f"⚠️ El comando {cmd} aún no está disponible en esta versión LITE.\n"
        "El análisis técnico y la reactivación de señales *sí* están activos.",
        parse_mode="Markdown",
    )


# ============================================================
# ⚙️ /config — Config básica
# ============================================================

async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sim = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"
    user_id = TELEGRAM_USER_ID if 'TELEGRAM_USER_ID' in globals() else "N/D"

    msg = (
        "⚙️ *Configuración actual (LITE):*\n"
        f"• Modo: {sim}\n"
        f"• Bot Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"• Usuario permitido: {user_id}\n\n"
        "_Panel de control reducido para máxima estabilidad._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# 🚀 Inicialización del bot
# ============================================================

async def start_command_bot():
    try:
        logger.info("🤖 Iniciando bot de comandos (LITE)...")

        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        # Comandos principales
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("analizar", cmd_analizar))
        app.add_handler(CommandHandler("reactivacion", reactivacion))
        app.add_handler(CommandHandler("config", config_cmd))

        # Comandos aún no integrados, pero sin romper nada
        app.add_handler(CommandHandler("reanudar", not_implemented))
        app.add_handler(CommandHandler("detener", not_implemented))
        app.add_handler(CommandHandler("reversion", not_implemented))
        app.add_handler(CommandHandler("historial", not_implemented))
        app.add_handler(CommandHandler("limpiar", not_implemented))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        logger.info("🤖 Bot de comandos (LITE) listo.")
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot (LITE): {e}", exc_info=True)
