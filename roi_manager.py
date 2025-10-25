"""
Gestor de ROI para operaciones según el prompt original
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from config import *
from indicators import indicators_calculator
from notifier import telegram_notifier

logger = logging.getLogger(__name__)

@dataclass
class ROIAction:
    """Acción basada en ROI"""
    action: str  # MANTENER, CERRAR_PARCIAL, CERRAR_TOTAL, REVERTIR
    reason: str
    details: Dict
    confidence: str

class ROIManager:
    """Gestiona operaciones basado en ROI según prompt original"""
    
    def __init__(self):
        self.indicators = indicators_calculator
    
    async def analyze_operation_roi(self, operation_data: Dict) -> ROIAction:
        """
        Analiza una operación abierta y decide acción basada en ROI
        """
        try:
            current_roi = operation_data.get('current_roi', 0)
            symbol = operation_data.get('symbol', 'UNKNOWN')
            direction = operation_data.get('direction', 'LONG')
            
            logger.info(f"📊 Analizando ROI para {symbol}: {current_roi}%")
            
            # 1. ROI -30%: Re-analizar temporalidades bajas para posible reversión
            if current_roi <= -30:  # ROI_REVERSION_THRESHOLD
                return await self._handle_negative_roi(operation_data)
            
            # 2. ROI +60%: Colocar Stop Loss dinámico en +5%
            elif current_roi >= 60:  # ROI_DYNAMIC_STOP_THRESHOLD
                return self._handle_high_positive_roi(operation_data)
            
            # 3. ROI +100%: Cerrar 70% y mantener 30%
            elif current_roi >= 100:  # ROI_TAKE_PROFIT_THRESHOLD
                return self._handle_take_profit_roi(operation_data)
            
            # 4. ROI normal: Mantener
            else:
                return ROIAction(
                    action="MANTENER",
                    reason=f"ROI dentro de rangos normales ({current_roi}%)",
                    details={'current_roi': current_roi},
                    confidence="ALTA"
                )
                
        except Exception as e:
            logger.error(f"❌ Error analizando ROI: {e}")
            return ROIAction(
                action="MANTENER",
                reason=f"Error en análisis: {str(e)}",
                details={'error': str(e)},
                confidence="BAJA"
            )
    
    async def _handle_negative_roi(self, operation_data: Dict) -> ROIAction:
        """Maneja ROI negativo (-30%): re-analiza para posible reversión"""
        symbol = operation_data['symbol']
        current_roi = operation_data['current_roi']
        
        logger.warning(f"⚠️ ROI crítico detectado: {symbol} @ {current_roi}%")
        
        # Re-analizar temporalidades bajas (1m, 5m, 15m)
        analysis_1m = self.indicators.analyze_timeframe(symbol, "1")
        analysis_5m = self.indicators.analyze_timeframe(symbol, "5") 
        analysis_15m = self.indicators.analyze_timeframe(symbol, "15")
        
        # Contar confirmaciones de reversión
        reversal_signals = 0
        total_timeframes = 0
        
        for tf_analysis in [analysis_1m, analysis_5m, analysis_15m]:
            if tf_analysis:
                total_timeframes += 1
                current_trend = tf_analysis.get('ema_trend', 'NEUTRO')
                original_direction = operation_data.get('direction', 'LONG')
                
                # Verificar si hay señal de reversión
                if (original_direction == 'LONG' and current_trend == 'BAJISTA') or \
                   (original_direction == 'SHORT' and current_trend == 'ALCISTA'):
                    reversal_signals += 1
        
        # Decidir acción basada en señales de reversión
        if total_timeframes > 0:
            reversal_ratio = reversal_signals / total_timeframes
            
            if reversal_ratio >= 0.67:  # 2/3 timeframes confirman reversión
                return ROIAction(
                    action="REVERTIR",
                    reason=f"Fuerte señal de reversión en {reversal_signals}/{total_timeframes} timeframes. ROI: {current_roi}%",
                    details={
                        'reversal_signals': reversal_signals,
                        'total_timeframes': total_timeframes,
                        'reversal_ratio': reversal_ratio,
                        'current_roi': current_roi
                    },
                    confidence="ALTA"
                )
            
            elif reversal_ratio >= 0.34:  # 1/3 timeframes sugieren reversión
                return ROIAction(
                    action="CERRAR_PARCIAL",
                    reason=f"Señales moderadas de reversión ({reversal_signals}/{total_timeframes}). ROI: {current_roi}%",
                    details={
                        'reversal_signals': reversal_signals,
                        'total_timeframes': total_timeframes,
                        'current_roi': current_roi
                    },
                    confidence="MEDIA"
                )
        
        # Si no hay señales fuertes de reversión, mantener con alerta
        return ROIAction(
            action="MANTENER",
            reason=f"ROI negativo ({current_roi}%) pero sin señales fuertes de reversión ({reversal_signals}/{total_timeframes} timeframes)",
            details={
                'reversal_signals': reversal_signals,
                'total_timeframes': total_timeframes,
                'current_roi': current_roi
            },
            confidence="MEDIA"
        )
    
    def _handle_high_positive_roi(self, operation_data: Dict) -> ROIAction:
        """Maneja ROI alto (+60%): SL dinámico en +5%"""
        current_roi = operation_data['current_roi']
        entry_price = operation_data.get('entry_price', 0)
        
        # Calcular precio para SL dinámico (+5% desde entry)
        if operation_data['direction'] == 'LONG':
            dynamic_stop = entry_price * 1.05
        else:
            dynamic_stop = entry_price * 0.95
        
        return ROIAction(
            action="MANTENER",
            reason=f"ROI alto ({current_roi}%). Stop Loss dinámico activado @ {dynamic_stop:.6f}",
            details={
                'dynamic_stop': dynamic_stop,
                'current_roi': current_roi,
                'stop_type': 'DYNAMIC'
            },
            confidence="ALTA"
        )
    
    def _handle_take_profit_roi(self, operation_data: Dict) -> ROIAction:
        """Maneja ROI muy alto (+100%): Cerrar 70% de la posición"""
        current_roi = operation_data['current_roi']
        
        return ROIAction(
            action="CERRAR_PARCIAL",
            reason=f"ROI objetivo alcanzado ({current_roi}%). Cerrar 70% de la posición",
            details={
                'close_percentage': 70,
                'current_roi': current_roi,
                'keep_percentage': 30
            },
            confidence="ALTA"
        )

# Instancia global
roi_manager = ROIManager()