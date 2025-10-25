"""
Sistema de reconexión automática para el Trading Bot
Maneja recuperación automática de conexiones caídas
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AutoReconnectManager:
    """Gestor de reconexión automática para servicios"""
    
    def __init__(self, connection_monitor):
        self.connection_monitor = connection_monitor
        self.reconnect_strategies = {
            'internet': self._reconnect_internet,
            'bybit_api': self._reconnect_bybit_api,
            'telegram_bot': self._reconnect_telegram_bot,
            'database': self._reconnect_database
        }
        
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 10  # segundos entre intentos
        self.backoff_factor = 2  # factor de crecimiento del delay
        
        # Estado de recuperación
        self.recovery_in_progress = False
        self.last_recovery_time = None
        
        # Registrar listener para cambios de estado
        self.connection_monitor.add_status_listener(self._handle_status_change)
    
    async def _handle_status_change(self, service: str, new_status: bool, old_status: bool):
        """Maneja cambios de estado de servicios"""
        if not new_status and old_status:  # Servicio cayó
            logger.warning(f"⚠️ Servicio {service} se desconectó. Iniciando recuperación...")
            await self.trigger_reconnection(service)
        elif new_status and not old_status:  # Servicio se recuperó
            logger.info(f"✅ Servicio {service} recuperado automáticamente")
            self.reconnect_attempts[service] = 0  # Reset attempts
    
    async def trigger_reconnection(self, service: str):
        """Inicia proceso de reconexión para un servicio"""
        if service not in self.reconnect_strategies:
            logger.error(f"❌ No hay estrategia de reconexión para {service}")
            return False
        
        attempts = self.reconnect_attempts.get(service, 0)
        
        if attempts >= self.max_reconnect_attempts:
            logger.error(f"🚨 Máximos intentos de reconexión alcanzados para {service}")
            return False
        
        self.reconnect_attempts[service] = attempts + 1
        delay = self.reconnect_delay * (self.backoff_factor ** attempts)
        
        logger.info(f"🔄 Intentando reconectar {service} (intento {attempts + 1}, delay: {delay}s)")
        
        # Esperar antes del intento
        await asyncio.sleep(delay)
        
        try:
            # Ejecutar estrategia de reconexión específica
            success = await self.reconnect_strategies[service]()
            
            if success:
                logger.info(f"✅ Reconexión exitosa para {service}")
                self.reconnect_attempts[service] = 0
                
                # Verificar estado después de reconexión
                await self.connection_monitor.perform_health_check(service)
                return True
            else:
                logger.warning(f"❌ Reconexión fallida para {service}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error durante reconexión de {service}: {e}")
            return False
    
    async def _reconnect_internet(self) -> bool:
        """Estrategia de reconexión para internet"""
        logger.info("🔧 Reintentando conexión a internet...")
        
        # Simplemente esperar y verificar - el sistema operativo maneja la reconexión
        await asyncio.sleep(5)
        
        # Verificar si se recuperó
        result = await self.connection_monitor.perform_health_check('internet')
        return result.get('internet', {}).get('status', False)
    
    async def _reconnect_bybit_api(self) -> bool:
        """Estrategia de reconexión para API de Bybit"""
        logger.info("🔧 Reconectando API de Bybit...")
        
        try:
            from bybit_api import bybit_client
            
            # Reiniciar cliente de Bybit
            await bybit_client.reconnect()
            
            # Verificar conexión
            await asyncio.sleep(2)
            ticker = await bybit_client.get_ticker("BTCUSDT")
            
            return ticker is not None
            
        except Exception as e:
            logger.error(f"❌ Error reconectando Bybit: {e}")
            return False
    
    async def _reconnect_telegram_bot(self) -> bool:
        """Estrategia de reconexión para bot de Telegram"""
        logger.info("🔧 Reconectando bot de Telegram...")
        
        try:
            from notifier import telegram_notifier
            
            # Reinicializar bot
            telegram_notifier._initialize_bot()
            
            # Verificar conexión
            await asyncio.sleep(2)
            success = await telegram_notifier.test_connection()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error reconectando Telegram: {e}")
            return False
    
    async def _reconnect_database(self) -> bool:
        """Estrategia de reconexión para base de datos"""
        logger.info("🔧 Reconectando base de datos...")
        
        try:
            from database import trading_db
            
            # Reabrir conexión
            trading_db.reconnect()
            
            # Verificar conexión
            await asyncio.sleep(1)
            success = trading_db.test_connection()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error reconectando base de datos: {e}")
            return False
    
    async def perform_emergency_recovery(self):
        """Realiza recuperación de emergencia de todos los servicios"""
        if self.recovery_in_progress:
            logger.warning("🔄 Recuperación de emergencia ya en progreso...")
            return
        
        self.recovery_in_progress = True
        logger.warning("🚨 INICIANDO RECUPERACIÓN DE EMERGENCIA")
        
        try:
            # Obtener servicios caídos
            status = self.connection_monitor.get_global_status()
            degraded_services = status.get('degraded_services', [])
            
            if not degraded_services:
                logger.info("✅ No hay servicios degradados para recuperar")
                return True
            
            logger.warning(f"🔧 Recuperando {len(degraded_services)} servicios: {degraded_services}")
            
            # Reconectar servicios en paralelo
            recovery_tasks = []
            for service in degraded_services:
                task = asyncio.create_task(self.trigger_reconnection(service))
                recovery_tasks.append(task)
            
            # Esperar resultados
            results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
            
            successful_recoveries = sum(1 for r in results if r is True)
            
            logger.info(f"📊 Recuperación completada: {successful_recoveries}/{len(degraded_services)} exitosas")
            
            self.last_recovery_time = datetime.now()
            return successful_recoveries > 0
            
        except Exception as e:
            logger.error(f"💥 Error durante recuperación de emergencia: {e}")
            return False
        finally:
            self.recovery_in_progress = False
    
    def get_reconnect_status(self) -> Dict:
        """Obtiene estado actual de reconexión"""
        return {
            'reconnect_attempts': self.reconnect_attempts,
            'recovery_in_progress': self.recovery_in_progress,
            'last_recovery_time': self.last_recovery_time,
            'max_attempts': self.max_reconnect_attempts
        }
    
    async def start_auto_reconnect(self):
        """Inicia el sistema de autoreconexión"""
        logger.info("🚀 Sistema de autoreconexión iniciado")
        
        # Realizar chequeo inicial
        await self.connection_monitor.perform_health_check()
        
        # Iniciar monitoreo continuo
        await self.connection_monitor.start_monitoring()
    
    async def stop_auto_reconnect(self):
        """Detiene el sistema de autoreconexión"""
        await self.connection_monitor.stop_monitoring()
        logger.info("🛑 Sistema de autoreconexión detenido")

# Instancia global (se inicializará después en main.py)
auto_reconnect_manager = None

def initialize_auto_reconnect(connection_monitor):
    """Inicializa el gestor de autoreconexión"""
    global auto_reconnect_manager
    auto_reconnect_manager = AutoReconnectManager(connection_monitor)
    return auto_reconnect_manager