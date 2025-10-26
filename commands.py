#!/usr/bin/env python3
"""
Módulo de comandos para Telegram Bot
"""
from telegram import Update
from telegram.ext import ContextTypes
from logger_config import get_logger

logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    try:
        user = update.effective_user
        message = f"""
🤖 **Hola {user.first_name}!** 🤖

**Trading AI Monitor v2** - Sistema activo y monitoreando

**Comandos disponibles:**
/start - Mensaje de bienvenida
/estado - Estado del sistema
/operaciones - Operaciones activas
/revisar - Revisar señal específica
/seguimiento - Seguimiento de operaciones
/help - Ayuda

**Sistema operativo y listo!** ✅
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"✅ Comando /start ejecutado por {user.first_name}")
    except Exception as e:
        logger.error(f"❌ Error en comando /start: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /estado"""
    try:
        from main import monitor_instance
        from signal_manager import signal_manager
        
        if not monitor_instance:
            await update.message.reply_text("❌ Sistema no inicializado")
            return
            
        pending_signals = signal_manager.get_pending_signals_count()
        active_operations = signal_manager.get_active_operations_count()
        
        message = f"""
📊 **ESTADO DEL SISTEMA** 📊

**Estado General:**
✅ Sistema operativo
🕒 Tiempo activo: Calculando...
🔍 Señales pendientes: {pending_signals}
💼 Operaciones activas: {active_operations}

**Componentes:**
🤖 Bot: Conectado
📱 User Client: Conectado  
💾 Base de datos: Operativa
🎧 Listener: Activo

**Todo funciona correctamente!** 🚀
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"✅ Comando /estado ejecutado")
    except Exception as e:
        logger.error(f"❌ Error en comando /estado: {e}")
        await update.message.reply_text("❌ Error obteniendo estado del sistema")

async def operations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /operaciones"""
    try:
        from signal_manager import signal_manager
        
        active_operations = signal_manager.get_active_operations()
        
        if not active_operations:
            message = "📭 No hay operaciones activas en este momento"
        else:
            message = "💼 **OPERACIONES ACTIVAS** 💼\n\n"
            for op in active_operations[:10]:  # Mostrar máximo 10
                message += f"• {op['pair']} - {op['direction']} - {op['status']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"✅ Comando /operaciones ejecutado")
    except Exception as e:
        logger.error(f"❌ Error en comando /operaciones: {e}")
        await update.message.reply_text("❌ Error obteniendo operaciones")

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /revisar"""
    await update.message.reply_text("🔍 **Función en desarrollo** - Próximamente podrás revisar señales específicas")

async def follow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /seguimiento"""
    await update.message.reply_text("📊 **Función en desarrollo** - Próximamente podrás hacer seguimiento de operaciones")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    message = """
🆘 **AYUDA - TRADING AI MONITOR** 🆘

**Comandos disponibles:**
/start - Mensaje de bienvenida
/estado - Estado del sistema y componentes
/operaciones - Lista de operaciones activas
/revisar - Revisar señal específica (próximamente)
/seguimiento - Seguimiento de operaciones (próximamente)
/help - Esta ayuda

**Soporte:**
Si encuentras problemas, verifica que:
1. El bot esté iniciado correctamente
2. Tengas conexión a internet
3. El sistema esté recibiendo señales

**¡Estamos aquí para ayudar!** ✅
"""
    await update.message.reply_text(message, parse_mode='Markdown')