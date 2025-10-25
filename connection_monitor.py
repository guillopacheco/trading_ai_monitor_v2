"""
Monitor de conexión en tiempo real para el Trading Bot
Detección proactiva de fallos de conexión y estado de servicios
"""
import asyncio
import logging
import time
from typing import Dict, List, Callable
from datetime import datetime, timedelta
import aiohttp
import requests

logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """Monitor de estado de conexión y servicios externos"""
    
    def __init__(self):
        self.connection_status = {
            'internet': {'status': True, 'last_check': None, 'response_time': 0},
            'bybit_api': {'status': True, 'last_check': None, 'response_time': 0},
            'telegram_bot': {'status': True, 'last_check': None, 'response_time': 0},
            'database': {'status': True, 'last_check': None, 'response_time': 0}
        }
        
        self.health_checkers = {
            'internet': self._check_internet_connection,
            'bybit_api': self._check_bybit_api,
            'telegram_bot': self._check_telegram_bot,
            'database': self._check_database
        }
        
        self.status_listeners = []
        self.monitoring_task = None
        self.is_monitoring = False
        
        # Configuración
        self.check_interval = 30  # segundos
        self.timeout_threshold = 10  # segundos
        self.failure_threshold = 3  # intentos consecutivos
        
        # Historial de fallos
        self.failure_count = {service: 0 for service in self.connection_status.keys()}
        self.last_failure_time = {service: None for service in self.connection_status.keys()}
    
    def add_status_listener(self, listener: Callable):
        """Agrega un listener para cambios de estado"""
        self.status_listeners.append(listener)
    
    async def _notify_status_change(self, service: str, new_status: bool, old_status: bool):
        """Notifica a los listeners sobre cambios de estado"""
        if new_status != old_status:
            for listener in self.status_listeners:
                try:
                    await listener(service, new_status, old_status)
                except Exception as e:
                    logger.error(f"Error en listener de estado {service}: {e}")
    
    async def _check_internet_connection(self) -> Dict:
        """Verifica conexión a internet"""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://www.google.com', timeout=5) as response:
                    success = response.status == 200
                    response_time = time.time() - start_time
                    
                    return {
                        'status': success,
                        'response_time': response_time,
                        'details': f'HTTP {response.status}'
                    }
        except Exception as e:
            return {
                'status': False,
                'response_time': 0,
                'details': str(e)
            }
    
    async def _check_bybit_api(self) -> Dict:
        """Verifica estado de la API de Bybit"""
        start_time = time.time()
        try:
            from bybit_api import bybit_client
            
            # Intentar obtener el ticker de BTCUSDT como prueba
            ticker = await bybit_client.get_ticker("BTCUSDT")
            response_time = time.time() - start_time
            
            return {
                'status': ticker is not None,
                'response_time': response_time,
                'details': 'API operativa' if ticker else 'Sin datos'
            }
        except Exception as e:
            return {
                'status': False,
                'response_time': 0,
                'details': str(e)
            }
    
    async def _check_telegram_bot(self) -> Dict:
        """Verifica estado del bot de Telegram"""
        start_time = time.time()
        try:
            from notifier import telegram_notifier
            
            # Test de conexión simple
            success = await telegram_notifier.test_connection()
            response_time = time.time() - start_time
            
            return {
                'status': success,
                'response_time': response_time,
                'details': 'Bot conectado' if success else 'Bot desconectado'
            }
        except Exception as e:
            return {
                'status': False,
                'response_time': 0,
                'details': str(e)
            }
    
    async def _check_database(self) -> Dict:
        """Verifica estado de la base de datos"""
        start_time = time.time()
        try:
            from database import trading_db
            
            # Test simple de consulta
            test_result = trading_db.test_connection()
            response_time = time.time() - start_time
            
            return {
                'status': test_result,
                'response_time': response_time,
                'details': 'DB conectada' if test_result else 'DB error'
            }
        except Exception as e:
            return {
                'status': False,
                'response_time': 0,
                'details': str(e)
            }
    
    async def perform_health_check(self, service: str = None) -> Dict:
        """Realiza chequeo de salud de uno o todos los servicios"""
        services_to_check = [service] if service else list(self.health_checkers.keys())
        results = {}
        
        for svc in services_to_check:
            if svc in self.health_checkers:
                old_status = self.connection_status[svc]['status']
                
                # Ejecutar check
                check_result = await self.health_checkers[svc]()
                
                # Actualizar estado
                self.connection_status[svc].update({
                    'status': check_result['status'],
                    'last_check': datetime.now(),
                    'response_time': check_result['response_time'],
                    'details': check_result['details']
                })
                
                # Manejar contador de fallos
                if not check_result['status']:
                    self.failure_count[svc] += 1
                    self.last_failure_time[svc] = datetime.now()
                    
                    if self.failure_count[svc] >= self.failure_threshold:
                        logger.warning(f"⚠️ Servicio {svc} con {self.failure_count[svc]} fallos consecutivos")
                else:
                    self.failure_count[svc] = 0  # Reset counter on success
                
                # Notificar cambio de estado
                await self._notify_status_change(svc, check_result['status'], old_status)
                
                results[svc] = self.connection_status[svc]
        
        return results
    
    async def start_monitoring(self):
        """Inicia el monitoreo continuo"""
        if self.is_monitoring:
            logger.warning("Monitor ya está ejecutándose")
            return
        
        self.is_monitoring = True
        logger.info("🚀 Iniciando monitor de conexión...")
        
        async def monitoring_loop():
            while self.is_monitoring:
                try:
                    await self.perform_health_check()
                    logger.debug("✅ Chequeo de salud completado")
                except Exception as e:
                    logger.error(f"❌ Error en chequeo de salud: {e}")
                
                await asyncio.sleep(self.check_interval)
        
        self.monitoring_task = asyncio.create_task(monitoring_loop())
    
    async def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Monitor de conexión detenido")
    
    def get_connection_status(self, service: str = None) -> Dict:
        """Obtiene el estado actual de conexión"""
        if service:
            return self.connection_status.get(service, {})
        return self.connection_status
    
    def is_service_healthy(self, service: str) -> bool:
        """Verifica si un servicio está saludable"""
        status = self.connection_status.get(service, {})
        return status.get('status', False) and self.failure_count.get(service, 0) < self.failure_threshold
    
    def get_global_status(self) -> Dict:
        """Obtiene estado global del sistema"""
        healthy_services = sum(1 for service in self.connection_status 
                             if self.is_service_healthy(service))
        total_services = len(self.connection_status)
        
        return {
            'global_status': 'HEALTHY' if healthy_services == total_services else 'DEGRADED',
            'healthy_services': healthy_services,
            'total_services': total_services,
            'degraded_services': [svc for svc in self.connection_status 
                                if not self.is_service_healthy(svc)],
            'last_checks': {svc: status['last_check'] 
                          for svc, status in self.connection_status.items()}
        }

# Instancia global
connection_monitor = ConnectionMonitor()