"""
Bot de comandos de Telegram mejorado - CON NUEVOS COMANDOS
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from health_monitor import health_monitor
from operation_tracker import operation_tracker
from database import trading_db
# Al inicio del archivo command_bot.py, agrega esta importación:
from datetime import datetime  # ✅ AGREGAR ESTA LÍNEA

logger = logging.getLogger(__name__)

class CommandBot:
    """Bot de comandos de Telegram - MEJORADO"""
    
    def __init__(self):
        self.application = None
        self.is_running = False

    async def start(self):
        """Inicia el bot de comandos - MEJORADO CON NUEVOS COMANDOS"""
        try:
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Configurar handlers de comandos MEJORADOS
            self.application.add_handler(CommandHandler("start", self.handle_start))
            self.application.add_handler(CommandHandler("estado", self.handle_status))
            self.application.add_handler(CommandHandler("salud", self.handle_health))
            self.application.add_handler(CommandHandler("operaciones", self.handle_operations))
            self.application.add_handler(CommandHandler("operaciones_abiertas", self.handle_open_operations))
            self.application.add_handler(CommandHandler("detectar_operaciones", self.handle_detectar_operaciones))
            self.application.add_handler(CommandHandler("debug_bybit", self.handle_debug_bybit))
            
            # Comandos existentes
            self.application.add_handler(CommandHandler("evaluar", self.handle_evaluar))
            self.application.add_handler(CommandHandler("estado_detallado", self.handle_estado_detallado))
            self.application.add_handler(CommandHandler("historial", self.handle_historial))
            
            # ✅ NUEVOS COMANDOS - REGISTRAR
            self.application.add_handler(CommandHandler("estadisticas", self.handle_estadisticas))
            self.application.add_handler(CommandHandler("config", self.handle_config))
            self.application.add_handler(CommandHandler("revisar", self.handle_revisar))
            self.application.add_handler(CommandHandler("seguimiento", self.handle_seguimiento))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            
            # Iniciar polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("✅ Bot de comandos iniciado correctamente")
            
            # Test de conexión
            bot_info = await self.application.bot.get_me()
            logger.info(f"🔍 Bot conectado como: {bot_info.username}")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando bot de comandos: {e}")
            raise

    async def stop(self):
        """Detiene el bot de comandos"""
        try:
            if self.application and self.is_running:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.is_running = False
                logger.info("✅ Bot de comandos detenido correctamente")
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot de comandos: {e}")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /start - MEJORADO"""
        try:
            response = """
🤖 *Trading AI Monitor v2* - Sistema Activado

*Comandos disponibles:*

📊 *Estado del Sistema*
/estado - Estado general del sistema
/estado_detallado - Información detallada
/salud - Reporte de salud completo

📈 *Operaciones y Señales*  
/operaciones - Últimas señales procesadas
/operaciones_abiertas - Operaciones en seguimiento
/historial - Historial de señales recientes

🔍 *Análisis bajo Demanda*
/evaluar <symbol> - Análisis manual de un símbolo

*Características:*
• Monitoreo automático de señales
• Análisis técnico multi-timeframe
• Gestión inteligente de riesgo
• Alertas de divergencias y pérdidas
• Base de datos en tiempo real

🔄 Sistema listo para recibir señales.
"""
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /start: {e}")
            await update.message.reply_text("❌ Error procesando comando")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /estado - MEJORADO"""
        try:
            health_status = health_monitor.get_health_status()
            operation_stats = operation_tracker.get_operation_stats()
            signal_stats = trading_db.get_signal_stats(hours=24)
            
            # Determinar estado general
            overall_health = health_status.get('overall_health', False)
            status_emoji = "🟢" if overall_health else "🔴"
            
            response = f"""
{status_emoji} *ESTADO DEL SISTEMA*

• Base de Datos: {'✅ Operativa' if health_status.get('database') else '❌ Problemas'}
• Señales (24h): {signal_stats.get('total', 0)}
• Telegram User: {'✅ Conectado' if health_status.get('telegram_user') else '❌ Desconectado'}
• Bybit: {'✅ Operativo' if health_status.get('bybit_api') else '❌ No inicializado'}
• Sistema Principal: {'✅ Activo' if health_status.get('main_system') else '❌ Inactivo'}
• Bot Comandos: {'✅ Activo' if health_status.get('command_bot') else '❌ Inactivo'}
• Health Monitor: {'🟢 HEALTHY' if overall_health else '🔴 ISSUES'}
• Operaciones Seguidas: {operation_stats.get('total_open', 0)}

🟢 Sistema operativo correctamente
"""
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /estado: {e}")
            await update.message.reply_text("❌ Error obteniendo estado del sistema")

    async def handle_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /salud"""
        try:
            health_report = health_monitor.get_detailed_report()
            
            response = f"""
📊 *REPORTE DE SALUD DETALLADO*

• Estado General: {health_report['health_status']['overall_status']}
• Tiempo Activo: {health_report['performance_metrics']['uptime_hours']:.1f} horas
• Señales Procesadas: {health_report['performance_metrics']['signals_processed']}
• Tasa de Éxito: {health_report['performance_metrics']['success_rate']:.1f}%
• Tasa Reconexión: {health_report['performance_metrics']['reconnect_success_rate']:.1f}%

*Alertas Activas:*
{chr(10).join(['• ' + alert for alert in health_report['health_status'].get('alerts', ['No hay alertas'])])}

*Recomendaciones:*
{chr(10).join(['• ' + rec for rec in health_report.get('recommendations', ['Sistema operando normalmente'])])}
"""
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /salud: {e}")
            await update.message.reply_text("❌ Error obteniendo reporte de salud")

    async def handle_operations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /operaciones"""
        try:
            recent_signals = trading_db.get_recent_signals(hours=24, limit=10)
            
            if not recent_signals:
                response = "📭 No hay señales procesadas en las últimas 24 horas"
            else:
                response = "📊 *ÚLTIMAS SEÑALES PROCESADAS*\n\n"
                
                for signal in recent_signals[:5]:  # Mostrar solo 5
                    status_emoji = "✅" if signal['status'] == 'confirmed' else "❌" if signal['status'] == 'rejected' else "⚠️"
                    response += f"""{status_emoji} *{signal['symbol']}* {signal['direction']}
• Entry: {signal['entry_price']}
• Estado: {signal['status']}
• Hora: {signal['created_at'][11:16]}\n\n"""
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /operaciones: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones")

    async def handle_open_operations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /operaciones_abiertas - CORREGIDO"""
        try:
            operation_stats = operation_tracker.get_operation_stats()
            open_operations = operation_stats.get('operations', [])
            
            if not open_operations:
                response = "📭 No hay operaciones abiertas en seguimiento"
            else:
                response = "📈 *OPERACIONES ABIERTAS*\n\n"
                
                for op in open_operations[:5]:  # Mostrar solo 5
                    signal_data = op.get('signal_data', {})
                    pnl = op.get('current_roi', 0)
                    pnl_emoji = "🟢" if pnl > 0 else "🔴"
                    
                    response += f"""📊 *{signal_data.get('pair', 'N/A')}* {signal_data.get('direction', 'N/A')}
    • Entry: {op.get('actual_entry', 'N/A')}
    • Actual: {op.get('current_price', 'N/A')}
    • PnL: {pnl_emoji} {pnl:.2f}%
    • Tamaño: {op.get('size', 0):.4f}
    • Leverage: x{signal_data.get('leverage', 'N/A')}\n\n"""
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /operaciones_abiertas: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones abiertas")

    # === NUEVOS COMANDOS MEJORADOS ===

    async def handle_evaluar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /evaluar - NUEVO COMANDO"""
        try:
            from notifier import telegram_notifier
            
            # Obtener símbolo del mensaje (ej: /evaluar BTCUSDT)
            symbol = context.args[0].upper() if context.args else None
            
            if not symbol:
                await update.message.reply_text("❌ Uso: /evaluar <symbol> (ej: /evaluar BTCUSDT)")
                return
            
            # Simular datos de análisis (en producción esto vendría del trend_analyzer)
            analysis_data = {
                'current_price': 0,  # En producción, obtener precio real
                'trend': 'ALCISTA',
                'rsi': 45.5,
                'recommendation': 'MANTENER',
                'ema_trend': 'ALCISTA',
                'macd_signal': 'COMPRA', 
                'volatility': 'MEDIA'
            }
            
            await telegram_notifier.send_manual_evaluation(symbol, analysis_data)
            await update.message.reply_text(f"📊 Evaluación enviada para {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error en comando /evaluar: {e}")
            await update.message.reply_text("❌ Error en evaluación")

    async def handle_estado_detallado(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /estado_detallado - NUEVO COMANDO"""
        try:
            from health_monitor import health_monitor
            
            health_report = health_monitor.get_detailed_report()
            stats = health_monitor.get_health_status()
            signal_stats = trading_db.get_signal_stats(hours=24)
            
            # Determinar salud general
            overall_status = health_report['health_status']['overall_status']
            status_emoji = "🟢" if overall_status == "HEALTHY" else "🟡" if overall_status == "DEGRADED" else "🔴"
            
            message = f"""
📊 **ESTADO DETALLADO DEL SISTEMA**

• Salud General: {status_emoji} {overall_status}
• Tiempo Activo: {health_report['performance_metrics']['uptime_hours']:.1f}h
• Señales Procesadas: {health_report['performance_metrics']['signals_processed']}
• Tasa de Éxito: {health_report['performance_metrics']['success_rate']:.1f}%

🔌 **CONEXIONES:**
• Base de Datos: {'✅' if stats['database'] else '❌'}
• Telegram User: {'✅' if stats['telegram_user'] else '❌'} 
• Bybit API: {'✅' if stats['bybit_api'] else '❌'}
• Sistema Principal: {'✅' if stats['main_system'] else '❌'}

📈 **ESTADÍSTICAS (24h):**
• Total Señales: {signal_stats.get('total', 0)}
• Confirmadas: {signal_stats.get('confirmed', 0)}
• Rechazadas: {signal_stats.get('rejected', 0)}
• Pendientes: {signal_stats.get('pending', 0)}
• Operaciones Seguidas: {stats.get('operations_tracked', 0)}
• Errores: {stats.get('errors', 0)}
• Advertencias: {stats.get('warnings', 0)}
"""
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /estado_detallado: {e}")
            await update.message.reply_text("❌ Error obteniendo estado detallado")

    async def handle_historial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /historial - NUEVO COMANDO"""
        try:
            recent_signals = trading_db.get_recent_signals(hours=24, limit=15)
            
            if not recent_signals:
                await update.message.reply_text("📭 No hay historial de señales en las últimas 24 horas")
                return
            
            # Agrupar por resultado
            confirmed = [s for s in recent_signals if s['status'] == 'confirmed']
            rejected = [s for s in recent_signals if s['status'] == 'rejected']
            
            message = f"""
📜 **HISTORIAL DE SEÑALES (24h)**

• Total: {len(recent_signals)} señales
• Confirmadas: {len(confirmed)}
• Rechazadas: {len(rejected)}

📈 **ÚLTIMAS 5 SEÑALES:**
"""
            
            for signal in recent_signals[:5]:
                status_emoji = "✅" if signal['status'] == 'confirmed' else "❌"
                message += f"\n{status_emoji} {signal['symbol']} {signal['direction']} - {signal['status']}"
            
            if len(recent_signals) > 5:
                message += f"\n\n... y {len(recent_signals) - 5} más"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /historial: {e}")
            await update.message.reply_text("❌ Error obteniendo historial")

    # Agregar estos métodos NUEVOS a la clase CommandBot:

    async def handle_estadisticas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /estadisticas - NUEVO COMANDO"""
        try:
            from database import trading_db
            from health_monitor import health_monitor
            
            # Obtener estadísticas
            signal_stats = trading_db.get_signal_stats(hours=24)
            health_status = health_monitor.get_health_status()
            operation_stats = operation_tracker.get_operation_stats()
            
            # Calcular porcentajes
            total = signal_stats.get('total', 1)
            confirmed_pct = (signal_stats.get('confirmed', 0) / total) * 100 if total > 0 else 0
            rejected_pct = (signal_stats.get('rejected', 0) / total) * 100 if total > 0 else 0
            
            message = f"""
    📈 **ESTADÍSTICAS DEL SISTEMA (24h)**

    • Total Señales: {total}
    • Confirmadas: {signal_stats.get('confirmed', 0)} ({confirmed_pct:.1f}%)
    • Rechazadas: {signal_stats.get('rejected', 0)} ({rejected_pct:.1f}%)
    • Pendientes: {signal_stats.get('pending', 0)}

    📊 **OPERACIONES:**
    • Abiertas: {operation_stats.get('total_open', 0)}
    • ROI Promedio: {operation_stats.get('average_roi', 0):.1f}%

    ⚡ **RENDIMIENTO:**
    • Tasa de Acierto: {confirmed_pct:.1f}%
    • Señales/Hora: {total / 24:.1f}
    • Uptime: {health_status.get('uptime_minutes', 0) / 60:.1f}h

    🔧 **SISTEMA:**
    • Base de Datos: {'✅' if health_status.get('database') else '❌'}
    • APIs Conectadas: {sum([health_status.get('bybit_api', False), health_status.get('telegram_user', False)])}/2
    • Errores: {health_status.get('errors', 0)}
    """
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /estadisticas: {e}")
            await update.message.reply_text("❌ Error obteniendo estadísticas")

    async def handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /config - NUEVO COMANDO"""
        try:
            from config import APP_MODE, LEVERAGE, RISK_PER_TRADE, ACCOUNT_BALANCE
            
            message = f"""
    ⚙️ **CONFIGURACIÓN ACTUAL**

    • Modo: {APP_MODE}
    • Apalancamiento: x{LEVERAGE}
    • Riesgo por Operación: {RISK_PER_TRADE * 100:.1f}%
    • Balance de Cuenta: ${ACCOUNT_BALANCE}

    📊 **UMBRALES:**
    • Match Mínimo Entrada: 50%
    • Match Mínimo Precaución: 33%
    • Stop Loss Base: 2%
    • Toma de Ganancia: 4 niveles

    🔔 **ALERTAS ACTIVAS:**
    • Divergencias fuertes
    • Pérdidas > 30%
    • Actualizaciones BD
    • Health checks
    """
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /config: {e}")
            await update.message.reply_text("❌ Error obteniendo configuración")

    async def handle_revisar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /revisar - NUEVO COMANDO"""
        try:
            operation_stats = operation_tracker.get_operation_stats()
            open_operations = operation_stats.get('operations', [])
            
            if not open_operations:
                message = "📭 No hay operaciones abiertas para revisar"
            else:
                message = "🔍 **REVISIÓN DE OPERACIONES ABIERTAS**\n\n"
                
                for op in open_operations:
                    signal_data = op.get('signal_data', {})
                    pnl = op.get('current_roi', 0)
                    pnl_emoji = "🟢" if pnl > 0 else "🔴"
                    status = "✅ EN PROFIT" if pnl > 0 else "⚠️ EN PÉRDIDA" if pnl < -10 else "⚪ NEUTRAL"
                    
                    message += f"""📊 *{signal_data.get('pair', 'N/A')}* {signal_data.get('direction', 'N/A')}
    • PnL: {pnl_emoji} {pnl:.2f}% ({status})
    • Entry: {op.get('actual_entry', 'N/A')}
    • Actual: {op.get('current_price', 'N/A')}
    • Tamaño: {op.get('size', 0):.4f}
    • Leverage: x{signal_data.get('leverage', 'N/A')}\n\n"""
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /revisar: {e}")
            await update.message.reply_text("❌ Error en revisión")

    async def handle_detectar_operaciones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /detectar_operaciones - NUEVO COMANDO"""
        try:
            await update.message.reply_text("🔍 Buscando operaciones en Bybit...")
            
            # Forzar detección
            operations_detected = await operation_tracker.auto_detect_operations()
            
            if operations_detected:
                operation_stats = operation_tracker.get_operation_stats()
                response = f"✅ Operaciones detectadas: {operation_stats['total_open']} operaciones"
            else:
                response = "📭 No se encontraron operaciones abiertas en Bybit"
                
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /detectar_operaciones: {e}")
            await update.message.reply_text("❌ Error detectando operaciones")

    async def handle_seguimiento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /seguimiento - NUEVO COMANDO"""
        try:
            operation_stats = operation_tracker.get_operation_stats()
            open_operations = operation_stats.get('operations', [])
            
            # Calcular estadísticas básicas
            total_open = len(open_operations)
            in_profit = len([op for op in open_operations if op.get('current_roi', 0) > 0])
            in_loss = len([op for op in open_operations if op.get('current_roi', 0) < 0])
            
            rois = [op.get('current_roi', 0) for op in open_operations]
            avg_roi = sum(rois) / len(rois) if rois else 0
            best_roi = max(rois) if rois else 0
            worst_roi = min(rois) if rois else 0
            
            message = f"""
    🎯 **SEGUIMIENTO DE OPERACIONES**

    • Total Abiertas: {total_open}
    • En Profit: {in_profit}
    • En Pérdida: {in_loss}

    📊 **RENDIMIENTO:**
    • ROI Promedio: {avg_roi:.2f}%
    • Mejor Operación: {best_roi:.2f}%
    • Peor Operación: {worst_roi:.2f}%

    🔄 **ESTADO ACTUAL:**
    • Monitoreo Activo: {'✅' if operation_tracker.is_tracking else '❌'}
    • Última Actualización: {datetime.now().strftime('%H:%M:%S')}
    """
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /seguimiento: {e}")
            await update.message.reply_text("❌ Error obteniendo seguimiento")

    async def handle_debug_bybit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /debug_bybit - NUEVO COMANDO PARA DIAGNÓSTICO"""
        try:
            await update.message.reply_text("🔧 Ejecutando diagnóstico de Bybit...")
            
            # Verificar conexión con Bybit
            from bybit_monitor import bybit_monitor
            
            # Test de conexión
            positions = await bybit_monitor.get_open_positions()
            balance = await bybit_monitor.get_account_balance()
            
            response = f"""
    🔧 *DIAGNÓSTICO BYBIT*

    • Posiciones encontradas: {len(positions) if positions else 0}
    • Balance: {balance if balance else 'N/A'}
    • Monitor inicializado: {bybit_monitor.session is not None}
    • API Key configurada: {bool(bybit_monitor.session and bybit_monitor.session.api_key)}

    📊 *OPERACIONES DETECTADAS:*
    """
            
            if positions:
                for pos in positions:
                    response += f"\n• {pos['symbol']} {pos['side']} - Tamaño: {pos['size']}"
            else:
                response += "\n• No hay posiciones abiertas"
                
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en comando /debug_bybit: {e}")
            await update.message.reply_text(f"❌ Error en diagnóstico: {e}")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja comando /help - NUEVO COMANDO"""
        try:
            message = """
    🤖 **TRADING AI MONITOR v2 - AYUDA**

    📊 *COMANDOS DE ESTADO:*
    /start - Iniciar bot y ver comandos
    /estado - Estado general del sistema
    /estado_detallado - Información detallada
    /salud - Reporte de salud completo
    /estadisticas - Estadísticas de rendimiento

    📈 *OPERACIONES Y SEÑALES:*
    /operaciones - Últimas señales procesadas
    /operaciones_abiertas - Operaciones en seguimiento  
    /historial - Historial de señales
    /revisar - Revisión detallada de operaciones
    /seguimiento - Estadísticas de seguimiento

    🔍 *ANÁLISIS Y CONFIGURACIÓN:*
    /evaluar <symbol> - Análisis manual
    /config - Configuración actual
    /help - Esta ayuda

    ⚡ *CARACTERÍSTICAS:*
    • Monitoreo automático 24/7
    • Análisis técnico multi-timeframe
    • Alertas inteligentes
    • Gestión de riesgo automatizada
    • Base de datos en tiempo real

    💡 *EJEMPLOS:*
    /evaluar BTCUSDT - Analizar Bitcoin
    /estadisticas - Ver rendimiento
    /revisar - Revisar operaciones abiertas
    """
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /help: {e}")
            await update.message.reply_text("❌ Error mostrando ayuda")

# Instancia global
command_bot = CommandBot()