# health_monitor.py - VERSIÓN CORREGIDA
"""
Sistema de monitorización de salud mejorado - CON DETECCIÓN DE DESCONEXIÓN
"""
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitor de salud del sistema trading - MEJORADO"""
    
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.health_data = {
            'start_time': datetime.now(),
            'last_telegram_activity': None,
            'last_signal_received': None,
            'last_bybit_api_call': None,
            'last_error': None,
            'total_signals_processed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'connection_issues': 0,
            'reconnects_attempted': 0,
            'reconnects_successful': 0
        }
        
        # Umbrales de alerta
        self.alert_thresholds = {
            'max_inactivity_minutes': 5,
            'max_error_count_per_hour': 10,
            'max_connection_issues_per_hour': 5
        }
        
        # Historial de eventos
        self.event_history = []
        self.connection_status = {
            'internet': True,
            'bybit_api': True, 
            'telegram': True,
            'database': True
        }
        
        # ✅ NUEVO: Contadores para estadísticas
        self.error_count = 0
        self.warning_count = 0
        self.operations_tracked = 0
        self.last_update = datetime.now()
    
    def record_telegram_bot_activity(self):
        """Registra actividad del bot de Telegram"""
        self.health_data['last_telegram_activity'] = datetime.now()
        self._log_event("TELEGRAM_ACTIVITY", "Bot de Telegram activo")
    
    def record_signal_processed(self, signal_data: Dict):
        """Registra procesamiento de señal"""
        self.health_data['last_signal_received'] = datetime.now()
        self.health_data['total_signals_processed'] += 1
        self._log_event("SIGNAL_PROCESSED", f"Señal {signal_data.get('pair', 'Unknown')} procesada")
    
    def record_bybit_api_call(self, endpoint: str):
        """Registra llamada a API de Bybit"""
        self.health_data['last_bybit_api_call'] = datetime.now()
        self._log_event("BYBIT_API_CALL", f"API call: {endpoint}")
    
    def record_error(self, error_msg: str, context: str = ""):
        """Registra error del sistema"""
        self.health_data['last_error'] = {
            'timestamp': datetime.now(),
            'message': error_msg,
            'context': context
        }
        self.health_data['failed_trades'] += 1
        self.error_count += 1
        self._log_event("ERROR", f"{context}: {error_msg}", "ERROR")
    
    def record_successful_trade(self):
        """Registra trade exitoso"""
        self.health_data['successful_trades'] += 1
        self._log_event("TRADE_SUCCESS", "Trade ejecutado exitosamente")
    
    def record_connection_issue(self, service: str, issue: str):
        """Registra problema de conexión"""
        self.health_data['connection_issues'] += 1
        self.connection_status[service] = False
        self.warning_count += 1
        self._log_event("CONNECTION_ISSUE", f"{service}: {issue}", "WARNING")
    
    def record_reconnect_attempt(self, service: str, success: bool):
        """Registra intento de reconexión"""
        self.health_data['reconnects_attempted'] += 1
        if success:
            self.health_data['reconnects_successful'] += 1
            self.connection_status[service] = True
            self._log_event("RECONNECT_SUCCESS", f"Reconexión exitosa: {service}")
        else:
            self._log_event("RECONNECT_FAILED", f"Reconexión fallida: {service}", "WARNING")
    
    def _log_event(self, event_type: str, message: str, level: str = "INFO"):
        """Registra evento en el historial"""
        event = {
            'timestamp': datetime.now(),
            'type': event_type,
            'message': message,
            'level': level
        }
        self.event_history.append(event)
        self.last_update = datetime.now()
        
        # Mantener solo últimos 1000 eventos
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]
    
    # ✅ NUEVO: Métodos de verificación de salud que el command_bot necesita
    def check_database_health(self) -> bool:
        """Verifica salud de la base de datos - NUEVO MÉTODO"""
        try:
            import sqlite3
            # Verificación básica de BD
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == 1:
                self.connection_status['database'] = True
                return True
            else:
                self.connection_status['database'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando BD: {e}")
            self.connection_status['database'] = False
            return False
    
    def check_telegram_health(self) -> bool:
        """Verifica salud de Telegram - NUEVO MÉTODO"""
        try:
            # Verificar actividad reciente de Telegram
            if self.health_data['last_telegram_activity']:
                inactivity = (datetime.now() - self.health_data['last_telegram_activity']).total_seconds() / 60
                if inactivity < 10:  # Menos de 10 minutos de inactividad
                    self.connection_status['telegram'] = True
                    return True
            
            self.connection_status['telegram'] = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Error verificando Telegram: {e}")
            self.connection_status['telegram'] = False
            return False
    
    def check_bybit_health(self) -> bool:
        """Verifica salud de Bybit API - NUEVO MÉTODO"""
        try:
            # Verificar actividad reciente de Bybit
            if self.health_data['last_bybit_api_call']:
                inactivity = (datetime.now() - self.health_data['last_bybit_api_call']).total_seconds() / 60
                if inactivity < 15:  # Menos de 15 minutos de inactividad
                    self.connection_status['bybit_api'] = True
                    return True
            
            self.connection_status['bybit_api'] = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Error verificando Bybit: {e}")
            self.connection_status['bybit_api'] = False
            return False
    
    def check_main_system_health(self) -> bool:
        """Verifica si el sistema principal está activo - NUEVO MÉTODO"""
        try:
            # Verificar que los componentes principales estén funcionando
            from signal_manager import signal_manager
            
            # Verificar que signal_manager esté funcionando
            if hasattr(signal_manager, 'active_monitoring'):
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando sistema principal: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, any]:
        """Obtiene estado completo del sistema - NUEVO MÉTODO"""
        try:
            database_health = self.check_database_health()
            telegram_health = self.check_telegram_health()
            bybit_health = self.check_bybit_health()
            main_system_health = self.check_main_system_health()
            
            # Calcular salud general
            overall_health = (database_health and telegram_health and 
                            bybit_health and main_system_health)
            
            return {
                'database': database_health,
                'telegram_user': telegram_health,
                'bybit_api': bybit_health,
                'main_system': main_system_health,
                'command_bot': True,  # Si estamos aquí, el bot de comandos funciona
                'overall_health': overall_health,
                'operations_tracked': self.operations_tracked,
                'errors': self.error_count,
                'warnings': self.warning_count,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del sistema: {e}")
            return self._get_error_status()
    
    def _get_error_status(self) -> Dict[str, any]:
        """Retorna estado de error cuando falla la verificación"""
        return {
            'database': False,
            'telegram_user': False,
            'bybit_api': False,
            'main_system': False,
            'command_bot': False,
            'overall_health': False,
            'operations_tracked': 0,
            'errors': self.error_count + 1,  # Incrementar por este error
            'warnings': self.warning_count,
            'last_update': datetime.now().isoformat()
        }
    
    def check_system_health(self) -> Dict:
        """Verifica salud del sistema - MÉTODO EXISTENTE MEJORADO"""
        current_time = datetime.now()
        health_status = {
            'overall_status': 'HEALTHY',
            'uptime_minutes': self._get_uptime_minutes(),
            'components': {},
            'alerts': [],
            'connection_status': self.connection_status.copy()
        }
        
        # Verificar inactividad de Telegram
        if self.health_data['last_telegram_activity']:
            inactivity = (current_time - self.health_data['last_telegram_activity']).total_seconds() / 60
            if inactivity > self.alert_thresholds['max_inactivity_minutes']:
                health_status['alerts'].append(f"Telegram inactivo por {inactivity:.1f} minutos")
                health_status['overall_status'] = 'DEGRADED'
        
        # Verificar inactividad de señales
        if self.health_data['last_signal_received']:
            signal_inactivity = (current_time - self.health_data['last_signal_received']).total_seconds() / 60
            if signal_inactivity > 30:  # 30 minutos sin señales
                health_status['alerts'].append(f"Sin señales por {signal_inactivity:.1f} minutos")
        
        # Verificar errores recientes
        recent_errors = self._get_recent_events('ERROR', hours=1)
        if len(recent_errors) > self.alert_thresholds['max_error_count_per_hour']:
            health_status['alerts'].append(f"Demasiados errores: {len(recent_errors)} en última hora")
            health_status['overall_status'] = 'DEGRADED'
        
        # Verificar problemas de conexión recientes
        recent_connection_issues = self._get_recent_events('CONNECTION_ISSUE', hours=1)
        if len(recent_connection_issues) > self.alert_thresholds['max_connection_issues_per_hour']:
            health_status['alerts'].append(f"Demasiados problemas de conexión: {len(recent_connection_issues)} en última hora")
            health_status['overall_status'] = 'DEGRADED'
        
        # Verificar servicios desconectados
        disconnected_services = [svc for svc, status in self.connection_status.items() if not status]
        if disconnected_services:
            health_status['alerts'].append(f"Servicios desconectados: {', '.join(disconnected_services)}")
            health_status['overall_status'] = 'DEGRADED'
        
        # Estadísticas de componentes
        health_status['components'] = {
            'telegram_bot': {
                'status': 'ACTIVE' if self.health_data['last_telegram_activity'] else 'INACTIVE',
                'last_activity': self.health_data['last_telegram_activity']
            },
            'signal_processor': {
                'status': 'ACTIVE' if self.health_data['last_signal_received'] else 'INACTIVE',
                'total_processed': self.health_data['total_signals_processed'],
                'last_signal': self.health_data['last_signal_received']
            },
            'bybit_api': {
                'status': 'ACTIVE' if self.health_data['last_bybit_api_call'] else 'INACTIVE',
                'last_call': self.health_data['last_bybit_api_call']
            },
            'trading_performance': {
                'success_rate': self._calculate_success_rate(),
                'total_trades': self.health_data['successful_trades'] + self.health_data['failed_trades']
            },
            'connection_health': {
                'total_issues': self.health_data['connection_issues'],
                'reconnect_success_rate': self._calculate_reconnect_success_rate(),
                'reconnects_attempted': self.health_data['reconnects_attempted']
            }
        }
        
        return health_status
    
    def _get_uptime_minutes(self) -> float:
        """Calcula uptime del sistema en minutos"""
        return (datetime.now() - self.health_data['start_time']).total_seconds() / 60
    
    def _get_recent_events(self, event_type: str, hours: int = 1) -> List:
        """Obtiene eventos recientes de un tipo específico"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [event for event in self.event_history 
                if event['type'] == event_type and event['timestamp'] > cutoff_time]
    
    def _calculate_success_rate(self) -> float:
        """Calcula tasa de éxito de trades"""
        total = self.health_data['successful_trades'] + self.health_data['failed_trades']
        if total == 0:
            return 0.0
        return (self.health_data['successful_trades'] / total) * 100
    
    def _calculate_reconnect_success_rate(self) -> float:
        """Calcula tasa de éxito de reconexiones"""
        if self.health_data['reconnects_attempted'] == 0:
            return 100.0  # No se intentaron reconexiones = 100% éxito
        return (self.health_data['reconnects_successful'] / self.health_data['reconnects_attempted']) * 100
    
    def get_detailed_report(self) -> Dict:
        """Genera reporte detallado de salud - MEJORADO"""
        health = self.check_system_health()
        
        report = {
            'timestamp': datetime.now(),
            'health_status': health,
            'performance_metrics': {
                'uptime_hours': self._get_uptime_minutes() / 60,
                'signals_processed': self.health_data['total_signals_processed'],
                'success_rate': self._calculate_success_rate(),
                'reconnect_success_rate': self._calculate_reconnect_success_rate()
            },
            'recent_events': self.event_history[-20:],  # Últimos 20 eventos
            'recommendations': self._generate_recommendations(health)
        }
        
        return report
    
    def _generate_recommendations(self, health_status: Dict) -> List[str]:
        """Genera recomendaciones basadas en el estado de salud"""
        recommendations = []
        
        if health_status['overall_status'] == 'DEGRADED':
            recommendations.append("🔧 Sistema degradado - Revisar logs y considerar reinicio")
        
        if any('inactivo' in alert.lower() for alert in health_status['alerts']):
            recommendations.append("🔄 Verificar conectividad de servicios externos")
        
        if health_status['connection_status'] and any(not status for status in health_status['connection_status'].values()):
            recommendations.append("🌐 Servicios desconectados - El sistema de autoreconexión debería actuar automáticamente")
        
        recent_errors = self._get_recent_events('ERROR', hours=1)
        if len(recent_errors) > 5:
            recommendations.append("🐛 Alto número de errores - Revisar estabilidad del código")
        
        if self._calculate_success_rate() < 50:
            recommendations.append("📈 Baja tasa de éxito - Revisar estrategia de trading")
        
        return recommendations

# Instancia global
health_monitor = HealthMonitor()