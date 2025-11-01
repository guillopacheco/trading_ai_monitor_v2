
"""
Bot de comandos separado usando python-telegram-bot - VERSIÓN CORREGIDA
"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import CallbackContext
from config import TELEGRAM_BOT_TOKEN
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class CommandBot:
    def __init__(self):
        self.application = None
        self.is_running = False

    async def start(self):
        """Inicia el bot de comandos"""
        try:
            if not TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN no configurado")

            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

            # Registrar comandos
            self.application.add_handler(CommandHandler("start", self.handle_start))
            self.application.add_handler(CommandHandler("estado", self.handle_status))
            self.application.add_handler(CommandHandler("operaciones", self.handle_operations))
            self.application.add_handler(CommandHandler("estadisticas", self.handle_stats))
            self.application.add_handler(CommandHandler("config", self.handle_config))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            self.application.add_handler(CommandHandler("revisar", self.handle_review))
            self.application.add_handler(CommandHandler("seguimiento", self.handle_follow))
            self.application.add_handler(CommandHandler("salud", self.handle_health))
            self.application.add_handler(CommandHandler("operaciones_abiertas", self.handle_open_operations))

            # Iniciar polling
            await self.application.initialize()
            await self.application.start()
            # depending on PTB version updater may be deprecated; keep for compatibility
            try:
                await self.application.updater.start_polling()
            except Exception:
                # Fall back if updater is not available
                try:
                    await self.application.start_polling()
                except Exception:
                    pass

            self.is_running = True
            logger.info("✅ Bot de comandos iniciado correctamente")

            # Test de conexión
            bot_info = await self.application.bot.get_me()
            logger.info(f"🔍 Bot conectado como: {bot_info.username}")

        except Exception as e:
            logger.error(f"❌ Error iniciando bot de comandos: {e}")
            raise

    async def handle_start(self, update: Update, context: CallbackContext):
        """Maneja el comando /start"""
        response = """
🤖 **SISTEMA DE TRADING AUTOMÁTICO**

Bienvenido al sistema de trading automatizado.

📋 **Comandos disponibles:**
/estado - Estado del sistema
/operaciones - Operaciones activas
/estadisticas - Estadísticas de trading
/config - Configuración actual
/revisar - Revisar operaciones abiertas
/seguimiento - Seguimiento de operaciones
/salud - Estado de salud completo
/operaciones_abiertas - Operaciones en Bybit
/help - Ayuda

🔧 Sistema operativo y monitorizando señales.
"""
        await update.message.reply_text(response, parse_mode='Markdown')

    async def handle_status(self, update: Update, context: CallbackContext):
        """Maneja el comando /estado - CORREGIDO SIN IMPORTS CIRCULARES"""
        try:
            from database import trading_db

            status_lines = ["📊 **ESTADO DEL SISTEMA**\n"]

            # Estado Base de Datos
            try:
                db_status = "✅ Operativa" if trading_db.is_connected() else "❌ Desconectada"
                recent_signals = trading_db.get_recent_signals(hours=24)
                signal_count = len(recent_signals)

                status_lines.append(f"• **Base de Datos**: {db_status}")
                status_lines.append(f"• **Señales (24h)**: {signal_count}")

            except Exception:
                status_lines.append(f"• **Base de Datos**: ❌ Error")

            # Estado Telegram User Client
            try:
                from telegram_client import telegram_user_client
                tg_status = "✅ Conectado" if getattr(telegram_user_client, "is_connected", False) else "❌ Desconectado"
                status_lines.append(f"• **Telegram User**: {tg_status}")
            except Exception:
                status_lines.append(f"• **Telegram User**: ❌ Error")

            # Estado Bybit - MEJORADO CON TEST REAL
            try:
                from bybit_api import bybit_client
                from config import BYBIT_API_KEY

                if not BYBIT_API_KEY or BYBIT_API_KEY == "TU_API_KEY_AQUI":
                    bybit_status = "❌ API No Configurada"
                else:
                    # TEST REAL de conexión a Bybit
                    try:
                        test_ticker = await bybit_client.get_ticker("BTCUSDT")
                        if test_ticker:
                            bybit_status = "✅ Conectado"
                        else:
                            bybit_status = "❌ Sin respuesta"
                    except Exception:
                        bybit_status = "❌ Error conexión"

                status_lines.append(f"• **Bybit**: {bybit_status}")

            except Exception:
                status_lines.append(f"• **Bybit**: ❌ Error")

            # Estado del sistema principal - CORREGIDO SIN IMPORT CIRCULAR
            try:
                system_detected = False

                # Método 1: Verificar si el sistema está ejecutándose por procesos
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info.get('cmdline') and 'main.py' in ' '.join(proc.info['cmdline']):
                            system_detected = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Método 2: Verificar variable global sin import
                try:
                    import sys
                    if 'main' in sys.modules:
                        main_module = sys.modules['main']
                        if hasattr(main_module, 'monitor_instance') and main_module.monitor_instance:
                            system_detected = True
                except Exception:
                    pass

                if system_detected:
                    status_lines.append(f"• **Sistema Principal**: ✅ Ejecutándose")
                else:
                    status_lines.append(f"• **Sistema Principal**: ⚠️ No detectado")

            except Exception:
                status_lines.append(f"• **Sistema Principal**: ⚠️ No detectado")

            # Estado del bot de comandos
            try:
                bot_status = "✅ Activo" if self.is_running else "❌ Inactivo"
                status_lines.append(f"• **Bot Comandos**: {bot_status}")
            except Exception:
                status_lines.append(f"• **Bot Comandos**: ⚠️ Desconocido")

            # Estado del Health Monitor
            try:
                from health_monitor import health_monitor
                health_status = health_monitor.check_system_health()
                status_emoji = "🟢" if health_status.get('overall_status') == 'HEALTHY' else "🟡" if health_status.get('overall_status') == 'DEGRADED' else "🔴"
                status_lines.append(f"• **Health Monitor**: {status_emoji} {health_status.get('overall_status')}")
            except Exception:
                status_lines.append(f"• **Health Monitor**: ⚠️ Error")

            # Estado del Operation Tracker
            try:
                from operation_tracker import operation_tracker
                operation_stats = operation_tracker.get_operation_stats()
                status_lines.append(f"• **Operaciones Seguidas**: {operation_stats.get('total_open', 0)}")
            except Exception:
                status_lines.append(f"• **Operation Tracker**: ⚠️ Error")

            # Estado general del sistema - MEJORADO
            error_count = sum(1 for line in status_lines if "❌" in line and "Error" not in line)
            warning_count = sum(1 for line in status_lines if "⚠️" in line)

            if error_count > 0:
                status_lines.append(f"\n🔴 **Sistema con {error_count} error(es)**")
            elif warning_count > 0:
                status_lines.append(f"\n🟡 **Sistema con {warning_count} advertencia(s)**")
            else:
                status_lines.append("\n🟢 **Sistema operativo correctamente**")

            await update.message.reply_text("\n".join(status_lines), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /estado: {e}")
            await update.message.reply_text("❌ Error obteniendo estado del sistema")

    async def handle_health(self, update: Update, context: CallbackContext):
        """Maneja el comando /salud"""
        try:
            from health_monitor import health_monitor

            health_report = health_monitor.get_detailed_report()
            health_status = health_report.get('health_status', {})

            status_emoji = "🟢" if health_status.get('overall_status') == 'HEALTHY' else "🟡" if health_status.get('overall_status') == 'DEGRADED' else "🔴"

            response_lines = [
                f"{status_emoji} **REPORTE DE SALUD DEL SISTEMA**\n",
                f"**Estado General:** {health_status.get('overall_status', 'Desconocido')}",
                f"**Uptime:** {health_report.get('performance_metrics', {}).get('uptime_hours', 0):.1f} horas",
                f"**Señales Procesadas:** {health_report.get('performance_metrics', {}).get('signals_processed', 0)}",
                f"**Tasa de Éxito:** {health_report.get('performance_metrics', {}).get('success_rate', 0):.1f}%",
            ]

            # Estado de conexiones
            conn = health_status.get('connection_status', {})
            if conn:
                response_lines.append("\n**CONEXIONES:**")
                for service, ok in conn.items():
                    ico = "✅" if ok else "❌"
                    response_lines.append(f"• {service.title()}: {ico} {'Conectado' if ok else 'Desconectado'}")

            await update.message.reply_text("\n".join(response_lines), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /salud: {e}")
            await update.message.reply_text("❌ Error obteniendo reporte de salud")

    async def handle_open_operations(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones_abiertas"""
        try:
            from operation_tracker import operation_tracker

            operation_stats = operation_tracker.get_operation_stats()

            if operation_stats.get('total_open', 0) == 0:
                await update.message.reply_text("📭 No hay operaciones abiertas en seguimiento")
                return

            response_lines = [
                f"📊 **OPERACIONES ABIERTAS: {operation_stats.get('total_open', 0)}**",
                f"**ROI Promedio:** {operation_stats.get('average_roi', 0)}%\n"
            ]

            for i, op in enumerate(operation_stats.get('operations', []), 1):
                signal = op.get('signal_data', {})
                roi = op.get('current_roi', 0)
                roi_emoji = "🟢" if roi > 0 else "🔴"
                response_lines.append(f"{i}. {roi_emoji} **{signal.get('pair', 'N/A')}** {signal.get('direction', '')}")
                response_lines.append(f"   ROI: {roi}% | Entry: {op.get('actual_entry', 'N/A')}")
                response_lines.append("")

            await update.message.reply_text("\n".join(response_lines), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /operaciones_abiertas: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones abiertas")

    async def handle_operations(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones - Señales recientes"""
        try:
            from database import trading_db

            recent_signals = trading_db.get_recent_signals(hours=24)

            if not recent_signals:
                await update.message.reply_text("📊 No hay operaciones recientes (últimas 24h)")
                return

            response_lines = ["📋 **OPERACIONES RECIENTES**\n"]

            for i, signal in enumerate(recent_signals[:10], 1):
                pair = signal.get('pair', 'N/A')
                direction = signal.get('direction', 'N/A')
                status = signal.get('status', 'N/A')
                dir_emoji = "🟢" if str(direction).upper() == "BUY" else "🔴"
                status_emoji = "✅" if status == "completed" else "🟡" if status == "pending" else "⚪"
                created_at = signal.get('created_at') or signal.get('timestamp') or ""
                if hasattr(created_at, "strftime"):
                    date_str = created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = str(created_at)[:16]
                response_lines.append(f"{i}. {dir_emoji} **{pair}** {direction.upper()} {status_emoji} {status} • {date_str}")

            response_lines.append(f"\n📈 Total: {len(recent_signals)} operaciones en 24h")

            await update.message.reply_text("\n".join(response_lines), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /operaciones: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones recientes")

    async def handle_stats(self, update: Update, context: CallbackContext):
        """Maneja el comando /estadisticas"""
        try:
            from database import trading_db

            stats = trading_db.get_signal_stats(days=1)

            if not stats:
                await update.message.reply_text("📊 No hay estadísticas disponibles")
                return

            response = [
                "📋 **ESTADÍSTICAS DE TRADING**\n",
                f"• **Señales Totales (24h)**: {stats.get('total_signals', 0)}",
                f"• **Tasa de Confirmación**: {stats.get('confirmation_rate', 0)}%",
            ]

            await update.message.reply_text("\n".join(response), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /estadisticas: {e}")
            await update.message.reply_text("❌ Error obteniendo estadísticas")

    async def handle_config(self, update: Update, context: CallbackContext):
        """Maneja el comando /config"""
        try:
            from config import (
                SIGNALS_CHANNEL_ID, OUTPUT_CHANNEL_ID,
                BYBIT_API_KEY, APP_MODE, LEVERAGE, RISK_PER_TRADE
            )

            config_info = [
                "⚙️ **CONFIGURACIÓN ACTUAL**\n",
                f"• **Modo App**: {APP_MODE}",
                f"• **Canal Señales**: {SIGNALS_CHANNEL_ID}",
                f"• **Canal Output**: {OUTPUT_CHANNEL_ID}",
                f"• **Apalancamiento**: x{LEVERAGE}",
                f"• **Riesgo por Operación**: {RISK_PER_TRADE*100}%",
                f"• **Bybit API**: {'✅ Configurada' if BYBIT_API_KEY else '❌ No configurada'}"
            ]

            await update.message.reply_text("\n".join(config_info), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error en comando /config: {e}")
            await update.message.reply_text("❌ Error obteniendo configuración")

    async def handle_help(self, update: Update, context: CallbackContext):
        """Maneja el comando /help"""
        help_text = """
🤖 **COMANDOS DISPONIBLES**

/start - Iniciar el bot
/estado - Estado general del sistema
/operaciones - Operaciones activas actuales
/estadisticas - Estadísticas de trading
/config - Configuración actual
/revisar - Revisar operaciones abiertas
/seguimiento - Seguimiento de operaciones
/salud - Estado de salud completo
/operaciones_abiertas - Operaciones en Bybit
/help - Muestra esta ayuda
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_review(self, update: Update, context: CallbackContext):
        """Maneja el comando /revisar"""
        try:
            response = """
🔍 **REVISIÓN DE OPERACIONES**

Funcionalidades disponibles:
• Detección automática de operaciones en Bybit
• Monitoreo de ROI en tiempo real
• Alertas de take-profit y stop-loss
• Recomendaciones de gestión de riesgo

Para usar:
1. El sistema detecta automáticamente operaciones abiertas
2. Usa /operaciones_abiertas para ver el estado actual
3. Recibirás alertas automáticas de cambios
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error en review_command: {e}")
            await update.message.reply_text("❌ Error en comando de revisión")

    async def handle_follow(self, update: Update, context: CallbackContext):
        """Maneja el comando /seguimiento"""
        try:
            response = """
📊 **SEGUIMIENTO DE OPERACIONES**

Estadísticas en tiempo real:
• ROI actual por operación
• Precio actual vs entrada
• Recomendaciones de gestión
• Historial de cambios

Alertas automáticas:
✅ Take-profit alcanzado
⚠️ ROI crítico
🔄 Recomendación de reversión
📉 Cambios de tendencia
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error en follow_command: {e}")
            await update.message.reply_text("❌ Error en comando de seguimiento")

    async def stop(self):
        """Detiene el bot de comandos"""
        try:
            if self.application and self.is_running:
                try:
                    await self.application.updater.stop()
                except Exception:
                    pass
                await self.application.stop()
                await self.application.shutdown()
                self.is_running = False
                logger.info("✅ Bot de comandos detenido")
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot de comandos: {e}")

# Instancia global
command_bot = CommandBot()