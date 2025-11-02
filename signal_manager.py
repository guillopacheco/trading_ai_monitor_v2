# signal_manager.py - VERSIÓN CORREGIDA
"""
Gestor inteligente de señales con sistema de confirmación y re-análisis - CON HEALTH MONITOR
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from config import *
from divergence_detector import divergence_detector
from database import trading_db
from notifier import telegram_notifier
from helpers import calculate_position_size

# ✅ NUEVO IMPORT
from health_monitor import health_monitor
from trend_analysis import trend_analyzer

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
    Gestor inteligente ACTUALIZADO CON HEALTH MONITOR
    """

    def __init__(self):
        self.pending_signals: Dict[str, PendingSignal] = {}
        self.active_monitoring = False
        self.discarded_signals: Dict[str, PendingSignal] = {}
        self.signals_processed = 0
        self.successful_analyses = 0
        # ✅ NUEVO: Inicializar dependencias
        from trend_analysis import trend_analyzer as _trend_analyzer
        from database import trading_db as _trading_db

        self.trend_analyzer = _trend_analyzer
        self.db = _trading_db

    async def process_new_signal(self, signal_data: Dict) -> bool:
        """Procesa una nueva señal - CON HEALTH MONITOR"""
        try:
            symbol = signal_data.get("pair", "UNKNOWN")
            logger.info(
                f"🔍 Procesando nueva señal: {symbol} (x{signal_data.get('leverage', 20)})"
            )

            # ✅ NUEVO: Registrar inicio de procesamiento
            health_monitor.record_signal_processed(signal_data)
            self.signals_processed += 1

            # 1. Análisis técnico COMPLETO
            analysis_result = await self.perform_technical_analysis(symbol, signal_data)
            if not analysis_result:
                logger.error(f"❌ Error en análisis técnico para {symbol}")
                health_monitor.record_error(f"Error en análisis técnico para {symbol}", "Signal Manager")
                return False

            # ✅ CORRECCIÓN: Extraer confirmation_result del análisis completo
            confirmation_result = analysis_result.get('confirmation_result', {})
            
            # ✅ VERIFICAR que confirmation_result tenga los campos requeridos
            if not confirmation_result or "match_percentage" not in confirmation_result:
                logger.error(f"❌ Resultado de confirmación inválido para {symbol}")
                health_monitor.record_error(f"Resultado de confirmación inválido para {symbol}", "Signal Manager")
                # Crear estructura por defecto
                confirmation_result = {
                    "status": "ERROR",
                    "match_percentage": 0.0,
                    "confidence": "BAJA",
                }

            # ✅ DEBUG: Loggear el match_percentage antes de guardar
            match_percentage = confirmation_result.get('match_percentage', 0.0)
            logger.info(f"📊 ANTES DE GUARDAR BD - Match: {match_percentage}%")

            # 3. Guardar en base de datos
            signal_id = self.db.save_signal(
                signal_data,
                {
                    "technical_analysis": analysis_result.get('technical_analysis', {}),
                    "confirmation_result": confirmation_result,
                    "analysis_summary": self._create_analysis_summary(
                        analysis_result, confirmation_result
                    ),
                },
            )

            if not signal_id:
                logger.error(f"❌ Error guardando señal {symbol} en BD")
                health_monitor.record_error(f"Error guardando señal {symbol} en BD", "Signal Manager")
                return False

            # 4. Tomar decisión de trading
            trade_success = await self.make_trading_decision(
                signal_id, signal_data, confirmation_result
            )

            # ✅ NUEVO: Registrar resultado del trade
            if trade_success:
                health_monitor.record_successful_trade()
                self.successful_analyses += 1
            else:
                health_monitor.record_error(f"Trade no ejecutado para {symbol}", "Signal Manager")

            logger.info(f"✅ Señal {symbol} procesada correctamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error procesando señal {symbol}: {e}")
            health_monitor.record_error(str(e), f"Procesamiento señal {symbol}")
            return False

    async def perform_technical_analysis(self, symbol: str, signal_data: Dict) -> Optional[Dict]:
        """Realiza análisis técnico COMPLETO - CORREGIDO CON ASYNC"""
        try:
            logger.info(f"🔍 Iniciando análisis técnico para {symbol}")

            # ✅ CORRECCIÓN: Usar analyze_signal que ahora es async
            analysis_result = await self.trend_analyzer.analyze_signal(signal_data, symbol)  # ✅ AGREGAR await

            if analysis_result and analysis_result.get("confirmation_result"):
                logger.info(f"✅ Análisis técnico completado para {symbol}")
                
                # ✅ DEBUG: Loggear el match_percentage del análisis
                match_percentage = analysis_result.get('confirmation_result', {}).get('match_percentage', 0)
                logger.info(f"📊 ANÁLISIS COMPLETO - Match: {match_percentage}%")
                
                return analysis_result
            else:
                logger.warning(f"⚠️ Análisis técnico retornó vacío para {symbol}")
                return None

        except Exception as e:
            logger.error(f"❌ Error en análisis técnico para {symbol}: {e}")
            health_monitor.record_error(str(e), f"Análisis técnico {symbol}")
            return None

    async def _execute_technical_analysis(self, symbol: str, signal_data: Dict) -> Optional[Dict]:
        """Ejecuta el análisis técnico real"""
        # Aquí va tu lógica existente de análisis técnico
        # Por ahora retornamos un dict vacío como placeholder
        return {
            "technical_analysis": {},
            "confirmation_result": {"status": "PENDING", "match_percentage": 0.0}
        }

    def _should_use_extended_monitoring(self, analysis_result: Dict) -> bool:
        """
        Determina si una señal califica para vigilancia extendida - ACTUALIZADO
        """
        try:
            tech_analysis = analysis_result.get("technical_analysis", {})
            consolidated = tech_analysis.get("consolidated", {})
            signal_data = analysis_result.get("signal_original", {})
            leverage = signal_data.get("leverage", LEVERAGE)

            conditions_met = 0
            total_conditions = 4

            # 1. Alta volatilidad (ATR multiplier > 1.3)
            atr_multiplier = consolidated.get("max_atr_multiplier", 1.0)
            if atr_multiplier >= EXTENDED_MONITORING_CONDITIONS["min_atr_multiplier"]:
                conditions_met += 1
                logger.debug(
                    f"✅ Condición extendida: Alta volatilidad (ATR: {atr_multiplier})"
                )

            # 2. Precio dentro del 15% del entry
            current_price = None
            for tf_key, analysis in tech_analysis.items():
                if tf_key.startswith("tf_"):
                    current_price = analysis.get("close_price")
                    break

            if current_price and signal_data.get("entry"):
                price_deviation = (
                    abs(current_price - signal_data["entry"]) / signal_data["entry"]
                )
                if (
                    price_deviation
                    <= EXTENDED_MONITORING_CONDITIONS["max_price_deviation"]
                ):
                    conditions_met += 1
                    logger.debug(
                        f"✅ Condición extendida: Precio cercano (dev: {price_deviation:.2%})"
                    )

            # 3. RSI en extremos (posible reversión)
            avg_rsi = consolidated.get("avg_rsi", 50)
            if avg_rsi <= EXTENDED_MONITORING_CONDITIONS[
                "rsi_extreme_threshold"
            ] or avg_rsi >= (
                100 - EXTENDED_MONITORING_CONDITIONS["rsi_extreme_threshold"]
            ):
                conditions_met += 1
                logger.debug(f"✅ Condición extendida: RSI en extremo ({avg_rsi})")

            # 4. Alto apalancamiento (mayor riesgo/oportunidad)
            if leverage >= 15:
                conditions_met += 1
                logger.debug(
                    f"✅ Condición extendida: Alto apalancamiento (x{leverage})"
                )

            # Calificar si se cumplen al menos 2 condiciones
            qualifies = conditions_met >= 2
            if qualifies:
                logger.info(
                    f"🎯 Señal califica para vigilancia extendida ({conditions_met}/{total_conditions} condiciones, x{leverage})"
                )

            return qualifies

        except Exception as e:
            logger.error(f"❌ Error evaluando vigilancia extendida: {e}")
            health_monitor.record_error(str(e), "Evaluación vigilancia extendida")
            return False

    async def _should_discard_signal_intelligent(
        self, signal_id: str, pending_signal: PendingSignal
    ) -> bool:
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

                if latest_analysis and self._is_still_technically_relevant(
                    latest_analysis, pending_signal
                ):
                    logger.info(
                        f"🔍 Señal {signal_id} mantiene relevancia técnica - extendiendo monitoreo (x{leverage})"
                    )
                    return False  # Mantener en monitoreo

                # Verificar si puede re-activarse posteriormente
                if self._could_reactivate_later(pending_signal, latest_analysis):
                    logger.info(
                        f"💾 Señal {signal_id} movida a cola de re-activación (x{leverage})"
                    )
                    self.discarded_signals[signal_id] = pending_signal
                    await self._notify_signal_suspended(signal_id, pending_signal)
                    return True  # Remover de monitoreo activo pero guardar para re-activación

                # Descartar definitivamente
                logger.info(
                    f"⏰ Señal {signal_id} descartada por timeout inteligente (x{leverage})"
                )
                health_monitor.record_error(f"Señal {signal_id} descartada por timeout", "Signal Manager")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error en timeout inteligente para señal {signal_id}: {e}")
            health_monitor.record_error(str(e), f"Timeout inteligente señal {signal_id}")
            return True  # En caso de error, descartar por seguridad

    async def _get_fresh_analysis(
        self, pending_signal: PendingSignal
    ) -> Optional[Dict]:
        """
        Obtiene análisis técnico actualizado - CON HEALTH MONITOR
        """
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data["pair"]

            # ✅ NUEVO: Registrar re-análisis
            health_monitor.record_bybit_api_call(f"reanalysis_{pair}")

            fresh_analysis = trend_analyzer.analyze_signal(signal_data, pair)
            return fresh_analysis

        except Exception as e:
            logger.error(f"❌ Error obteniendo análisis fresco: {e}")
            health_monitor.record_error(str(e), f"Análisis fresco {pair}")
            return None

    def _is_still_technically_relevant(
        self, analysis: Dict, pending_signal: PendingSignal
    ) -> bool:
        """
        Verifica si la señal mantiene relevancia técnica - ACTUALIZADO
        """
        try:
            tech_analysis = analysis.get("technical_analysis", {})
            consolidated = tech_analysis.get("consolidated", {})
            signal_data = pending_signal.signal_data
            leverage = pending_signal.leverage

            conditions = []

            # 1. Precio aún en rango relevante (±15% del entry)
            current_price = None
            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith("tf_"):
                    current_price = tf_analysis.get("close_price")
                    break

            if current_price and signal_data.get("entry"):
                price_deviation = (
                    abs(current_price - signal_data["entry"]) / signal_data["entry"]
                )
                conditions.append(price_deviation <= 0.15)  # Dentro del 15%

            # 2. Volatilidad aún alta (más importante con alto leverage)
            atr_multiplier = consolidated.get("max_atr_multiplier", 1.0)
            conditions.append(atr_multiplier > (1.1 if leverage <= 10 else 1.2))

            # 3. No hay divergencias fuertes en contra
            divergences = analysis.get("divergences", [])
            strong_contrary_divs = [
                d
                for d in divergences
                if d.get("strength") == "strong"
                and (
                    (d.get("type") == "bullish" and signal_data["direction"] == "SHORT")
                    or (
                        d.get("type") == "bearish"
                        and signal_data["direction"] == "LONG"
                    )
                )
            ]
            conditions.append(len(strong_contrary_divs) == 0)

            # 4. Confirmación parcial o mejoría
            confirmation = analysis.get("confirmation_result", {})
            current_match = confirmation.get("match_percentage", 0)
            previous_match = pending_signal.last_analysis.get(
                "confirmation_result", {}
            ).get("match_percentage", 0) if pending_signal.last_analysis else 0
            conditions.append(current_match >= 30 or current_match > previous_match)

            # Para alto leverage, requerir más condiciones
            min_conditions = 3 if leverage >= 15 else 2
            return sum(conditions) >= min_conditions

        except Exception as e:
            logger.error(f"❌ Error evaluando relevancia técnica: {e}")
            health_monitor.record_error(str(e), "Evaluación relevancia técnica")
            return False

    def _could_reactivate_later(
        self, pending_signal: PendingSignal, latest_analysis: Dict
    ) -> bool:
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
                latest_analysis.get("technical_analysis", {})
                .get("consolidated", {})
                .get("max_atr_multiplier", 1.0)
                > (1.0 if leverage <= 10 else 1.1),
                # No ha pasado demasiado tiempo desde última mejora
                (datetime.now() - pending_signal.received_at).days
                < (7 if leverage <= 10 else 5),
            ]

            return any(conditions)

        except Exception as e:
            logger.error(f"❌ Error evaluando re-activación futura: {e}")
            health_monitor.record_error(str(e), "Evaluación re-activación")
            return False

    def _is_price_in_reactivation_range(
        self, signal_data: Dict, analysis: Dict
    ) -> bool:
        """
        Verifica si el precio está en rango para posible re-activación
        """
        try:
            tech_analysis = analysis.get("technical_analysis", {})
            current_price = None

            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith("tf_"):
                    current_price = tf_analysis.get("close_price")
                    break

            if not current_price or not signal_data.get("entry"):
                return False

            price_deviation = (
                abs(current_price - signal_data["entry"]) / signal_data["entry"]
            )
            return price_deviation <= REACTIVATION_THRESHOLDS["price_proximity"]

        except Exception as e:
            logger.error(f"❌ Error verificando rango de re-activación: {e}")
            return False

    async def _notify_signal_suspended(
        self, signal_id: str, pending_signal: PendingSignal
    ):
        """
        Notifica que una señal fue suspendida (no descartada) - ACTUALIZADO
        """
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data["pair"]
            leverage = pending_signal.leverage

            await telegram_notifier.send_alert(
                f"Señal Suspendida - {pair}",
                f"La señal ha sido movida a modo suspensión.\n"
                f"Apalancamiento: x{leverage}\n"
                f"Será re-evaluada si las condiciones del mercado mejoran.\n"
                f"Entry original: {signal_data['entry']}\n"
                f"Precio actual: {self._get_current_price(pending_signal.last_analysis)}",
                "info",
            )

        except Exception as e:
            logger.error(f"❌ Error notificando suspensión de señal {signal_id}: {e}")
            health_monitor.record_error(str(e), f"Notificación suspensión {signal_id}")

    def _get_current_price(self, analysis: Dict) -> float:
        """Obtiene el precio actual del análisis"""
        try:
            tech_analysis = analysis.get("technical_analysis", {})
            for tf_key, tf_analysis in tech_analysis.items():
                if tf_key.startswith("tf_"):
                    return tf_analysis.get("close_price", 0)
            return 0
        except:
            return 0

    async def _start_signal_monitoring(self):
        """Inicia el monitoreo periódico de señales en espera - CON HEALTH MONITOR"""
        if self.active_monitoring:
            return

        self.active_monitoring = True
        logger.info("🚀 Iniciando monitoreo MEJORADO de señales en espera")

        try:
            while self.pending_signals and self.active_monitoring:
                current_time = datetime.now()
                signals_to_remove = []

                # ✅ NUEVO: Registrar actividad del monitor
                health_monitor.record_telegram_bot_activity()

                # 1. Monitoreo de señales activas
                for signal_id, pending_signal in list(self.pending_signals.items()):
                    if await self._should_discard_signal_intelligent(
                        signal_id, pending_signal
                    ):
                        signals_to_remove.append(signal_id)
                        continue

                    # 2. Re-activación de señales descartadas (cada 6 horas)
                    if current_time.hour % 6 == 0 and current_time.minute < 5:
                        await self._check_reactivation_candidates()

                    # 3. Re-análisis periódico (ajustado por leverage)
                    volatility_high = self._is_high_volatility(
                        pending_signal.last_analysis
                    )
                    leverage = pending_signal.leverage

                    # Revisar más frecuentemente con alto leverage
                    base_interval = (
                        REVIEW_INTERVAL_HIGH_VOL
                        if volatility_high
                        else REVIEW_INTERVAL_NORMAL
                    )
                    if leverage >= 15:
                        base_interval = max(
                            300, base_interval // 2
                        )  # Máximo cada 5 minutos

                    interval = base_interval

                    time_since_last_analysis = current_time - pending_signal.received_at
                    if pending_signal.analysis_count > 0:
                        last_analysis_time = datetime.fromisoformat(
                            pending_signal.last_analysis.get(
                                "analysis_timestamp",
                                pending_signal.received_at.isoformat(),
                            )
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
            health_monitor.record_error(str(e), "Monitoreo de señales")
            self.active_monitoring = False

    def _is_high_volatility(self, analysis: Dict) -> bool:
        """Determina si hay alta volatilidad"""
        try:
            tech_analysis = analysis.get("technical_analysis", {})
            consolidated = tech_analysis.get("consolidated", {})
            atr_multiplier = consolidated.get("max_atr_multiplier", 1.0)
            return atr_multiplier > 1.3
        except:
            return False

    async def _reanalyze_signal(self, signal_id: str, pending_signal: PendingSignal):
        """Re-analiza una señal pendiente - CON HEALTH MONITOR"""
        try:
            signal_data = pending_signal.signal_data
            pair = signal_data["pair"]
            leverage = pending_signal.leverage

            logger.info(f"🔍 Re-analizando señal: {pair} (x{leverage})")

            # ✅ NUEVO: Registrar re-análisis
            health_monitor.record_bybit_api_call(f"reanalysis_{pair}")

            # Obtener análisis actualizado
            new_analysis = await self._get_fresh_analysis(pending_signal)
            if not new_analysis:
                return

            # Actualizar análisis
            pending_signal.last_analysis = new_analysis
            pending_signal.analysis_count += 1

            # Verificar si ahora está confirmada
            confirmation_status = new_analysis["confirmation_result"]["status"]
            if confirmation_status in ["CONFIRMADA", "PARCIALMENTE CONFIRMADA"]:
                logger.info(f"✅ Señal {pair} ahora confirmada después de re-análisis")

                # Enviar notificación de confirmación tardía
                await telegram_notifier.send_confirmation_status(
                    signal_data, new_analysis["confirmation_result"]
                )
                await telegram_notifier.send_signal_analysis(new_analysis)

                # ✅ NUEVO: Registrar confirmación exitosa
                health_monitor.record_successful_trade()

                # Remover de pendientes
                self.pending_signals.pop(signal_id, None)

        except Exception as e:
            logger.error(f"❌ Error re-analizando señal {signal_id}: {e}")
            health_monitor.record_error(str(e), f"Re-análisis señal {signal_id}")

    async def _check_reactivation_candidates(self):
        """Verifica señales descartadas para posible re-activación"""
        try:
            for signal_id, discarded_signal in list(self.discarded_signals.items()):
                if await self._should_reactivate_signal(discarded_signal):
                    await self._reactivate_signal(signal_id, discarded_signal)
        except Exception as e:
            logger.error(f"❌ Error verificando re-activación: {e}")
            health_monitor.record_error(str(e), "Verificación re-activación")

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

            # ✅ NUEVO: Registrar re-activación
            health_monitor.record_telegram_bot_activity()

        except Exception as e:
            logger.error(f"❌ Error re-activando señal {signal_id}: {e}")
            health_monitor.record_error(str(e), f"Re-activación señal {signal_id}")

    def get_pending_signals_count(self) -> int:
        """Retorna el número de señales pendientes"""
        return len(self.pending_signals)

    def get_signal_manager_stats(self) -> Dict:
        """✅ NUEVO: Obtiene estadísticas del signal manager"""
        return {
            'pending_signals': len(self.pending_signals),
            'discarded_signals': len(self.discarded_signals),
            'signals_processed': self.signals_processed,
            'successful_analyses': self.successful_analyses,
            'success_rate': (self.successful_analyses / self.signals_processed * 100) if self.signals_processed > 0 else 0,
        }

    def _create_analysis_summary(self, analysis_result: Dict, confirmation_result: Dict) -> Dict:
        """Crea resumen del análisis - MÉTODO FALTANTE"""
        try:
            if not analysis_result:
                return {"error": "No analysis result"}

            # Obtener recomendación si existe
            recommendation = analysis_result.get("recommendation", {})

            # Manejar tanto si es objeto como dict
            if hasattr(recommendation, 'action'):
                # Es un objeto TradingRecommendation
                action = recommendation.action
                confidence = recommendation.confidence
                reason = recommendation.reason
                suggested_entry = recommendation.suggested_entry
                stop_loss = recommendation.stop_loss
                position_size = recommendation.position_size
                leverage = recommendation.leverage
            else:
                # Es un dict
                action = recommendation.get('action', 'ESPERAR')
                confidence = recommendation.get('confidence', 'BAJA')
                reason = recommendation.get('reason', 'Sin análisis')
                suggested_entry = recommendation.get('suggested_entry', 0)
                stop_loss = recommendation.get('stop_loss', 0)
                position_size = recommendation.get('position_size', 0)
                leverage = recommendation.get('leverage', 20)

            # Obtener análisis técnico
            tech_analysis = analysis_result.get("technical_analysis", {})
            consolidated = tech_analysis.get("consolidated", {})

            return {
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "suggested_entry": suggested_entry,
                "stop_loss": stop_loss,
                "position_size": position_size,
                "leverage": leverage,
                "predominant_trend": consolidated.get("predominant_trend", "NEUTRO"),
                "avg_rsi": consolidated.get("avg_rsi", 50),
                "match_percentage": confirmation_result.get("match_percentage", 0),  # ✅ CORREGIDO
                "confirmation_status": confirmation_result.get("status", "NO CONFIRMADA"),
                "analysis_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Error creando resumen de análisis: {e}")
            return {
                "error": str(e),
                "action": "ESPERAR",
                "confidence": "BAJA",
                "reason": "Error en análisis"
            }

    async def make_trading_decision(self, signal_id: str, signal_data: Dict, confirmation_result: Dict) -> bool:
        """Toma decisión de trading - MÉTODO FALTANTE"""
        try:
            symbol = signal_data["pair"]
            logger.info(f"🤔 Tomando decisión para {symbol}...")

            # Obtener análisis completo
            analysis_result = await self.perform_technical_analysis(symbol, signal_data)
            if not analysis_result:
                logger.error(f"❌ No se pudo obtener análisis para {symbol}")
                return False

            # Obtener recomendación
            recommendation = analysis_result.get("recommendation")
            if not recommendation:
                logger.warning(f"⚠️ No hay recomendación para {symbol}")
                return False

            # Determinar acción basada en recomendación
            if hasattr(recommendation, 'action'):
                action = recommendation.action
                reason = recommendation.reason
                match_percentage = getattr(recommendation, 'match_percentage', 0)
            else:
                action = recommendation.get('action', 'ESPERAR')
                reason = recommendation.get('reason', 'Sin razón')
                match_percentage = recommendation.get('match_percentage', 0)

            # ✅ NUEVO: ENVIAR NOTIFICACIÓN CONCISA
            await self._send_concise_notification(signal_data, action, match_percentage, reason)

            if action == "ENTRAR":
                logger.info(f"🎯 DECISIÓN: ENTRAR en {symbol} - {reason}")

                # Enviar notificación
                await telegram_notifier.send_signal_analysis(analysis_result)

                # Actualizar BD
                self.db.update_signal_status(signal_id, "confirmed", {
                    "analysis_result": analysis_result,
                    "confirmed_at": datetime.now().isoformat(),
                    "decision": "ENTRAR"
                })

                return True

            elif action == "ESPERAR":
                logger.info(f"⏸️ DECISIÓN: ESPERAR para {symbol} - {reason}")

                # Guardar como pendiente
                self.db.update_signal_status(signal_id, "pending", {
                    "analysis_result": analysis_result,
                    "pending_reason": reason
                })

                return False

            else:
                logger.info(f"❌ DECISIÓN: RECHAZAR {symbol} - {reason}")
                self.db.update_signal_status(signal_id, "rejected", {
                    "analysis_result": analysis_result,
                    "rejection_reason": reason
                })
                return False

        except Exception as e:
            logger.error(f"❌ Error en decisión de trading para {signal_id}: {e}")
            return False
        
    async def _send_concise_notification(self, signal_data: Dict, decision: str, match_percentage: float, reason: str):
        """Envía notificación MUY concisa a Telegram del resultado del análisis"""
        try:
            symbol = signal_data['pair']
            direction = signal_data['direction']
            
            # Determinar emoji y texto basado en la decisión
            if decision == "ENTRAR":
                emoji = "✅"
                action_text = "CONFIRMADA"
            elif decision == "ESPERAR":
                emoji = "⚠️" 
                action_text = "EN ESPERA"
            else:  # RECHAZAR
                emoji = "❌"
                action_text = "RECHAZADA"
            
            # Mensaje super conciso
            message = f"{emoji} {symbol} {direction} - {action_text} ({match_percentage:.1f}%)"
            
            # Enviar como alerta simple
            await telegram_notifier.send_alert(
                "Análisis Completado",
                message,
                "success" if decision == "ENTRAR" else "warning" if decision == "ESPERAR" else "error"
            )
            
            logger.info(f"📱 Notificación concisa enviada: {message}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación concisa: {e}")


# Instancia global
signal_manager = SignalManager()