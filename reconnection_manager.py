# reconnection_manager.py
"""
Gestor de reconexión automática para componentes del sistema
"""
import asyncio
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ReconnectionManager:
    """Manejador de reconexión con backoff exponencial y circuit breaker"""
    
    def __init__(self, max_retries: int = 10, base_delay: float = 5.0, max_delay: float = 300.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_counts: Dict[str, int] = {}
        self.last_failure_time: Dict[str, datetime] = {}
        self.circuit_open: Dict[str, datetime] = {}
        self.success_count: Dict[str, int] = {}
    
    async def execute_with_retry(self, component_name: str, operation: Callable, 
                               *args, **kwargs) -> Any:
        """
        Ejecuta una operación con reintentos automáticos
        """
        if self._is_circuit_open(component_name):
            logger.warning(f"⏳ Circuito abierto para {component_name}, esperando...")
            return None
        
        for attempt in range(self.max_retries):
            try:
                result = await operation(*args, **kwargs)
                self._on_success(component_name)
                return result
                
            except Exception as e:
                await self._handle_failure(component_name, e, attempt)
                
        logger.error(f"❌ Máximo de reintentos alcanzado para {component_name}")
        self._open_circuit(component_name)
        return None
    
    def _is_circuit_open(self, component_name: str) -> bool:
        """Verifica si el circuito está abierto para un componente"""
        if component_name not in self.circuit_open:
            return False
        
        open_time = self.circuit_open[component_name]
        if datetime.now() - open_time > timedelta(minutes=5):
            # Intentar resetear después de 5 minutos
            logger.info(f"🔄 Intentando resetear circuito para {component_name}")
            self.circuit_open.pop(component_name, None)
            return False
            
        return True
    
    def _on_success(self, component_name: str):
        """Limpia el estado después de una operación exitosa"""
        self.retry_counts.pop(component_name, None)
        self.last_failure_time.pop(component_name, None)
        self.circuit_open.pop(component_name, None)
        
        # Contar éxitos consecutivos
        self.success_count[component_name] = self.success_count.get(component_name, 0) + 1
        
        if self.success_count[component_name] == 1:
            logger.info(f"✅ Reconexión exitosa para {component_name}")
        elif self.success_count[component_name] % 10 == 0:
            logger.info(f"✅ {self.success_count[component_name]} operaciones exitosas consecutivas para {component_name}")
    
    async def _handle_failure(self, component_name: str, error: Exception, attempt: int):
        """Maneja fallos con backoff exponencial"""
        self.retry_counts[component_name] = attempt + 1
        self.last_failure_time[component_name] = datetime.now()
        self.success_count[component_name] = 0  # Resetear contador de éxitos
        
        # Calcular delay con backoff exponencial
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        logger.warning(
            f"🔄 Reintento {attempt + 1}/{self.max_retries} para {component_name} "
            f"en {delay:.1f}s - Error: {str(error)[:100]}"
        )
        
        await asyncio.sleep(delay)
        
        # Abrir circuito después de varios intentos fallidos
        if attempt >= 3:
            self._open_circuit(component_name)
    
    def _open_circuit(self, component_name: str):
        """Abre el circuito para un componente"""
        self.circuit_open[component_name] = datetime.now()
        logger.error(f"🚨 Circuito abierto para {component_name} después de múltiples fallos")
    
    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Obtiene el estado actual de un componente"""
        status = {
            'circuit_open': component_name in self.circuit_open,
            'retry_count': self.retry_counts.get(component_name, 0),
            'success_count': self.success_count.get(component_name, 0),
        }
        
        if component_name in self.last_failure_time:
            status['last_failure'] = self.last_failure_time[component_name]
            status['time_since_failure'] = datetime.now() - self.last_failure_time[component_name]
        
        if component_name in self.circuit_open:
            status['circuit_open_since'] = self.circuit_open[component_name]
            status['circuit_open_duration'] = datetime.now() - self.circuit_open[component_name]
        
        return status
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los componentes monitoreados"""
        all_components = set(list(self.retry_counts.keys()) + 
                           list(self.circuit_open.keys()) + 
                           list(self.success_count.keys()))
        
        return {comp: self.get_component_status(comp) for comp in all_components}

# Instancia global
reconnection_manager = ReconnectionManager(
    max_retries=8,
    base_delay=3.0,
    max_delay=600.0  # 10 minutos máximo
)