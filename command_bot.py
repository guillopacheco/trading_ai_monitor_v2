"""
Bot de comandos separado usando python-telegram-bot
"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import CallbackContext
from config import TELEGRAM_BOT_TOKEN
import asyncio

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
/help - Ayuda

🔧 Sistema operativo y monitorizando señales.
"""
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_status(self, update: Update, context: CallbackContext):
        """Maneja el comando /estado"""
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
                
            except Exception as e:
                status_lines.append(f"• **Base de Datos**: ❌ Error ({str(e)[:30]})")
            
            # Estado Telegram User Client
            try:
                from telegram_client import telegram_user_client
                tg_status = "✅ Conectado" if telegram_user_client.is_connected else "❌ Desconectado"
                status_lines.append(f"• **Telegram User**: {tg_status}")
            except Exception as e:
                status_lines.append(f"• **Telegram User**: ❌ Error")
            
            # Estado Bybit
            try:
                from bybit_api import bybit_client
                bybit_status = "✅ Conectado" if bybit_client.is_connected() else "❌ Desconectado"
                status_lines.append(f"• **Bybit**: {bybit_status}")
            except Exception as e:
                status_lines.append(f"• **Bybit**: ❌ Error")
            
            # Estado del sistema
            try:
                from main import monitor_instance
                if monitor_instance and monitor_instance.is_running:
                    status_lines.append(f"• **Sistema Principal**: ✅ Ejecutándose")
                else:
                    status_lines.append(f"• **Sistema Principal**: ❌ Detenido")
            except:
                status_lines.append(f"• **Sistema Principal**: ⚠️ Desconocido")
            
            status_lines.append("\n🟢 **Sistema operativo**")
            
            await update.message.reply_text("\n".join(status_lines), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error en comando /estado: {e}")
            await update.message.reply_text("❌ Error obteniendo estado del sistema")
    
    async def handle_operations(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones"""
        try:
            from database import trading_db
            
            recent_signals = trading_db.get_recent_signals(hours=24)
            
            if not recent_signals:
                await update.message.reply_text(
                    "📭 No hay operaciones en las últimas 24 horas",
                    parse_mode='Markdown'
                )
                return
            
            response = ["📈 **OPERACIONES RECIENTES (24h)**\n"]
            
            for signal in recent_signals[:10]:  # Mostrar máximo 10
                pair = signal.get('pair', 'N/A')
                direction = signal.get('direction', 'N/A')
                entry = signal.get('entry_price', 'N/A')
                status = signal.get('status', 'N/A')
                leverage = signal.get('leverage', 20)
                
                direction_emoji = "📈" if direction == "LONG" else "📉"
                response.append(f"• {direction_emoji} **{pair}** {direction} (x{leverage})")
                response.append(f"  Entry: {entry} | {status}")
                response.append("")
            
            response.append(f"📊 **Total**: {len(recent_signals)} señales")
            
            await update.message.reply_text("\n".join(response), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error en comando /operaciones: {e}")
            await update.message.reply_text("❌ Error obteniendo operaciones")
    
    async def handle_stats(self, update: Update, context: CallbackContext):
        """Maneja el comando /estadisticas"""
        try:
            from database import trading_db
            
            stats = trading_db.get_signal_stats(days=1)
            
            if not stats:
                await update.message.reply_text(
                    "📊 No hay estadísticas disponibles",
                    parse_mode='Markdown'
                )
                return
            
            response = [
                "📋 **ESTADÍSTICAS DE TRADING**\n",
                f"• **Señales Totales (24h)**: {stats.get('total_signals', 0)}",
                f"• **Tasa de Confirmación**: {stats.get('confirmation_rate', 0)}%",
            ]
            
            # Agregar pares más activos
            pair_counts = stats.get('pair_counts', {})
            if pair_counts:
                top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                response.append(f"• **Pares Activos**: {', '.join([f'{pair}({count})' for pair, count in top_pairs])}")
            
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
/help - Muestra esta ayuda

📊 **Sistema de Trading Automático**
- Monitoreo de señales en tiempo real
- Análisis técnico multi-temporalidad
- Gestión de riesgo integrada
- Notificaciones automáticas
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_review(self, update: Update, context: CallbackContext):
        """Maneja el comando /revisar"""
        try:
            response = """
🔍 **REVISIÓN DE OPERACIONES**

📊 **Funcionalidades disponibles:**
• Detección automática de operaciones en Bybit
• Monitoreo de ROI en tiempo real
• Alertas de take-profit y stop-loss
• Recomendaciones de gestión de riesgo

🚀 **Para usar:**
1. El sistema detecta automáticamente operaciones abiertas
2. Usa /seguimiento para ver el estado actual
3. Recibirás alertas automáticas de cambios

📝 *Esta función se integra con operation_tracker.py*
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

📈 **Estadísticas en tiempo real:**
• ROI actual por operación
• Precio actual vs entrada
• Recomendaciones de gestión
• Historial de cambios

🔔 **Alertas automáticas:**
✅ Take-profit alcanzado
⚠️  ROI crítico (-30%)
🔄 Recomendación de reversión
📉 Cambios de tendencia

📋 *Usa /operaciones para ver señales recientes*
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error en follow_command: {e}")
            await update.message.reply_text("❌ Error en comando de seguimiento")
    
    async def stop(self):
        """Detiene el bot de comandos"""
        try:
            if self.application and self.is_running:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.is_running = False
                logger.info("✅ Bot de comandos detenido")
        except Exception as e:
            logger.error(f"❌ Error deteniendo bot de comandos: {e}")

# Instancia global
command_bot = CommandBot()