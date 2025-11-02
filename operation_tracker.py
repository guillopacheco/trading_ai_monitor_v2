"""
Sistema de seguimiento automático de operaciones abiertas - CORREGIDO
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from database import trading_db
from notifier import telegram_notifier
from indicators import indicators_calculator
from bybit_monitor import bybit_monitor
from roi_manager import roi_manager, ROIAction  # ✅ AGREGAR ESTE IMPORT

logger = logging.getLogger(__name__)

@dataclass
class OperationRecommendation:
    """Recomendación para operación abierta"""
    action: str  # MANTENER, CERRAR_PARCIAL, CERRAR_TOTAL, REVERTIR
    reason: str
    confidence: str  # ALTA, MEDIA, BAJA
    details: Dict

class OperationTracker:
    """Rastrea operaciones abiertas automáticamente"""
    
    def __init__(self):
        self.open_operations: Dict[str, Dict] = {}
        self.check_interval = 120  # segundos entre verificaciones (2 minutos)
        self.is_tracking = False
    
    async def auto_detect_operations(self) -> bool:
        """Detecta automáticamente operaciones abiertas en Bybit - MEJORADO"""
        try:
            logger.info("🔍 Buscando operaciones abiertas en Bybit...")
            
            open_positions = await bybit_monitor.get_open_positions()
            
            if not open_positions:
                logger.info("📭 No hay operaciones abiertas en Bybit")
                return False
            
            operations_added = 0
            for position in open_positions:
                operation_id = await self._create_operation_from_position(position)
                if operation_id:
                    operations_added += 1
            
            logger.info(f"✅ {operations_added} operaciones agregadas al seguimiento")
            
            # ✅ INICIAR TRACKING SI HAY OPERACIONES
            if operations_added > 0 and not self.is_tracking:
                asyncio.create_task(self._start_tracking())
                
            return operations_added > 0
            
        except Exception as e:
            logger.error(f"❌ Error en detección automática: {e}")
            return False
    
    async def _create_operation_from_position(self, position: Dict) -> Optional[str]:
        """Crea una operación de seguimiento desde una posición de Bybit"""
        try:
            symbol = position['symbol']
            direction = "LONG" if position['side'] == "BUY" else "SHORT"
            
            # Verificar si ya estamos siguiendo esta operación
            existing_id = self._find_existing_operation(symbol, direction)
            if existing_id:
                logger.debug(f"🔄 Operación ya en seguimiento: {symbol} {direction}")
                return existing_id
            
            operation_id = f"{symbol}_{direction}_{datetime.now().strftime('%H%M%S')}"
            
            # Crear signal_data básica para el seguimiento
            signal_data = {
                'pair': symbol,
                'direction': direction,
                'entry': position['entry_price'],
                'leverage': position['leverage'],
                'size': position['size'],
                # TPs estimados basados en dirección
                'tp1': self._calculate_tp_level(position['entry_price'], direction, 1),
                'tp2': self._calculate_tp_level(position['entry_price'], direction, 2),
                'tp3': self._calculate_tp_level(position['entry_price'], direction, 3),
                'tp4': self._calculate_tp_level(position['entry_price'], direction, 4)
            }
            
            operation = {
                'id': operation_id,
                'signal_data': signal_data,
                'actual_entry': position['entry_price'],
                'current_price': position['entry_price'],  # Inicialmente igual al entry
                'size': position['size'],
                'leverage': position['leverage'],
                'open_time': datetime.fromtimestamp(int(position['created_time']) / 1000),
                'max_roi': 0,
                'min_roi': 0,
                'current_roi': 0,  # ✅ AGREGAR: ROI actual
                'status': 'open',
                'recommendation_history': [],
                'source': 'bybit_auto'
            }
            
            self.open_operations[operation_id] = operation
            
            logger.info(f"✅ Operación detectada: {symbol} {direction} @ {position['entry_price']}")
            
            # Iniciar tracking si no está activo
            if not self.is_tracking and self.open_operations:
                asyncio.create_task(self._start_tracking())
            
            return operation_id
            
        except Exception as e:
            logger.error(f"❌ Error creando operación desde posición: {e}")
            return None
    
    def _find_existing_operation(self, symbol: str, direction: str) -> Optional[str]:
        """Busca si ya existe una operación igual en seguimiento"""
        for op_id, operation in self.open_operations.items():
            if (operation['signal_data']['pair'] == symbol and 
                operation['signal_data']['direction'] == direction and
                operation['status'] == 'open'):
                return op_id
        return None
    
    def _calculate_tp_level(self, entry_price: float, direction: str, level: int) -> float:
        """Calcula niveles de TP estimados"""
        multiplier = 0.02 * level  # 2%, 4%, 6%, 8%
        if direction == "LONG":
            return round(entry_price * (1 + multiplier), 6)
        else:
            return round(entry_price * (1 - multiplier), 6)
    
    async def _start_tracking(self):
        """Inicia el seguimiento continuo de operaciones"""
        self.is_tracking = True
        logger.info("🚀 Iniciando seguimiento automático de operaciones")
        
        while self.is_tracking and self.open_operations:
            try:
                # Actualizar precios y verificar cada operación
                for operation_id, operation in list(self.open_operations.items()):
                    if operation['status'] == 'open':
                        await self._check_operation_status(operation)
                
                # Verificar si hay nuevas operaciones cada 5 minutos
                if len(self.open_operations) == 0:
                    await asyncio.sleep(300)  # Esperar 5 minutos antes de revisar nuevamente
                    await self.auto_detect_operations()
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error en seguimiento automático: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_operation_status(self, operation: Dict):
        """Verifica el estado de una operación - ACTUALIZADO CON ROI"""
        try:
            pair = operation['signal_data']['pair']
            
            # Obtener precio actual
            current_price = await self._get_current_price(pair)
            if not current_price:
                return
            
            operation['current_price'] = current_price
            
            # Calcular ROI actual
            roi = self._calculate_roi(operation, current_price)
            operation['current_roi'] = roi
            
            # Actualizar ROI máximo/mínimo
            operation['max_roi'] = max(operation['max_roi'], roi)
            operation['min_roi'] = min(operation['min_roi'], roi)
            
            logger.debug(f"📊 {pair}: ROI actual {roi}%")
            
            # ✅ NUEVO: Analizar ROI y tomar decisiones
            if operation['status'] == 'open':
                roi_action = await roi_manager.analyze_operation_roi({
                    'symbol': pair,
                    'direction': operation['signal_data']['direction'],
                    'current_roi': roi,
                    'entry_price': operation['actual_entry'],
                    'size': operation['size']
                })
                
                # Guardar recomendación
                operation['recommendation_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'recommendation': roi_action.action,
                    'reason': roi_action.reason,
                    'confidence': roi_action.confidence,
                    'details': roi_action.details
                })
                
                # Notificar acciones importantes
                if roi_action.action in ['REVERTIR', 'CERRAR_PARCIAL', 'CERRAR_TOTAL']:
                    await self._notify_roi_action(operation, roi_action)
                    
        except Exception as e:
            logger.error(f"❌ Error verificando operación {operation.get('id', 'UNKNOWN')}: {e}")
    
    async def _get_current_price(self, pair: str) -> Optional[float]:
        """Obtiene el precio actual del par"""
        try:
            analysis = indicators_calculator.analyze_timeframe(pair, "1")
            return analysis.get('close_price') if analysis else None
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio para {pair}: {e}")
            return None
    
    def _calculate_roi(self, operation: Dict, current_price: float) -> float:
        """Calcula el ROI actual de la operación"""
        try:
            entry = operation['actual_entry']
            direction = operation['signal_data']['direction']
            
            if direction == "LONG":
                roi = ((current_price - entry) / entry) * 100
            else:
                roi = ((entry - current_price) / entry) * 100
                
            return round(roi, 2)
        except Exception as e:
            logger.error(f"Error calculando ROI: {e}")
            return 0
    
    async def _notify_roi_action(self, operation: Dict, roi_action: ROIAction):
        """Notifica acciones basadas en ROI"""
        try:
            signal = operation['signal_data']
            message = f"""
🎯 **ACCIÓN POR ROI - {signal['pair']}**

**Operación Actual:**
- Dirección: {signal['direction']}
- Entry: {operation['actual_entry']}
- ROI Actual: {operation['current_roi']}%
- ROI Máximo: {operation['max_roi']}%

**Recomendación:** {roi_action.action}
**Confianza:** {roi_action.confidence}
**Razón:** {roi_action.reason}

**Detalles:** {roi_action.details}
"""
            await telegram_notifier.send_alert(
                f"Gestión ROI - {signal['pair']}",
                message,
                "warning" if roi_action.action == "REVERTIR" else "info"
            )
        except Exception as e:
            logger.error(f"Error notificando acción ROI: {e}")
    
    def get_open_operations(self) -> List[Dict]:
        """Obtiene operaciones abiertas"""
        return [op for op in self.open_operations.values() if op['status'] == 'open']
    
    def get_operation_stats(self) -> Dict:
        """Obtiene estadísticas de operaciones - CORREGIDO"""
        try:
            open_ops = self.get_open_operations()
            
            if not open_ops:
                return {
                    'total_open': 0,
                    'average_roi': 0,
                    'operations': []
                }
            
            current_rois = [op.get('current_roi', 0) for op in open_ops]
            avg_roi = sum(current_rois) / len(current_rois) if current_rois else 0
            
            return {
                'total_open': len(open_ops),
                'average_roi': round(avg_roi, 1),
                'operations': open_ops  # ✅ CORREGIDO: incluir las operaciones
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas de operaciones: {e}")
            return {
                'total_open': 0,
                'average_roi': 0,
                'operations': []
            }
    
    def close_operation(self, operation_id: str, reason: str = "Manual"):
        """Cierra una operación"""
        if operation_id in self.open_operations:
            self.open_operations[operation_id]['status'] = 'closed'
            self.open_operations[operation_id]['close_time'] = datetime.now()
            self.open_operations[operation_id]['close_reason'] = reason
            logger.info(f"✅ Operación {operation_id} cerrada: {reason}")
    
    def get_operation_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Obtiene operación por símbolo"""
        for operation in self.open_operations.values():
            if (operation['signal_data']['pair'] == symbol and 
                operation['status'] == 'open'):
                return operation
        return None

# Instancia global
operation_tracker = OperationTracker()