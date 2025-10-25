#!/usr/bin/env python3
"""
Trading AI Monitor v2 - Sistema Principal - ACTUALIZADO CON COMANDOS
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from config import validate_config, SIGNALS_CHANNEL_ID
from logger_config import setup_logging, get_logger
from telegram_client import telegram_user_client
from signal_manager import signal_manager
from notifier import telegram_notifier
from database import trading_db
from helpers import parse_signal_message
from typing import Dict
from datetime import timedelta

# ✅ NUEVOS IMPORTS PARA COMANDOS
from telegram.ext import Application

logger = get_logger(__name__)

class TradingAIMonitor:
    """Clase principal del sistema de trading - ACTUALIZADO CON COMANDOS"""
    
    def __init__(self):
        self.is_running = False
        self.startup_time = None
        self.last_health_check = None
        self.telegram_application = None  # ✅ NUEVO: Para manejar comandos
    
    async def startup(self):
        """Inicializa el sistema - ACTUALIZADO CON COMANDOS"""
        try:
            logger.info("🚀 Iniciando Trading AI Monitor v2...")
            self.startup_time = datetime.now()
            
            # 1. Validar configuración
            validate_config()
            
            # 2. Testear conexión con Telegram BOT (notifier)
            logger.info("🤖 Probando conexión con Telegram Bot...")
            if not await telegram_notifier.test_connection():
                raise Exception("No se pudo conectar con Telegram Bot")
            
            # ✅ 3. INICIALIZAR SISTEMA DE COMANDOS
            await self._setup_telegram_commands()
            
            # 4. Configurar callback para señales recibidas
            telegram_user_client.set_signal_callback(self.handle_raw_signal_received)
            
            # 5. Limpieza inicial de BD
            trading_db.cleanup_old_signals(7)
            
            # 6. Notificar inicio del sistema
            await self.send_startup_notification()
            
            self.is_running = True
            logger.info("✅ Trading AI Monitor v2 iniciado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error en startup: {e}")
            await telegram_notifier.send_error_notification(str(e), "Startup del sistema")
            raise
    
    async def _setup_telegram_commands(self):
        """Configura el sistema de comandos de Telegram - ✅ NUEVA FUNCIÓN"""
        try:
            # Crear aplicación de Telegram para comandos
            self.telegram_application = Application.builder().token(telegram_notifier.bot.token).build()
            
            # Configurar comandos usando el método setup_commands de telegram_notifier
            await telegram_notifier.setup_commands(self.telegram_application)
            
            # Iniciar el polling de comandos en segundo plano
            await self.telegram_application.initialize()
            await self.telegram_application.start()
            await self.telegram_application.updater.start_polling()
            
            logger.info("✅ Sistema de comandos de Telegram inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error configurando comandos de Telegram: {e}")
            raise
    
    async def shutdown(self):
        """Apaga el sistema de manera controlada - ACTUALIZADO CON COMANDOS"""
        try:
            logger.info("🛑 Apagando Trading AI Monitor v2...")
            self.is_running = False
            
            # ✅ Detener sistema de comandos
            if self.telegram_application:
                await self.telegram_application.updater.stop()
                await self.telegram_application.stop()
                await self.telegram_application.shutdown()
            
            # Detener componentes existentes
            await telegram_user_client.disconnect()
            
            # Enviar notificación de apagado
            uptime = datetime.now() - self.startup_time if self.startup_time else None
            await self.send_shutdown_notification(uptime)
            
            logger.info("✅ Sistema apagado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error en shutdown: {e}")
    
    async def handle_raw_signal_received(self, raw_signal_data: Dict):
        """
        Callback para procesar señales RAW recibidas de Telegram User Client
        """
        try:
            if not self.is_running:
                logger.warning("Sistema no está ejecutándose, ignorando señal")
                return
            
            message_text = raw_signal_data.get('message_text', '')
            logger.info(f"📨 Procesando señal recibida: {message_text[:100]}...")
            
            # Parsear la señal usando helpers.py
            signal_data = parse_signal_message(message_text)
            
            if not signal_data:
                logger.warning("❌ No se pudo parsear la señal")
                return
            
            logger.info(f"✅ Señal parseada: {signal_data['pair']} {signal_data['direction']}")
            
            # Procesar la señal a través del signal manager
            success = await signal_manager.process_new_signal(signal_data)
            
            if not success:
                logger.error(f"❌ Error procesando señal: {signal_data['pair']}")
                await telegram_notifier.send_error_notification(
                    f"Error procesando señal {signal_data['pair']}", 
                    "Procesamiento de señal"
                )
                
        except Exception as e:
            logger.error(f"❌ Error en callback de señal: {e}")
            await telegram_notifier.send_error_notification(str(e), "Callback de señal")
    
    async def send_startup_notification(self):
        """Envía notificación de inicio del sistema"""
        message = f"""
🤖 **Trading AI Monitor v2 INICIADO** 🤖

**Sistema activo y monitoreando señales**
- 🕒 Hora de inicio: {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')}
- 📊 Modo: Análisis y Notificaciones
- 🔍 Monitoreo: Canal de señales (User Account)
- 📢 Salida: Canal de resultados (Bot)
- 💾 Base de datos: Operacional
- ⌨️ Comandos: /operaciones, /estado, /revisar, /seguimiento

**Configuración:**
✅ User Account: Conectado para leer señales
✅ Bot: Conectado para enviar resultados  
✅ Parser: Configurado para formato NeuroTrader
✅ Análisis: Multi-temporalidad activa
✅ Comandos: Sistema de comandos activado

**Esperando señales del canal...**
"""
        await telegram_notifier.send_alert(
            "Sistema Iniciado",
            message,
            "success"
        )
    
    async def send_shutdown_notification(self, uptime: timedelta = None):
        """Envía notificación de apagado del sistema"""
        uptime_str = str(uptime).split('.')[0] if uptime else "Desconocido"
        
        message = f"""
🛑 **Trading AI Monitor v2 APAGADO** 🛑

**Sistema detenido correctamente**
- 🕒 Tiempo de actividad: {uptime_str}
- 📊 Señales procesadas: {signal_manager.get_pending_signals_count()}
- 💾 Base de datos: Respaldada

**Hasta pronto!** 👋
"""
        await telegram_notifier.send_alert(
            "Sistema Apagado", 
            message,
            "info"
        )
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""
        def signal_handler(signum, frame):
            logger.info(f"📞 Señal {signum} recibida, apagando...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Bucle principal de ejecución - ACTUALIZADO"""
        try:
            await self.startup()
            self.setup_signal_handlers()
            
            logger.info("🎧 Iniciando escucha del canal de señales...")
            
            # Iniciar la escucha del canal (esto bloqueará hasta desconexión)
            await telegram_user_client.start_listening()
            
        except Exception as e:
            logger.error(f"❌ Error en bucle principal: {e}")
            await self.shutdown()
    
    async def _system_health_check(self):
        """Verificación periódica del estado del sistema"""
        try:
            now = datetime.now()
            # Verificar cada 30 minutos
            if (self.last_health_check is None or 
                (now - self.last_health_check).total_seconds() >= 1800):
                
                self.last_health_check = now
                
                if not await telegram_notifier.test_connection():
                    logger.warning("❌ Problema de conexión con Telegram Bot detectado")
            
            # Verificar señales pendientes siempre
            pending_count = signal_manager.get_pending_signals_count()
            if pending_count > 0:
                logger.debug(f"🔍 Monitoreando {pending_count} señales pendientes")
                
        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")

async def main():
    """Función principal"""
    monitor = TradingAIMonitor()
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("Apagado por usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    finally:
        if monitor.is_running:
            await monitor.shutdown()

if __name__ == "__main__":
    # Configurar logging
    setup_logging()
    
    # Ejecutar sistema
    asyncio.run(main())