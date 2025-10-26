# commands.py - VERSIÓN COMPLETA Y CORREGIDA
import logging
from database import trading_db
from notifier import telegram_notifier

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self):
        self.commands = {
            '/start': self.handle_start,
            '/estado': self.handle_status,
            '/operaciones': self.handle_operations,
            '/estadisticas': self.handle_stats,
            '/help': self.handle_help,
            '/config': self.handle_config
        }
    
    async def handle_command(self, message):
        """Maneja todos los comandos entrantes"""
        try:
            if not message.text:
                return "❌ Comando no reconocido"
            
            command = message.text.split()[0].lower()
            
            if command in self.commands:
                return await self.commands[command](message)
            else:
                return await self.handle_help(message)
                
        except Exception as e:
            logger.error(f"Error procesando comando {message.text}: {e}")
            return "❌ Error procesando comando"
    
    async def handle_start(self, message):
        """Maneja el comando /start"""
        return """
🤖 **SISTEMA DE TRADING AUTOMÁTICO**

Bienvenido al sistema de trading automatizado.

📋 **Comandos disponibles:**
/estado - Estado del sistema
/operaciones - Operaciones activas
/estadisticas - Estadísticas de trading
/config - Configuración actual
/help - Ayuda

🔧 Sistema operativo y monitorizando señales.
"""
    
    async def handle_status(self, message):
        """Maneja el comando /estado"""
        try:
            status_lines = ["📊 **ESTADO DEL SISTEMA**\n"]
            
            # Estado Base de Datos
            try:
                db_status = "✅ Operativa" if trading_db.is_connected() else "❌ Desconectada"
                cursor = trading_db.get_connection().cursor()
                cursor.execute("SELECT COUNT(*) FROM signals")
                signal_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM signals WHERE status='ACTIVE'")
                active_count = cursor.fetchone()[0]
                status_lines.append(f"• **Base de Datos**: {db_status}")
                status_lines.append(f"• **Señales Totales**: {signal_count}")
                status_lines.append(f"• **Operaciones Activas**: {active_count}")
            except Exception as e:
                status_lines.append(f"• **Base de Datos**: ❌ Error ({str(e)[:30]})")
            
            # Estado Telegram
            try:
                from telegram_client import telegram_user_client
                tg_status = "✅ Conectado" if telegram_user_client.is_connected() else "❌ Desconectado"
                status_lines.append(f"• **Telegram**: {tg_status}")
            except Exception as e:
                status_lines.append(f"• **Telegram**: ❌ Error")
            
            # Estado Bybit
            try:
                from bybit_api import bybit_client
                bybit_status = "✅ Conectado" if bybit_client.is_connected() else "❌ Desconectado"
                status_lines.append(f"• **Bybit**: {bybit_status}")
            except Exception as e:
                status_lines.append(f"• **Bybit**: ❌ Error")
            
            return "\n".join(status_lines)
            
        except Exception as e:
            logger.error(f"Error en comando /estado: {e}")
            return "❌ Error obteniendo estado del sistema"
    
    async def handle_operations(self, message):
        """Maneja el comando /operaciones"""
        try:
            cursor = trading_db.get_connection().cursor()
            cursor.execute("""
                SELECT pair, direction, entry_price, status, created_at 
                FROM signals 
                WHERE status='ACTIVE' 
                ORDER BY created_at DESC
            """)
            operations = cursor.fetchall()
            
            if not operations:
                return "📭 No hay operaciones activas actualmente"
            
            result = ["📈 **OPERACIONES ACTIVAS**\n"]
            for op in operations:
                pair, direction, entry_price, status, created_at = op
                result.append(f"• {pair} {direction} @ {entry_price}")
                result.append(f"  🕒 {created_at[:16]}\n")
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"Error en comando /operaciones: {e}")
            return "❌ Error obteniendo operaciones activas"
    
    async def handle_stats(self, message):
        """Maneja el comando /estadisticas"""
        try:
            cursor = trading_db.get_connection().cursor()
            
            # Estadísticas básicas
            cursor.execute("SELECT COUNT(*) FROM signals")
            total_signals = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE status='COMPLETED'")
            completed_signals = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE status='ACTIVE'")
            active_signals = cursor.fetchone()[0]
            
            stats = [
                "📋 **ESTADÍSTICAS DE TRADING**\n",
                f"• Señales Totales: {total_signals}",
                f"• Señales Completadas: {completed_signals}",
                f"• Señales Activas: {active_signals}",
                f"• Tasa de Finalización: {completed_signals/max(total_signals,1)*100:.1f}%"
            ]
            
            return "\n".join(stats)
            
        except Exception as e:
            logger.error(f"Error en comando /estadisticas: {e}")
            return "❌ Error obteniendo estadísticas"
    
    async def handle_config(self, message):
        """Maneja el comando /config"""
        try:
            from config import (
                TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE,
                TELEGRAM_BOT_TOKEN, OUTPUT_CHANNEL_ID, SIGNALS_CHANNEL_ID,
                BYBIT_API_KEY, BYBIT_TESTNET, RISK_PERCENTAGE
            )
            
            config_info = [
                "⚙️ **CONFIGURACIÓN ACTUAL**\n",
                f"• Canal Señales: {SIGNALS_CHANNEL_ID}",
                f"• Canal Output: {OUTPUT_CHANNEL_ID}",
                f"• Bybit Testnet: {BYBIT_TESTNET}",
                f"• Riesgo por Operación: {RISK_PERCENTAGE}%"
            ]
            
            return "\n".join(config_info)
            
        except Exception as e:
            logger.error(f"Error en comando /config: {e}")
            return "❌ Error obteniendo configuración"
    
    async def handle_help(self, message):
        """Maneja el comando /help"""
        help_text = """
🤖 **COMANDOS DISPONIBLES**

/start - Iniciar el bot
/estado - Estado general del sistema
/operaciones - Operaciones activas actuales  
/estadisticas - Estadísticas de trading
/config - Configuración actual
/help - Muestra esta ayuda

📊 **Sistema de Trading Automático**
- Monitoreo de señales en tiempo real
- Ejecución automática en Bybit
- Gestión de riesgo integrada
"""
        return help_text

# Instancia global del manejador de comandos
command_handler = CommandHandler()

# === FUNCIONES DE COMPATIBILIDAD PARA notifier.py ===

async def start_command(update, context):
    """Wrapper para compatibilidad con telegram.ext"""
    try:
        response = await command_handler.handle_start(update.message)
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en start_command: {e}")
        await update.message.reply_text("❌ Error procesando comando")

async def status_command(update, context):
    """Wrapper para compatibilidad con telegram.ext"""
    try:
        response = await command_handler.handle_status(update.message)
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en status_command: {e}")
        await update.message.reply_text("❌ Error procesando comando")

async def operations_command(update, context):
    """Wrapper para compatibilidad con telegram.ext"""
    try:
        response = await command_handler.handle_operations(update.message)
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en operations_command: {e}")
        await update.message.reply_text("❌ Error procesando comando")

async def help_command(update, context):
    """Wrapper para compatibilidad con telegram.ext"""
    try:
        response = await command_handler.handle_help(update.message)
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en help_command: {e}")
        await update.message.reply_text("❌ Error procesando comando")

async def review_command(update, context):
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

async def follow_command(update, context):
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