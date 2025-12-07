"""
command_bot.py (LITE)
---------------------
Bot de comandos para Trading AI Monitor v2, integrado con el motor
técnico unificado (technical_engine.analyze).

Comandos activos en esta versión LITE:
- /help
- /estado
- /analizar <SIMBOLO> [long|short]
- /reactivacion
- /config
"""

import logging
import threading
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, TRADING_MODE

# 🚀 Motor técnico unificado
from services.technical_engine.technical_engine import analyze as core_analyze

# ♻️ Reactivación de señales
from services.signals_service.signal_reactivation_sync import run_reactivation_cycle

from services.application_layer import manual_analysis


logger = logging.getLogger("command_bot")


# ============================================================
# 🔎 Helpers de formateo
# ============================================================

def _humanize_bias(code: str | None) -> str:
    if not code:
        return "N/A"
    mapping = {
        "continuation": "Continuación de tendencia",
        "reversal": "Posible reversión",
        "neutral": "Neutral / indeciso",
        "contrarian": "Contrario a la tendencia",
    }
    return mapping.get(code, code)


def _humanize_decision(code: str | None) -> str:
    if not code:
        return "wait"
    mapping = {
        "enter": "entrar al mercado",
        "reactivate": "reactivar señal pendiente",
        "wait": "esperar, sin entrar",
        "cancel": "cancelar / ignorar esta señal",
        "close": "cerrar la operación",
        "protect": "proteger la operación (take profit / stop)",
        "reverse": "revertir la posición",
    }
    return mapping.get(code, code)


def _format_analysis_message(symbol: str, direction: str | None, result: dict) -> str:
    """
    Formatea el resultado de core_analyze() en un mensaje para Telegram.
    Usa SIEMPRE los datos reales del motor unificado (nada de 0% por defecto).
    """
    symbol = symbol.upper()

    # -----------------------------
    # Datos principales del motor
    # -----------------------------
    confidence = float(result.get("confidence") or 0.0)
    grade = result.get("grade", "N/A")
    decision = result.get("decision", "wait")
    decision_reasons = result.get("decision_reasons") or []
    context = result.get("context", "entry")

    # Debug snapshot (donde vienen tendencia mayor y smart_bias)
    debug = result.get("debug") or {}
    snapshot = debug.get("raw_snapshot") or {}

    major_trend = snapshot.get("major_trend_label", "N/A")
    smart_bias_code = snapshot.get("smart_bias_code")
    smart_bias = _humanize_bias(smart_bias_code)

    # -----------------------------
    # Cálculos numéricos
    # -----------------------------
    conf_pct = round(confidence * 100, 1)
    # Para la recomendación usamos la misma confianza global
    decision_conf_pct = conf_pct

    decision_human = _humanize_decision(decision)

    # Motivo principal (si existe)
    motivo = ""
    if decision_reasons:
        motivo = f"\n📝 Motivo principal: {decision_reasons[0]}"

    # Dirección opcional
    dir_str = ""
    if direction:
        dir_str = f" ({direction.lower()})"

    # -----------------------------
    # Mensaje final
    # -----------------------------
    msg = (
        f"📊 Análisis de {symbol}{dir_str}\n"
        f"• Tendencia mayor: {major_trend}\n"
        f"• Smart Bias: {smart_bias}\n"
        f"• Confianza: {conf_pct:.1f}% (Grado {grade})\n\n"
        f"📌 Recomendación: {decision} ({decision_conf_pct:.1f}% confianza)\n"
        f"➡️ Acción sugerida: {decision_human}{motivo}"
    )

    # Contexto (solo informativo)
    msg += f"\n\nℹ️ Contexto analizado: {context}"
    return msg


# ============================================================
# 🧵 Handlers de comandos
# ============================================================

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 Trading AI Monitor — Panel de Control (LITE)\n\n"
        "Comandos disponibles:\n"
        "• /estado → Ver estado básico del sistema\n"
        "• /analizar BTCUSDT → Análisis técnico manual\n"
        "• /reactivacion → Revisar señales pendientes (motor técnico único)\n"
        "• /config → Ver configuración básica del sistema\n"
        "• /help → Mostrar esta ayuda\n\n"
        "Los comandos /reanudar, /detener, /reversion, /historial y /limpiar "
        "están en construcción en esta versión LITE."
    )
    await update.message.reply_text(text)


async def estado_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trading_mode = "💹 REAL" if TRADING_MODE.upper() == "REAL" else "🧪 DEMO"

    text = (
        "📊 Estado del Sistema (LITE)\n"
        f"• Modo de Trading: {trading_mode}\n"
        f"• Hora actual: {now}\n\n"
        "♻️ Reactivación automática\n"
        "• Gestión: Motor técnico único activo en segundo plano.\n"
        "• Control detallado por comandos: pendiente de integración"
    )
    await update.message.reply_text(text)


# =====================================================================
# 🔎 /analizar  — Análisis técnico manual usando Application Layer
# =====================================================================
async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args

        if not args:
            await update.message.reply_text(
                "❗ Uso: /analizar BTCUSDT [long|short]"
            )
            return
        
        symbol = args[0]
        direction = args[1] if len(args) > 1 else None

        await update.message.reply_text(
            f"⏳ Analizando *{symbol}*...", parse_mode="Markdown"
        )

        # -----------------------------
        # 🧠 Llamar al Application Layer
        # -----------------------------
        result = manual_analysis(
            symbol_raw=symbol,
            direction_raw=direction,
            context="manual",
        )

        summary = result["summary"]

        await update.message.reply_text(summary)

    except Exception as e:
        logging.exception("❌ Error en /analizar")
        await update.message.reply_text(
            f"❌ Error analizando {symbol}: {str(e)}"
        )



async def reactivacion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ejecuta una revisión manual de reactivaciones pendientes usando
    el motor técnico unificado.
    """
    await update.message.reply_text("♻️ Revisando señales pendientes...")

    try:
        # Ejecutamos el ciclo de reactivación en un thread del executor
        await context.application.run_in_executor(None, run_reactivation_cycle)
        await update.message.reply_text("✅ Revisión de reactivaciones completada.")
    except Exception as e:
        logger.exception(f"❌ Error en /reactivacion: {e}")
        await update.message.reply_text(f"❌ Error ejecutando reactivación: {e}")


async def config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    trading_mode = "💹 REAL" if TRADING_MODE.upper() == "REAL" else "🧪 DEMO"

    text = (
        "⚙️ Configuración básica del sistema (LITE)\n\n"
        f"• Modo de Trading: {trading_mode}\n"
        "• Motor técnico: ÚNICO, centralizado (technical_engine.analyze)\n"
        "• Reactivación automática: activa en segundo plano\n"
        "• Panel extendido de control: en construcción"
    )
    await update.message.reply_text(text)


# ============================================================
# 🚀 Inicialización del bot
# ============================================================

async def start_command_bot():
    logger = logging.getLogger("command_bot")
    logger.info("🤖 Iniciando bot de comandos (LITE)...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers con nombres reales
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("analizar", analizar_cmd))
    app.add_handler(CommandHandler("estado", estado_cmd))
    app.add_handler(CommandHandler("reactivacion", reactivacion_cmd))
    app.add_handler(CommandHandler("config", config_cmd))

    # Inicializar sin bloquear el loop
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logger.info("🤖 Bot de comandos LISTO. Escuchando…")

    return app


