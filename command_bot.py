# command_bot.py - VERSIÓN CORREGIDA
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

            # ✅ NUEVO: Agregar manejador de errores global
            self.application.add_error_handler(self.error_handler)

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

    async def error_handler(self, update: Update, context: CallbackContext):
        """Maneja errores globales del bot - NUEVO MÉTODO"""
        try:
            logger.error(f"❌ Error en bot de comandos: {context.error}")
            
            # Enviar mensaje de error genérico al usuario
            if update and update.message:
                await update.message.reply_text(
                    "❌ Ocurrió un error procesando el comando. Por favor, intenta nuevamente.",
                    parse_mode=None  # ✅ Sin formato para evitar errores
                )
        except Exception as e:
            logger.error(f"❌ Error en manejador de errores: {e}")

    async def handle_start(self, update: Update, context: CallbackContext):
        """Maneja el comando /start - CORREGIDO SIN MARKDOWN PROBLEMÁTICO"""
        response = """
🤖 SISTEMA DE TRADING AUTOMÁTICO

Bienvenido al sistema de trading automatizado.

📋 Comandos disponibles:
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
        # ✅ CORRECCIÓN: Enviar sin parse_mode para evitar errores
        await update.message.reply_text(response, parse_mode=None)

    async def handle_status(self, update: Update, context: CallbackContext):
        """Maneja el comando /estado - CORREGIDO SIN IMPORTS CIRCULARES Y SIN MARKDOWN"""
        try:
            status_lines = ["📊 ESTADO DEL SISTEMA\n"]

            # Estado Base de Datos - MEJORADO
            try:
                from database import trading_db
                db_status = "✅ Operativa" if trading_db.is_connected else "❌ Desconectada"
                recent_signals = trading_db.get_recent_signals(hours=24)
                signal_count = len(recent_signals) if recent_signals is not None else 0

                status_lines.append(f"• Base de Datos: {db_status}")
                status_lines.append(f"• Señales (24h): {signal_count}")

            except Exception as e:
                logger.error(f"❌ Error verificando BD: {e}")
                status_lines.append(f"• Base de Datos: ❌ Error")

            # Estado Telegram User Client - MEJORADO
            try:
                from telegram_client import telegram_user_client
                # Verificar conexión real
                if hasattr(telegram_user_client, 'is_connected') and telegram_user_client.is_connected:
                    tg_status = "✅ Conectado"
                else:
                    tg_status = "❌ Desconectado"
                status_lines.append(f"• Telegram User: {tg_status}")
            except Exception as e:
                logger.error(f"❌ Error verificando Telegram: {e}")
                status_lines.append(f"• Telegram User: ❌ Error")

            # Estado Bybit - MEJORADO CON VERIFICACIÓN SEGURA
            try:
                from config import BYBIT_API_KEY

                if not BYBIT_API_KEY or BYBIT_API_KEY == "TU_API_KEY_AQUI":
                    bybit_status = "❌ API No Configurada"
                else:
                    # Verificación segura sin import circular
                    try:
                        from bybit_api import bybit_client
                        if hasattr(bybit_client, 'is_initialized') and bybit_client.is_initialized:
                            bybit_status = "✅ Conectado"
                        else:
                            bybit_status = "❌ No inicializado"
                    except Exception as e:
                        logger.error(f"❌ Error verificando Bybit: {e}")
                        bybit_status = "❌ Error conexión"

                status_lines.append(f"• Bybit: {bybit_status}")

            except Exception as e:
                logger.error(f"❌ Error verificando Bybit config: {e}")
                status_lines.append(f"• Bybit: ❌ Error")

            # Estado del sistema principal - CORREGIDO SIN PSUTIL
            try:
                # Método simple: verificar si los módulos principales están cargados
                import sys
                system_detected = any(module in sys.modules for module in ['main', 'signal_manager', 'health_monitor'])
                
                if system_detected:
                    status_lines.append(f"• Sistema Principal: ✅ Activo")
                else:
                    status_lines.append(f"• Sistema Principal: ⚠️ No detectado")

            except Exception as e:
                logger.error(f"❌ Error verificando sistema principal: {e}")
                status_lines.append(f"• Sistema Principal: ⚠️ Error")

            # Estado del bot de comandos
            try:
                bot_status = "✅ Activo" if self.is_running else "❌ Inactivo"
                status_lines.append(f"• Bot Comandos: {bot_status}")
            except Exception as e:
                logger.error(f"❌ Error verificando bot: {e}")
                status_lines.append(f"• Bot Comandos: ⚠️ Error")

            # Estado del Health Monitor - MEJORADO
            try:
                from health_monitor import health_monitor
                # Verificación simple sin dependencias circulares
                if hasattr(health_monitor, 'error_count'):
                    health_ok = health_monitor.error_count == 0
                    status_emoji = "🟢" if health_ok else "🔴"
                    status_lines.append(f"• Health Monitor: {status_emoji} {'HEALTHY' if health_ok else 'ISSUES'}")
                else:
                    status_lines.append(f"• Health Monitor: ⚠️ No disponible")
            except Exception as e:
                logger.error(f"❌ Error verificando health monitor: {e}")
                status_lines.append(f"• Health Monitor: ⚠️ Error")

            # Estado del Operation Tracker - MEJORADO
            try:
                from operation_tracker import operation_tracker
                if hasattr(operation_tracker, 'get_operation_stats'):
                    operation_stats = operation_tracker.get_operation_stats()
                    open_ops = operation_stats.get('total_open', 0)
                    status_lines.append(f"• Operaciones Seguidas: {open_ops}")
                else:
                    status_lines.append(f"• Operation Tracker: ⚠️ No disponible")
            except Exception as e:
                logger.error(f"❌ Error verificando operation tracker: {e}")
                status_lines.append(f"• Operation Tracker: ⚠️ Error")

            # Estado general del sistema - MEJORADO
            error_count = sum(1 for line in status_lines if "❌ Error" in line)
            warning_count = sum(1 for line in status_lines if "⚠️" in line)

            status_lines.append("")  # Línea en blanco

            if error_count > 0:
                status_lines.append(f"🔴 Sistema con {error_count} error(es)")
            elif warning_count > 0:
                status_lines.append(f"🟡 Sistema con {warning_count} advertencia(s)")
            else:
                status_lines.append("🟢 Sistema operativo correctamente")

            # ✅ CORRECCIÓN: Enviar sin parse_mode para evitar errores de Markdown
            await update.message.reply_text("\n".join(status_lines), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /estado: {e}")
            try:
                await update.message.reply_text(
                    "❌ Error obteniendo estado del sistema",
                    parse_mode=None
                )
            except Exception as inner_e:
                logger.error(f"❌ Error enviando mensaje de error: {inner_e}")

    async def handle_health(self, update: Update, context: CallbackContext):
        """Maneja el comando /salud - CORREGIDO SIN MARKDOWN"""
        try:
            from health_monitor import health_monitor

            health_report = health_monitor.get_detailed_report()
            health_status = health_report.get('health_status', {})

            status_emoji = "🟢" if health_status.get('overall_status') == 'HEALTHY' else "🟡" if health_status.get('overall_status') == 'DEGRADED' else "🔴"

            response_lines = [
                f"{status_emoji} REPORTE DE SALUD DEL SISTEMA\n",
                f"Estado General: {health_status.get('overall_status', 'Desconocido')}",
                f"Uptime: {health_report.get('performance_metrics', {}).get('uptime_hours', 0):.1f} horas",
                f"Señales Procesadas: {health_report.get('performance_metrics', {}).get('signals_processed', 0)}",
                f"Tasa de Éxito: {health_report.get('performance_metrics', {}).get('success_rate', 0):.1f}%",
            ]

            # Estado de conexiones
            conn = health_status.get('connection_status', {})
            if conn:
                response_lines.append("\nCONEXIONES:")
                for service, ok in conn.items():
                    ico = "✅" if ok else "❌"
                    response_lines.append(f"• {service.title()}: {ico} {'Conectado' if ok else 'Desconectado'}")

            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text("\n".join(response_lines), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /salud: {e}")
            await update.message.reply_text("❌ Error obteniendo reporte de salud", parse_mode=None)

    async def handle_open_operations(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones_abiertas - CORREGIDO SIN MARKDOWN"""
        try:
            from operation_tracker import operation_tracker

            operation_stats = operation_tracker.get_operation_stats()

            if operation_stats.get('total_open', 0) == 0:
                await update.message.reply_text("📭 No hay operaciones abiertas en seguimiento", parse_mode=None)
                return

            response_lines = [
                f"📊 OPERACIONES ABIERTAS: {operation_stats.get('total_open', 0)}",
                f"ROI Promedio: {operation_stats.get('average_roi', 0)}%\n"
            ]

            for i, op in enumerate(operation_stats.get('operations', []), 1):
                signal = op.get('signal_data', {})
                roi = op.get('current_roi', 0)
                roi_emoji = "🟢" if roi > 0 else "🔴"
                response_lines.append(f"{i}. {roi_emoji} {signal.get('pair', 'N/A')} {signal.get('direction', '')}")
                response_lines.append(f"   ROI: {roi}% | Entry: {op.get('actual_entry', 'N/A')}")
                response_lines.append("")

            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text("\n".join(response_lines), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /operaciones_abiertas: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones abiertas", parse_mode=None)

    async def handle_operations(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones - CORREGIDO SIN MARKDOWN"""
        try:
            from database import trading_db

            recent_signals = trading_db.get_recent_signals(hours=24)

            if not recent_signals:
                await update.message.reply_text("📊 No hay operaciones recientes (últimas 24h)", parse_mode=None)
                return

            response_lines = ["📋 OPERACIONES RECIENTES\n"]

            for i, signal in enumerate(recent_signals[:10], 1):
                pair = signal.get('pair', 'N/A')
                direction = signal.get('direction', 'N/A')
                status = signal.get('status', 'N/A')
                dir_emoji = "🟢" if str(direction).upper() == "LONG" else "🔴"
                status_emoji = "✅" if status == "confirmed" else "🟡" if status == "pending" else "⚪"
                created_at = signal.get('created_at') or signal.get('timestamp') or ""
                if hasattr(created_at, "strftime"):
                    date_str = created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = str(created_at)[:16]
                response_lines.append(f"{i}. {dir_emoji} {pair} {direction.upper()} {status_emoji} {status} • {date_str}")

            response_lines.append(f"\n📈 Total: {len(recent_signals)} operaciones en 24h")

            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text("\n".join(response_lines), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /operaciones: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones recientes", parse_mode=None)

    async def handle_stats(self, update: Update, context: CallbackContext):
        """Maneja el comando /estadisticas - CORREGIDO SIN MARKDOWN"""
        try:
            from database import trading_db

            stats = trading_db.get_signal_stats(days=1)

            if not stats:
                await update.message.reply_text("📊 No hay estadísticas disponibles", parse_mode=None)
                return

            response = [
                "📋 ESTADÍSTICAS DE TRADING\n",
                f"• Señales Totales (24h): {stats.get('total_signals', 0)}",
                f"• Tasa de Confirmación: {stats.get('confirmation_rate', 0)}%",
            ]

            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text("\n".join(response), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /estadisticas: {e}")
            await update.message.reply_text("❌ Error obteniendo estadísticas", parse_mode=None)

    async def handle_config(self, update: Update, context: CallbackContext):
        """Maneja el comando /config - CORREGIDO SIN MARKDOWN"""
        try:
            from config import (
                SIGNALS_CHANNEL_ID, OUTPUT_CHANNEL_ID,
                BYBIT_API_KEY, APP_MODE, LEVERAGE, RISK_PER_TRADE
            )

            config_info = [
                "⚙️ CONFIGURACIÓN ACTUAL\n",
                f"• Modo App: {APP_MODE}",
                f"• Canal Señales: {SIGNALS_CHANNEL_ID}",
                f"• Canal Output: {OUTPUT_CHANNEL_ID}",
                f"• Apalancamiento: x{LEVERAGE}",
                f"• Riesgo por Operación: {RISK_PER_TRADE*100}%",
                f"• Bybit API: {'✅ Configurada' if BYBIT_API_KEY and BYBIT_API_KEY != 'TU_API_KEY_AQUI' else '❌ No configurada'}"
            ]

            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text("\n".join(config_info), parse_mode=None)

        except Exception as e:
            logger.error(f"❌ Error en comando /config: {e}")
            await update.message.reply_text("❌ Error obteniendo configuración", parse_mode=None)

    async def handle_help(self, update: Update, context: CallbackContext):
        """Maneja el comando /help - CORREGIDO SIN MARKDOWN"""
        help_text = """
🤖 COMANDOS DISPONIBLES

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
        # ✅ CORRECCIÓN: Enviar sin parse_mode
        await update.message.reply_text(help_text, parse_mode=None)

    async def handle_review(self, update: Update, context: CallbackContext):
        """Maneja el comando /revisar - CORREGIDO SIN MARKDOWN"""
        try:
            response = """
🔍 REVISIÓN DE OPERACIONES

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
            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text(response, parse_mode=None)
        except Exception as e:
            logger.error(f"❌ Error en review_command: {e}")
            await update.message.reply_text("❌ Error en comando de revisión", parse_mode=None)

    async def handle_follow(self, update: Update, context: CallbackContext):
        """Maneja el comando /seguimiento - CORREGIDO SIN MARKDOWN"""
        try:
            response = """
📊 SEGUIMIENTO DE OPERACIONES

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
            # ✅ CORRECCIÓN: Enviar sin parse_mode
            await update.message.reply_text(response, parse_mode=None)
        except Exception as e:
            logger.error(f"❌ Error en follow_command: {e}")
            await update.message.reply_text("❌ Error en comando de seguimiento", parse_mode=None)

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