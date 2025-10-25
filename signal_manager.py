"""
Gestor inteligente de señales con sistema de confirmación y re-análisis - ACTUALIZADO CON APALANCAMIENTO
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from config import *
from trend_analysis import trend_analyzer
from divergence_detector import divergence_detector
from database import trading_db
from notifier import telegram_notifier
from helpers import calculate_position_size

logger = logging.getLogger(__name__)

@dataclass
class PendingSignal:
    """Señal en estado de espera para re-análisis - ACTUALIZADO CON APALANCAMIENTO"""
    signal_data: Dict
    received_at: datetime
    last_analysis: Dict = None
    analysis_count: int = 0
    status: str = "waiting"
    extended_monitoring: bool = False
    reactivation_attempts: int = 0
    last_reactivation_check: datetime = None
    leverage: int = LEVERAGE  # NUEVO: Apalancamiento

class SignalManager:
    """
    Gestor inteligente ACTUALIZADO CON APALANCAMIENTO
    """
    
    def __init__(self):
        self.pending_signals: Dict[str, PendingSignal] = {}
        self.active_monitoring = False
        self.discarded_signals: Dict[str, PendingSignal] = {}
    
    async def process_new_signal(self, signal_data: Dict) -> bool:
        """
        Procesa una nueva señal recibida - ACTUALIZADO CON APALANCAMIENTO
        """
        try:
            pair = signal_data['pair']
            leverage = signal_data.get('leverage', LEVERAGE)
            logger.info(f"🔍 Procesando nueva señal: {pair} (x{leverage})")
            
            # 1. Análisis técnico inicial
            analysis_result = trend_analyzer.analyze_signal(signal_data, pair)
            
            # 2. Guardar en base de datos
            signal_id = trading_db.save_signal(signal_data, analysis_result)
            if not signal_id:
                logger.error(f"❌ No se pudo guardar señal en BD: {pair}")
                return False
            
            # 3. Obtener resumen para notificaciones
            analysis_summary = trend_analyzer.get_analysis_summary(analysis_result)
            analysis_result['analysis_summary'] = analysis_summary
            
            # 4. Enviar notificación inicial
            await telegram_notifier.send_signal_analysis(analysis_result)
            
            # 5. Enviar información específica de gestión de riesgo
            if analysis_summary.get('position_size'):
                risk_info = {
                    'position_size': analysis_summary.get('position_size'),
                    'dollar_risk': analysis_summary.get('dollar_risk'),
                    'real_risk_percent': analysis_summary.get('real_risk_percent'),
                    'max_position_allowed': analysis_summary.get('position_size', 0) * 2,  # Estimado
                    'risk_reward_ratio': analysis_summary.get('real_risk_percent', 0) / 2  # Estimado
                }
                await telegram_notifier.send_risk_management_info(signal_data, risk_info)
            
            # 6. Determinar acción basada en confirmación
            confirmation_status = analysis_result['confirmation_result']['status']
            
            if confirmation_status in ["CONFIRMADA", "PARCIALMENTE CONFIRMADA"]:
                # Señal confirmada - enviar estado de confirmación
                await telegram_notifier.send_confirmation_status(signal_data, analysis_result['confirmation_result'])
                logger.info(f"✅ Señal {pair} confirmada inicialmente (x{leverage})")
                
            else:
                # Señal no confirmada - agregar a monitoreo pendiente
                pending_signal = PendingSignal(
                    signal_data=signal_data,
                    received_at=datetime.now(),
                    last_analysis=analysis_result,
                    analysis_count=1,
                    leverage=leverage,
                    extended_monitoring=self._should_use_extended_monitoring(analysis_result)
                )
                self.pending_signals[str(signal_id)] = pending_signal
                
                # Enviar estado de espera
                await telegram_notifier.send_confirmation_status(signal_data, analysis_result['confirmation_result'])
                
                if pending_signal.extended_monitoring:
                    logger.info(f"⏸️ Señal {pair} en espera - VIGILANCIA EXTENDIDA ACTIVADA (x{leverage})")
                    await telegram_notifier.send_alert(
                        f"Vigilancia Extendida - {pair}",
                        f"Señal en modo vigilancia extendida por condiciones técnicas favorables.\n"
                        f"Apalancamiento: x{leverage}\n"
                        f"Monitoreo continuará hasta 72 horas.",
                        "info"
                    )
                else:
                    logger.info(f"⏸️ Señal {pair} en espera de confirmación (x{leverage})")
            
            # 6. Iniciar monitoreo si no está activo
            if not self.active_monitoring and self.pending_signals:
                asyncio.create_task(self._start_signal_monitoring())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error procesando señal {signal_data.get('pair', 'UNKNOWN')}: {e}")
            await telegram_notifier.send_error_notification(str(e), "Procesando nueva señal")
            return False
    
    def _should_use_extended_monitoring(self, analysis_result: Dict) -> bool:
        """
        Determina si una señal califica para vigilancia extendida - ACTUALIZADO
        """
        try:
            tech_analysis = analysis_result.get('technical_analysis', {})
            consolidated = tech_analysis.get('consolidated', {})
            signal_data = analysis_result.get('signal_original', {})
            leverage = signal_data.get('leverage', LEVERAGE)
            
            conditions_met = 0
            total_conditions = 4
            
            # 1. Alta volatilidad (ATR multiplier > 1.3)
            atr_multiplier = consolidated.get('max_atr_multiplier', 1.0)
            if atr_multiplier >= EXTENDED_MONITORING_CONDITIONS['min_atr_multiplier']:
                conditions_met += 1
                logger.debug(f"✅ Condición extendida: Alta volatilidad (ATR: {atr_multiplier})")
            
            # 2. Precio dentro del 15% del entry
            current_price = None
            for tf_key, analysis in tech_analysis.items():
                if tf_key.startswith('tf_'):
                    current_price = analysis.get('close_price')
                    break
            
            if current_price and signal_data.get('entry'):
                price_deviation = abs(current_price - signal_data['entry']) / signal_data['entry']
                if price_deviation <= EXTENDED_MONITORING_CONDITIONS['max_price_deviation']:
                    conditions_met += 1
                    logger.debug(f"✅ Condición extendida: Precio cercano (dev: {price_deviation:.2%})")
            
            # 3. RSI en extremos (posible reversión)
            avg_rsi = consolidated.get('avg_rsi', 50)
            if (avg_rsi <= EXTENDED_MONITORING_CONDITIONS['rsi_extreme_threshold'] or 
                avg_rsi >= (100 - EXTENDED_MONITORING_CONDITIONS['rsi_extreme_threshold'])):
                conditions_met += 1
                logger.debug(f"✅ Condición extendida: RSI en extremo ({avg_rsi})")
            
            # 4. Alto apalancamiento (mayor riesgo/oportunidad)
            if leverage >= 15:
                conditions_met += 1
                logger.debug(f"✅ Condición extendida: Alto apalancamiento (x{leverage})")
            
            # Calificar si se cumplen al menos 2 condiciones
            qualifies = conditions_met >= 2
            if qualifies:
                logger.info(f"🎯 Señal califica para vigilancia extendida ({conditions_met}/{total_conditions} condiciones, x{leverage})")
            
            return qualifies
            
        except Exception as e:
            logger.error(f"❌ Error evaluando vigilancia extendida: {e}")
            return False

    async def _should_discard_signal_intelligent(self, signal_id: str, pending_signal: PendingSignal) -> bool:
        """
        Evalúa inteligentemente si descartar una señal (mejorado) - ACTUALIZADO
        """
        try:
            current_time = datetime.now()
            time_elapsed = current_time - pending_signal.received_at
            leverage = pending_signal.leverage
            
            # Timeout base diferenciado (más corto para alto leverage)
            base_timeout_hours = 24 if leverage <= 10 else 18 if leverage <= 20 else 12
            base_timeout = timedelta(hours=base_timeout_hours)
            
            if pending_signal.extended_monitoring:
                base_timeout = timedelta(hours=EXTENDED_MONITORING_TIMEOUT / 3600)
            
            if time_elapsed > base_timeout:
                # Verificar condiciones técnicas antes de descartar
                latest_analysis = await self._get_fresh_analysis(pending_signal)
                
                if latest_analysis and self._is_still_technically_relevant(latest_analysis, pending_signal):
                    logger.info(f"🔍 Señal {signal_id} mantiene relevancia técnica - extendiendo monitoreo (x{leverage})")
                    return False  # Mantener en monitoreo
                
                # Verificar si puede re-activarse posteriormente
                if self._could_reactivate_later(pending_signal, latest_analysis):
                    logger.info(f"💾 Señal {signal_id} movida a cola de re-activación (x{leverage})")
                    self.discarded_signals[signal_id] = pending_signal
                    await self._notify_signal_suspended(signal_id, pending_signal)
                    return True  # Remover de monitoreo activo pero guardar para re-activación
                
                # Descartar definitivamente
                logger.info(f"⏰ Señal {signal_id} descartada por timeout inteligente (x{leverage})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en timeout inteligente para señal {signal_id}: {e}")
            return True  # En caso de error, descartar por seguridad

    async def _get_fresh_analysis(self, pending_signal: PendingSignal) -> Optional[Dict]:
        """
        Obtiene análisis técnico actualizado
        """
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data['pair']
            
            fresh_analysis = trend_analyzer.analyze_signal(signal_data, pair)
            return fresh_analysis
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo análisis fresco: {e}")
            return None

    def _is_still_technically_relevant(self, analysis: Dict, pending_signal: PendingSignal) -> bool:
        """
        Verifica si la señal mantiene relevancia técnica - ACTUALIZADO
        """
        try:
            tech_analysis = analysis.get('technical_analysis', {})
            consolidated = tech_analysis.get('consolidated', {})
            signal_data = pending_signal.signal_data
            leverage = pending_signal.leverage
            
            conditions = []
            
            # 1. Precio aún en rango relevante (±15% del entry)
            current_price = None
            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith('tf_'):
                    current_price = tf_analysis.get('close_price')
                    break
            
            if current_price and signal_data.get('entry'):
                price_deviation = abs(current_price - signal_data['entry']) / signal_data['entry']
                conditions.append(price_deviation <= 0.15)  # Dentro del 15%
            
            # 2. Volatilidad aún alta (más importante con alto leverage)
            atr_multiplier = consolidated.get('max_atr_multiplier', 1.0)
            conditions.append(atr_multiplier > (1.1 if leverage <= 10 else 1.2))
            
            # 3. No hay divergencias fuertes en contra
            divergences = analysis.get('divergences', [])
            strong_contrary_divs = [
                d for d in divergences 
                if d.get('strength') == 'strong' and 
                ((d.get('type') == 'bullish' and signal_data['direction'] == 'SHORT') or
                 (d.get('type') == 'bearish' and signal_data['direction'] == 'LONG'))
            ]
            conditions.append(len(strong_contrary_divs) == 0)
            
            # 4. Confirmación parcial o mejoría
            confirmation = analysis.get('confirmation_result', {})
            current_match = confirmation.get('match_percentage', 0)
            previous_match = pending_signal.last_analysis.get('confirmation_result', {}).get('match_percentage', 0)
            conditions.append(current_match >= 30 or current_match > previous_match)
            
            # Para alto leverage, requerir más condiciones
            min_conditions = 3 if leverage >= 15 else 2
            return sum(conditions) >= min_conditions
            
        except Exception as e:
            logger.error(f"❌ Error evaluando relevancia técnica: {e}")
            return False

    def _could_reactivate_later(self, pending_signal: PendingSignal, latest_analysis: Dict) -> bool:
        """
        Evalúa si la señal podría re-activarse en el futuro - ACTUALIZADO
        """
        try:
            if pending_signal.reactivation_attempts >= 3:  # Máximo 3 intentos
                return False
            
            signal_data = pending_signal.signal_data
            leverage = pending_signal.leverage
            
            # Condiciones para posible re-activación
            conditions = [
                # Precio aún no muy lejano del entry
                self._is_price_in_reactivation_range(signal_data, latest_analysis),
                # Mercado aún volátil (más importante con alto leverage)
                latest_analysis.get('technical_analysis', {}).get('consolidated', {}).get('max_atr_multiplier', 1.0) > (1.0 if leverage <= 10 else 1.1),
                # No ha pasado demasiado tiempo desde última mejora
                (datetime.now() - pending_signal.received_at).days < (7 if leverage <= 10 else 5)
            ]
            
            return any(conditions)
            
        except Exception as e:
            logger.error(f"❌ Error evaluando re-activación futura: {e}")
            return False

    def _is_price_in_reactivation_range(self, signal_data: Dict, analysis: Dict) -> bool:
        """
        Verifica si el precio está en rango para posible re-activación
        """
        try:
            tech_analysis = analysis.get('technical_analysis', {})
            current_price = None
            
            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith('tf_'):
                    current_price = tf_analysis.get('close_price')
                    break
            
            if not current_price or not signal_data.get('entry'):
                return False
            
            price_deviation = abs(current_price - signal_data['entry']) / signal_data['entry']
            return price_deviation <= REACTIVATION_THRESHOLDS['price_proximity']
            
        except Exception as e:
            logger.error(f"❌ Error verificando rango de re-activación: {e}")
            return False

    async def _notify_signal_suspended(self, signal_id: str, pending_signal: PendingSignal):
        """
        Notifica que una señal fue suspendida (no descartada) - ACTUALIZADO
        """
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data['pair']
            leverage = pending_signal.leverage
            
            await telegram_notifier.send_alert(
                f"Señal Suspendida - {pair}",
                f"La señal ha sido movida a modo suspensión.\n"
                f"Apalancamiento: x{leverage}\n"
                f"Será re-evaluada si las condiciones del mercado mejoran.\n"
                f"Entry original: {signal_data['entry']}\n"
                f"Precio actual: {self._get_current_price(pending_signal.last_analysis)}",
                "info"
            )
            
        except Exception as e:
            logger.error(f"❌ Error notificando suspensión de señal {signal_id}: {e}")

    def _get_current_price(self, analysis: Dict) -> float:
        """Obtiene el precio actual del análisis"""
        try:
            tech_analysis = analysis.get('technical_analysis', {})
            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith('tf_'):
                    return tf_analysis.get('close_price', 0)
            return 0
        except:
            return 0

    async def _start_signal_monitoring(self):
        """Inicia el monitoreo periódico de señales en espera - ACTUALIZADO"""
        if self.active_monitoring:
            return
        
        self.active_monitoring = True
        logger.info("🚀 Iniciando monitoreo MEJORADO de señales en espera")
        
        try:
            while self.pending_signals and self.active_monitoring:
                current_time = datetime.now()
                signals_to_remove = []
                
                # 1. Monitoreo de señales activas
                for signal_id, pending_signal in list(self.pending_signals.items()):
                    if await self._should_discard_signal_intelligent(signal_id, pending_signal):
                        signals_to_remove.append(signal_id)
                        continue
                    
                    # 2. Re-activación de señales descartadas (cada 6 horas)
                    if current_time.hour % 6 == 0 and current_time.minute < 5:
                        await self._check_reactivation_candidates()
                    
                    # 3. Re-análisis periódico (ajustado por leverage)
                    volatility_high = self._is_high_volatility(pending_signal.last_analysis)
                    leverage = pending_signal.leverage
                    
                    # Revisar más frecuentemente con alto leverage
                    base_interval = REVIEW_INTERVAL_HIGH_VOL if volatility_high else REVIEW_INTERVAL_NORMAL
                    if leverage >= 15:
                        base_interval = max(300, base_interval // 2)  # Máximo cada 5 minutos
                    
                    interval = base_interval
                    
                    time_since_last_analysis = current_time - pending_signal.received_at
                    if pending_signal.analysis_count > 0:
                        last_analysis_time = datetime.fromisoformat(
                            pending_signal.last_analysis.get('analysis_timestamp', pending_signal.received_at.isoformat())
                        )
                        time_since_last_analysis = current_time - last_analysis_time
                    
                    if time_since_last_analysis.total_seconds() >= interval:
                        await self._reanalyze_signal(signal_id, pending_signal)
                
                # Remover señales procesadas
                for signal_id in signals_to_remove:
                    self.pending_signals.pop(signal_id, None)
                
                # Esperar antes del próximo ciclo
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"❌ Error en monitoreo MEJORADO de señales: {e}")
            self.active_monitoring = False

    def _is_high_volatility(self, analysis: Dict) -> bool:
        """Determina si hay alta volatilidad"""
        try:
            tech_analysis = analysis.get('technical_analysis', {})
            consolidated = tech_analysis.get('consolidated', {})
            atr_multiplier = consolidated.get('max_atr_multiplier', 1.0)
            return atr_multiplier > 1.3
        except:
            return False

    async def _reanalyze_signal(self, signal_id: str, pending_signal: PendingSignal):
        """Re-analiza una señal pendiente"""
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data['pair']
            leverage = pending_signal.leverage
            
            logger.info(f"🔍 Re-analizando señal: {pair} (x{leverage})")
            
            # Obtener análisis actualizado
            new_analysis = await self._get_fresh_analysis(pending_signal)
            if not new_analysis:
                return
            
            # Actualizar análisis
            pending_signal.last_analysis = new_analysis
            pending_signal.analysis_count += 1
            
            # Verificar si ahora está confirmada
            confirmation_status = new_analysis['confirmation_result']['status']
            if confirmation_status in ["CONFIRMADA", "PARCIALMENTE CONFIRMADA"]:
                logger.info(f"✅ Señal {pair} ahora confirmada después de re-análisis")
                
                # Enviar notificación de confirmación tardía
                await telegram_notifier.send_confirmation_status(signal_data, new_analysis['confirmation_result'])
                await telegram_notifier.send_signal_analysis(new_analysis)
                
                # Remover de pendientes
                self.pending_signals.pop(signal_id, None)
                
        except Exception as e:
            logger.error(f"❌ Error re-analizando señal {signal_id}: {e}")

    async def _check_reactivation_candidates(self):
        """Verifica señales descartadas para posible re-activación"""
        try:
            for signal_id, discarded_signal in list(self.discarded_signals.items()):
                if await self._should_reactivate_signal(discarded_signal):
                    await self._reactivate_signal(signal_id, discarded_signal)
        except Exception as e:
            logger.error(f"❌ Error verificando re-activación: {e}")

    async def _should_reactivate_signal(self, discarded_signal: PendingSignal) -> bool:
        """Determina si una señal descartada debe re-activarse"""
        # Lógica de re-activación (simplificada)
        return discarded_signal.reactivation_attempts < 2

    async def _reactivate_signal(self, signal_id: str, discarded_signal: PendingSignal):
        """Re-activa una señal previamente descartada"""
        try:
            discarded_signal.reactivation_attempts += 1
            discarded_signal.last_reactivation_check = datetime.now()
            
            # Mover de vuelta a pendientes
            self.pending_signals[signal_id] = discarded_signal
            self.discarded_signals.pop(signal_id)
            
            logger.info(f"🔄 Señal {discarded_signal.signal_data['pair']} re-activada")
            
        except Exception as e:
            logger.error(f"❌ Error re-activando señal {signal_id}: {e}")

    def get_pending_signals_count(self) -> int:
        """Retorna el número de señales pendientes"""
        return len(self.pending_signals)

# Instancia global
signal_manager = SignalManager()