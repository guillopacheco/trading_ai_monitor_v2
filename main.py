"""
Trading Bot v2 - MAIN ENTRY POINT
Sistema completo con autoreconexión integrada
"""
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TradingBot:
    """Bot principal de trading con sistema de reconexión automática"""
    
    def __init__(self):
        self.is_running = False
        self.components = {}
        
        # Inicializar sistema de reconexión PRIMERO
        from connection_monitor import connection_monitor
        from auto_reconnect import initialize_auto_reconnect
        from health_monitor import health_monitor
        
        self.connection_monitor = connection_monitor
        self.auto_reconnect = initialize_auto_reconnect(connection_monitor)
        self.health_monitor = health_monitor
        
        # Configurar manejador de señales para shutdown graceful
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de terminación"""
        logger.info(f"📡 Señal {signum} recibida. Apagando gracefully...")
        self.is_running = False
    
    async def initialize_components(self):
        """Inicializa todos los componentes del sistema"""
        logger.info("🚀 Inicializando componentes del Trading Bot...")
        
        try:
            # 1. Base de datos
            from database import trading_db
            self.components['database'] = trading_db
            logger.info("✅ Base de datos inicializada")
            
            # 2. Cliente Bybit
            from bybit_api import bybit_client
            await bybit_client.initialize()
            self.components['bybit'] = bybit_client
            logger.info("✅ Cliente Bybit inicializado")
            
            # 3. Notificador Telegram
            from notifier import telegram_notifier
            self.components['telegram'] = telegram_notifier
            logger.info("✅ Notificador Telegram inicializado")
            
            # 4. Gestor de señales
            from signal_manager import signal_manager
            self.components['signal_manager'] = signal_manager
            logger.info("✅ Gestor de señales inicializado")
            
            # 5. Rastreador de operaciones
            from operation_tracker import operation_tracker
            self.components['operation_tracker'] = operation_tracker
            logger.info("✅ Rastreador de operaciones inicializado")
            
            # 6. Configurar comandos de Telegram
            from telegram.ext import Application
            application = Application.builder().token(telegram_notifier.bot.token).build()
            await telegram_notifier.setup_commands(application)
            self.components['telegram_application'] = application
            logger.info("✅ Comandos Telegram configurados")
            
            # 7. Registrar listeners para cambios de conexión
            self._setup_connection_listeners()
            
            logger.info("🎉 Todos los componentes inicializados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    def _setup_connection_listeners(self):
        """Configura listeners para cambios de estado de conexión"""
        
        async def connection_status_handler(service: str, new_status: bool, old_status: bool):
            """Maneja cambios de estado de conexión"""
            if not new_status and old_status:
                # Servicio cayó
                self.health_monitor.record_connection_issue(service, "Desconectado")
                logger.warning(f"⚠️ {service} desconectado. Sistema de autoreconexión activado.")
                
                # Intentar reconexión inmediata
                asyncio.create_task(self.auto_reconnect.trigger_reconnection(service))
                
            elif new_status and not old_status:
                # Servicio recuperado
                self.health_monitor.record_reconnect_attempt(service, True)
                logger.info(f"✅ {service} recuperado automáticamente")
        
        # Registrar handler
        self.connection_monitor.add_status_listener(connection_status_handler)
    
    async def perform_health_check(self):
        """Realiza chequeo completo de salud"""
        try:
            health_report = self.health_monitor.get_detailed_report()
            
            if health_report['health_status']['overall_status'] == 'DEGRADED':
                logger.warning("🔧 Sistema degradado detectado")
                
                # Notificar por Telegram si está disponible
                if self.connection_monitor.is_service_healthy('telegram_bot'):
                    alert_msg = "⚠️ **SISTEMA DEGRADADO**\n\n"
                    for alert in health_report['health_status']['alerts']:
                        alert_msg += f"• {alert}\n"
                    
                    await self.components['telegram'].send_alert(
                        "Alerta de Salud del Sistema", 
                        alert_msg, 
                        "warning"
                    )
            
            return health_report
            
        except Exception as e:
            logger.error(f"❌ Error en chequeo de salud: {e}")
    
    async def emergency_recovery_protocol(self):
        """Protocolo de recuperación de emergencia"""
        logger.warning("🚨 ACTIVANDO PROTOCOLO DE RECUPERACIÓN DE EMERGENCIA")
        
        try:
            # 1. Detener monitoreo temporalmente
            await self.connection_monitor.stop_monitoring()
            
            # 2. Realizar recuperación completa
            success = await self.auto_reconnect.perform_emergency_recovery()
            
            # 3. Reanudar monitoreo
            await self.connection_monitor.start_monitoring()
            
            if success:
                logger.info("✅ Recuperación de emergencia exitosa")
                
                # Notificar recuperación
                if self.connection_monitor.is_service_healthy('telegram_bot'):
                    await self.components['telegram'].send_alert(
                        "Recuperación del Sistema",
                        "✅ El sistema se ha recuperado exitosamente de una condición degradada",
                        "success"
                    )
            else:
                logger.error("❌ Recuperación de emergencia fallida")
                
            return success
            
        except Exception as e:
            logger.error(f"💥 Error en protocolo de emergencia: {e}")
            return False
    
    async def run(self):
        """Loop principal del bot"""
        self.is_running = True
        logger.info("🤖 Iniciando Trading Bot v2...")
        
        # Inicializar componentes
        if not await self.initialize_components():
            logger.error("❌ No se pudieron inicializar componentes. Saliendo...")
            return
        
        # Iniciar sistema de autoreconexión
        await self.auto_reconnect.start_auto_reconnect()
        
        # Chequeo de salud inicial
        initial_health = await self.perform_health_check()
        logger.info(f"📊 Estado inicial: {initial_health['health_status']['overall_status']}")
        
        # Contadores para tareas periódicas
        last_health_check = time.time()
        last_operation_check = time.time()
        health_check_interval = 300  # 5 minutos
        operation_check_interval = 60  # 1 minuto
        
        logger.info("🎯 Trading Bot ejecutándose. Esperando señales...")
        
        try:
            while self.is_running:
                current_time = time.time()
                
                # Chequeo periódico de salud
                if current_time - last_health_check >= health_check_interval:
                    await self.perform_health_check()
                    last_health_check = current_time
                
                # Verificación periódica de operaciones abiertas
                if current_time - last_operation_check >= operation_check_interval:
                    try:
                        open_ops = self.components['operation_tracker'].get_open_operations()
                        if open_ops:
                            logger.debug(f"📊 Monitoreando {len(open_ops)} operaciones abiertas")
                    except Exception as e:
                        logger.error(f"❌ Error verificando operaciones: {e}")
                    
                    last_operation_check = current_time
                
                # Verificar si necesitamos recuperación de emergencia
                global_status = self.connection_monitor.get_global_status()
                if global_status['global_status'] == 'DEGRADED':
                    degraded_count = len(global_status['degraded_services'])
                    if degraded_count >= 2:  # Si 2+ servicios están caídos
                        logger.warning(f"🚨 {degraded_count} servicios degradados - Considerando recuperación de emergencia")
                        await self.emergency_recovery_protocol()
                
                # Esperar antes de siguiente iteración
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"💥 Error crítico en loop principal: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Apagado graceful del sistema"""
        logger.info("🛑 Apagando Trading Bot...")
        
        try:
            # 1. Detener sistema de autoreconexión
            await self.auto_reconnect.stop_auto_reconnect()
            
            # 2. Cerrar conexiones
            if 'bybit' in self.components:
                await self.components['bybit'].close()
            
            # 3. Guardar estado final
            final_health = self.health_monitor.get_detailed_report()
            logger.info(f"📊 Estado final: {final_health['health_status']['overall_status']}")
            logger.info(f"⏱️  Uptime: {final_health['performance_metrics']['uptime_hours']:.2f} horas")
            
            # 4. Notificar apagado si Telegram funciona
            if (self.connection_monitor and 
                self.connection_monitor.is_service_healthy('telegram_bot') and
                'telegram' in self.components):
                
                await self.components['telegram'].send_alert(
                    "Apagado del Sistema",
                    f"🔴 Trading Bot apagado\n\n"
                    f"⏱️ Uptime: {final_health['performance_metrics']['uptime_hours']:.2f} horas\n"
                    f"📈 Señales procesadas: {final_health['performance_metrics']['signals_processed']}",
                    "info"
                )
            
        except Exception as e:
            logger.error(f"❌ Error durante apagado: {e}")
        finally:
            logger.info("👋 Trading Bot apagado exitosamente")

async def main():
    """Función principal"""
    bot = TradingBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("📡 Interrupción por usuario detectada")
    except Exception as e:
        logger.error(f"💥 Error fatal: {e}")
        # Intentar notificar error crítico
        try:
            from notifier import telegram_notifier
            await telegram_notifier.send_error_notification(
                str(e), 
                "Error fatal en main()"
            )
        except:
            pass  # Si no podemos notificar, al menos loguear
    finally:
        if bot.is_running:
            await bot.shutdown()

if __name__ == "__main__":
    # Ejecutar bot
    asyncio.run(main())