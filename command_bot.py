from operation_tracker import monitor_open_positions
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SIMULATION_MODE
from trend_system_final import analyze_and_format

logger = logging.getLogger("command_bot")

# Estado global del monitoreo
active_monitoring = {"running": False, "task": None}

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
        "• /analizar → Ejecutar análisis técnico de un par (ej: `/analizar BTCUSDT`)\n"
        "• /help → Mostrar esta ayuda nuevamente"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ================================================================
# 🧭 /estado
# ================================================================
async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from signal_reactivation_sync import get_reactivation_status

    status = "🟢 Activo" if active_monitoring["running"] else "🔴 Inactivo"
    sim_mode = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"

    # Datos del módulo de reactivación
    re_status = get_reactivation_status()
    re_running = "✅ Activo" if re_status.get("running") else "⚫ Inactivo"
    re_signals = re_status.get("monitored_signals", 0)
    re_last = re_status.get("last_run", "Sin registro")

    msg = (
        f"📊 *Estado actual del sistema:*\n"
        f"🧠 Estado: {status}\n"
        f"⚙️ Modo: {sim_mode}\n"
        f"⏱️ Última actualización: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        f"♻️ *Reactivación automática:*\n"
        f"   • Estado: {re_running}\n"
        f"   • Último ciclo: {re_last}\n"
        f"   • Señales vigiladas: 👁 {re_signals}\n"
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

    async def run_monitor():
        try:
            positions = []  # 🧩 aquí se integrarían las posiciones reales de Bybit
            await asyncio.to_thread(monitor_open_positions, positions)
        except Exception as e:
            logger.error(f"❌ Error en el hilo de monitoreo: {e}")
        finally:
            active_monitoring["running"] = False

    active_monitoring["task"] = asyncio.create_task(run_monitor())
    await update.message.reply_text("🟢 Monitoreo iniciado correctamente.", parse_mode="Markdown")

# ================================================================
# 🛑 /detener
# ================================================================
async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_monitoring["running"]:
        await update.message.reply_text("⚠️ No hay monitoreo activo.", parse_mode="Markdown")
        return

    active_monitoring["running"] = False
    task = active_monitoring.get("task")
    if task and not task.done():
        task.cancel()
        logger.info("🛑 Monitoreo cancelado manualmente.")
    await update.message.reply_text("🛑 Monitoreo detenido manualmente.", parse_mode="Markdown")

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
        pair = sig.get("pair", "N/A")
        direction = sig.get("direction", "?").upper()
        leverage = sig.get("leverage", 0)
        rec = sig.get("recommendation", "Sin datos")
        ratio = float(sig.get("match_ratio", 0)) * 100
        ts = sig.get("timestamp", "Sin fecha")

        msg += (
            f"• {pair} ({direction}, {leverage}x)\n"
            f"  ➤ {rec} ({ratio:.1f}%)\n"
            f"  🕒 {ts}\n\n"
        )

    await update.message.reply_text(msg.strip(), parse_mode="Markdown")

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
        f"Bot Token: {'OK' if TELEGRAM_BOT_TOKEN else '❌'}\n"
        f"User ID: {'OK' if TELEGRAM_USER_ID else '❌'}\n"
        f"Logging: activo"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ================================================================
# ♻️ /reactivacion — Fuerza revisión manual de señales
# ================================================================
async def reactivacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta manualmente el ciclo de reactivación sin esperar 15 minutos."""
    from signal_reactivation_sync import check_reactivation
    from database import get_signals

    await update.message.reply_text("♻️ Iniciando revisión manual de señales en espera...", parse_mode="Markdown")

    try:
        signals = get_signals(limit=20)
        count_total = 0
        count_reactivated = 0

        for sig in signals:
            if sig["recommendation"] in ["ESPERAR MEJOR ENTRADA", "DESCARTAR"]:
                count_total += 1
                result = check_reactivation(
                    sig["pair"],
                    sig["direction"],
                    sig["leverage"],
                    sig.get("entry")
                )
                if result and result.get("status") == "reactivada":
                    count_reactivated += 1

        msg = (
            f"♻️ *Revisión manual completada.*\n\n"
            f"🔎 Señales evaluadas: {count_total}\n"
            f"✅ Reactivadas: {count_reactivated}\n"
            f"🕒 Hora: {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")
        logger.info(f"♻️ Revisión manual ejecutada: {count_total} señales revisadas, {count_reactivated} reactivadas.")

    except Exception as e:
        logger.error(f"❌ Error en /reactivacion: {e}")
        await update.message.reply_text(f"⚠️ Error ejecutando reactivación: {e}", parse_mode="Markdown")

# ================================================================
# 💬 /help
# ================================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ================================================================
# 🧠 /analizar
# ================================================================
async def cmd_analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analiza un par solicitado desde Telegram y responde con resumen técnico."""
    try:
        if not context.args:
            # Se usa update.message.reply_text directamente para evitar problemas de await
            await update.message.reply_text(
                "Uso: `/analizar <PAR>` — Ejemplo: `/analizar ZECUSDT`",
                parse_mode="Markdown"
            )
            return

        symbol = context.args[0].upper().replace("/", "").replace("-", "")
        direction_hint = None

        if len(context.args) > 1:
            dir_candidate = context.args[1].lower()
            if dir_candidate in ["long", "short"]:
                direction_hint = dir_candidate

        # 🔍 Ejecutar análisis
        result, report = analyze_and_format(symbol, direction_hint=direction_hint)

        # ✅ Intentar enviar usando notifier.send_message si es síncrono, de lo contrario usar Telegram directamente
        try:
            send_message(report)  # compatible con tu versión actual (síncrona)
        except TypeError:
            # Si espera parsemode en vez de parse_mode
            send_message(report, parsemode="Markdown")
        except Exception:
            # En caso de que sea async en versiones nuevas
            await update.message.reply_text(report, parse_mode="Markdown")

        logger.info(f"📊 Análisis enviado para {symbol}: {result['recommendation']}")

    except Exception as e:
        logger.error(f"❌ Error en /analizar: {e}")
        await update.message.reply_text(f"⚠️ Error procesando análisis: {e}", parse_mode="Markdown")

# ================================================================
# 🚀 Inicialización del bot
# ================================================================
async def start_command_bot():
    try:
        logger.info("🤖 Iniciando bot de comandos (modo estable sin cierre de loop)...")

        app = (
            ApplicationBuilder()
            .token(TELEGRAM_BOT_TOKEN)
            .connect_timeout(30)
            .build()
        )

        # Registro de comandos
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("reanudar", reanudar))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("historial", historial))
        app.add_handler(CommandHandler("limpiar", limpiar))
        app.add_handler(CommandHandler("config", config))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("analizar", cmd_analizar))
        app.add_handler(CommandHandler("reactivacion", reactivacion))

        await app.initialize()
        await app.start()

        # --- Configurar menú de comandos visibles en Telegram ---
        try:
            await app.bot.set_my_commands([
                ("analizar", "Analiza un par de trading. Ej: /analizar BTCUSDT"),
                ("estado", "Ver estado actual del sistema"),
                ("reactivacion", "Forzar revisión inmediata de señales en espera"),
                ("historial", "Ver últimas señales analizadas"),
                ("config", "Mostrar configuración activa"),
                ("limpiar", "Borrar señales antiguas"),
                ("help", "Mostrar ayuda general")
            ])
            logger.info("✅ Menú de comandos actualizado correctamente en Telegram.")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo actualizar menú de comandos: {e}")

        # --- Activar polling ---
        await app.updater.start_polling()
        logger.info("🤖 Bot de comandos inicializado completamente y esperando órdenes.")
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"❌ Error iniciando command_bot: {e}")