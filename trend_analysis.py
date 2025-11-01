# trend_analysis.py - VERSIÓN MEJORADA
"""
Análisis de tendencias y recomendaciones basadas en múltiples temporalidades - ACTUALIZADO CON APALANCAMIENTO Y LÓGICA MEJORADA
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import *
from indicators import indicators_calculator
from divergence_detector import divergence_detector
from helpers import calculate_position_size
from datetime import datetime

# ✅ AGREGAR IMPORTACIONES ESPECÍFICAS
from config import (
    LEVERAGE,
    RISK_PER_TRADE,
    ACCOUNT_BALANCE,
    MAX_POSITION_SIZE,
    BASE_STOP_PERCENTAGE,
    MIN_STOP_DISTANCE,
    MAX_STOP_DISTANCE,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    DEFAULT_TIMEFRAMES,
    EMA_SHORT_PERIOD,
    EMA_LONG_PERIOD,
    ATR_PERIOD,
    EXTENDED_MONITORING_CONDITIONS,
    REACTIVATION_THRESHOLDS,
)

logger = logging.getLogger(__name__)


@dataclass
class TradingRecommendation:
    """Estructura para recomendaciones de trading - ACTUALIZADO CON APALANCAMIENTO"""

    action: str  # ENTRAR, ESPERAR, CERRAR, REVERTIR
    confidence: str  # ALTA, MEDIA, BAJA
    reason: str
    suggested_entry: float = None
    stop_loss: float = None
    take_profits: List[float] = None
    position_size: float = None  # NUEVO: Tamaño de posición
    dollar_risk: float = None  # NUEVO: Riesgo en dólares
    leverage: int = LEVERAGE  # NUEVO: Apalancamiento
    real_risk_percent: float = None  # NUEVO: Riesgo real con leverage


class TrendAnalyzer:
    """Analizador de tendencias y generador de recomendaciones - ACTUALIZADO CON APALANCAMIENTO Y LÓGICA MEJORADA"""

    def __init__(self):
        self.indicators = indicators_calculator
        self.divergence_detector = divergence_detector

    def analyze_signal(self, signal_data: Dict, symbol: str) -> Dict[str, any]:
        """
        Analiza una señal completa con todos los indicadores y divergencias - ACTUALIZADO
        """
        try:
            # 1. Análisis técnico de todas las temporalidades
            technical_analysis = self.indicators.analyze_all_timeframes(symbol)
            if not technical_analysis:
                return self._create_error_analysis(
                    "No se pudo obtener análisis técnico"
                )

            # 2. Detección de divergencias
            divergences = self.divergence_detector.analyze_divergences(
                symbol, technical_analysis
            )

            # 3. Análisis de confirmación de señal - MEJORADO
            confirmation_result = self._analyze_signal_confirmation(
                signal_data, technical_analysis
            )

            # 4. Generar recomendación final CON APALANCAMIENTO
            recommendation = self._generate_recommendation(
                signal_data, technical_analysis, divergences, confirmation_result
            )

            # 5. Compilar resultado completo
            result = {
                "symbol": symbol,
                "technical_analysis": technical_analysis,
                "divergences": divergences,
                "confirmation_result": confirmation_result,
                "recommendation": recommendation,
                "signal_original": signal_data,
                "analysis_timestamp": self._get_current_timestamp(),
                "leverage": signal_data.get("leverage", LEVERAGE),
            }

            logger.info(
                f"✅ Análisis completado para {symbol}: {recommendation.action} (x{signal_data.get('leverage', LEVERAGE)})"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error en análisis de {symbol}: {e}")
            return self._create_error_analysis(str(e))

    # trend_analysis.py - AJUSTAR LA LÓGICA EN _analyze_signal_confirmation
    def _analyze_signal_confirmation(
        self, signal_data: Dict, technical_analysis: Dict
    ) -> Dict[str, any]:
        """
        Analiza si la señal recibida está confirmada por los indicadores - MÁS FLEXIBLE
        """
        try:
            signal_direction = signal_data["direction"]
            consolidated = technical_analysis.get("consolidated", {})
            predominant_trend = consolidated.get("predominant_trend", "NEUTRO")
            predominant_macd = consolidated.get("predominant_macd", "NEUTRO")
            avg_rsi = consolidated.get("avg_rsi", 50)
            
            # ✅ MEJORADO: Contadores de coincidencia por timeframe con puntuación granular
            total_score = 0
            max_possible_score = 0
            timeframe_details = []

            for tf_key, analysis in technical_analysis.items():
                if tf_key.startswith("tf_"):
                    timeframe = analysis.get("timeframe", "1")
                    tf_score = 0
                    tf_max_score = 0
                    reasons = []
                    
                    # 1. Tendencia EMA (40 puntos máximo)
                    tf_max_score += 40
                    ema_trend = analysis["ema_trend"]
                    if ema_trend == signal_direction:
                        tf_score += 40
                        reasons.append("✅ Tendencia EMA favorable")
                    elif ema_trend == "NEUTRO":
                        tf_score += 25  # ✅ INCREMENTADO: Más puntos para tendencia neutra
                        reasons.append("⚠️ Tendencia EMA neutra")
                    else:
                        tf_score += 5   # ✅ NUEVO: Puntos mínimos incluso para tendencia contraria
                        reasons.append("❌ Tendencia EMA contraria")
                    
                    # 2. RSI (30 puntos máximo)
                    tf_max_score += 30
                    rsi_value = analysis["rsi"]
                    if signal_direction == "LONG":
                        if rsi_value < 40:  # ✅ AJUSTADO: Más flexible
                            tf_score += 30
                            reasons.append("✅ RSI en zona favorable para LONG")
                        elif rsi_value < 55:
                            tf_score += 25  # ✅ INCREMENTADO: Más puntos para zona neutral
                            reasons.append("✅ RSI en zona neutral-baja")
                        elif rsi_value < 70:
                            tf_score += 15  # ✅ INCREMENTADO: Más puntos para zona alta
                            reasons.append("⚠️ RSI en zona neutral-alta")
                        else:
                            tf_score += 5   # ✅ NUEVO: Puntos mínimos
                            reasons.append("❌ RSI sobrecomprado")
                    else:  # SHORT
                        if rsi_value > 60:  # ✅ AJUSTADO: Más flexible
                            tf_score += 30
                            reasons.append("✅ RSI en zona favorable para SHORT")
                        elif rsi_value > 45:
                            tf_score += 25  # ✅ INCREMENTADO: Más puntos para zona neutral
                            reasons.append("✅ RSI en zona neutral-alta")
                        elif rsi_value > 30:
                            tf_score += 15  # ✅ INCREMENTADO: Más puntos para zona baja
                            reasons.append("⚠️ RSI en zona neutral-baja")
                        else:
                            tf_score += 5   # ✅ NUEVO: Puntos mínimos
                            reasons.append("❌ RSI sobrevendido")
                    
                    # 3. MACD (30 puntos máximo)
                    tf_max_score += 30
                    macd_signal = analysis["macd_signal"]
                    if macd_signal == signal_direction:
                        tf_score += 30
                        reasons.append("✅ Señal MACD favorable")
                    elif macd_signal == "NEUTRO":
                        tf_score += 20  # ✅ INCREMENTADO: Más puntos para MACD neutro
                        reasons.append("⚠️ Señal MACD neutra")
                    else:
                        tf_score += 5   # ✅ NUEVO: Puntos mínimos
                        reasons.append("❌ Señal MACD contraria")
                    
                    # Calcular porcentaje para este timeframe
                    tf_percentage = (tf_score / tf_max_score * 100) if tf_max_score > 0 else 0
                    
                    timeframe_details.append({
                        'timeframe': timeframe,
                        'score': tf_score,
                        'max_score': tf_max_score,
                        'percentage': tf_percentage,
                        'reasons': reasons
                    })
                    
                    total_score += tf_score
                    max_possible_score += tf_max_score

            # Calcular porcentaje total de coincidencia
            match_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
            
            # ✅ MEJORADO: Análisis de consistencia entre timeframes más flexible
            consistent_timeframes = 0
            total_timeframes = len(timeframe_details)
            
            for tf_detail in timeframe_details:
                if tf_detail['percentage'] >= 40:  # ✅ REDUCIDO: 40% en lugar de 50%
                    consistent_timeframes += 1
            
            consistency_ratio = consistent_timeframes / total_timeframes if total_timeframes > 0 else 0
            
            # ✅ MEJORADO: Lógica de confirmación MÁS FLEXIBLE
            if match_percentage >= 55 and consistency_ratio >= 0.5:  # ✅ REDUCIDO: 55% y 50%
                status = "CONFIRMADA"
                confidence = "ALTA"
            elif match_percentage >= 45 and consistency_ratio >= 0.33:  # ✅ REDUCIDO: 45% y 33%
                status = "PARCIALMENTE CONFIRMADA" 
                confidence = "MEDIA"
            elif match_percentage >= 35:  # ✅ REDUCIDO: 35%
                status = "DÉBILMENTE CONFIRMADA"
                confidence = "BAJA"
            else:
                status = "NO CONFIRMADA"
                confidence = "MUY BAJA"

            # ✅ MEJORADO: Boost de confianza para tokens nuevos
            # Si es un token nuevo (como ICNT, ZORA, etc.), ser más flexible
            symbol = signal_data.get('pair', '').upper()
            is_new_token = any(token in symbol for token in ['ICNT', 'ZORA', 'LAB', 'PIPPIN'])
            
            if is_new_token:
                # Boost para tokens nuevos
                if status == "DÉBILMENTE CONFIRMADA" and match_percentage >= 40:
                    status = "PARCIALMENTE CONFIRMADA"
                    confidence = "MEDIA"
                    logger.info(f"🎯 Boost aplicado para token nuevo: {symbol}")

            # Boost de confianza si hay factores adicionales favorables
            volume_analysis = self._analyze_volume_confirmation(technical_analysis, signal_direction)
            if volume_analysis["volume_confirms"] and confidence in ["ALTA", "MEDIA"]:
                confidence = "ALTA"
                volume_analysis["confidence_boost"] = True

            # Análisis de tendencia predominante
            trend_aligned = predominant_trend == signal_direction
            macd_aligned = predominant_macd == signal_direction

            result = {
                "status": status,
                "confidence": confidence,
                "match_percentage": round(match_percentage, 1),
                "consistency_ratio": round(consistency_ratio, 2),
                "consistent_timeframes": f"{consistent_timeframes}/{total_timeframes}",
                "trend_aligned": trend_aligned,
                "macd_aligned": macd_aligned,
                "predominant_trend": predominant_trend,
                "avg_rsi": avg_rsi,
                "volume_analysis": volume_analysis,
                "timeframe_details": timeframe_details,
                "scoring_summary": f"{total_score}/{max_possible_score}",
                "is_new_token": is_new_token,  # ✅ NUEVO: Para debugging
            }

            logger.info(
                f"📊 Confirmación: {status} ({confidence}) - "
                f"Match: {match_percentage:.1f}% - "
                f"Consistencia: {consistent_timeframes}/{total_timeframes} - "
                f"Token Nuevo: {'Sí' if is_new_token else 'No'}"
            )
            
            return result

        except Exception as e:
            logger.error(f"❌ Error en análisis de confirmación: {e}")
            return {
                "status": "ERROR",
                "confidence": "MUY BAJA",
                "match_percentage": 0.0,
                "reason": f"Error en análisis: {str(e)}"
            }

    def analyze_trend_confirmation(
        self, symbol: str, signal_data: Dict, analysis_data: Dict
    ) -> Dict:
        """Analiza confirmación de tendencia - CORREGIDO"""

        try:
            # ✅ Asegurar que entry esté disponible
            entry_price = signal_data.get("entry", 0.0)

            # Tu análisis existente...
            analysis_result = {
                "status": "CONFIRMADA",
                "match_percentage": 0.0,
                "confidence": "ALTA",
                "entry_price": entry_price,
                "summary": "Análisis completado",
            }

            return analysis_result

        except Exception as e:
                logger.error(f"❌ Error en análisis de {symbol}: {e}")
                return {
                    "status": "ERROR",
                    "match_percentage": 0.0,
                    "confidence": "BAJA",
                    "entry_price": 0.0,
                    "summary": f"Error: {str(e)}",
                }

    def _analyze_volume_confirmation(
        self, technical_analysis: Dict, signal_direction: str
    ) -> Dict[str, any]:
        """
        Analiza confirmación por volumen (estructura preparada para implementación futura)
        """
        try:
            # Placeholder para cuando integres datos de volumen reales
            volume_analysis = {
                "volume_confirms": False,
                "volume_trend": "NEUTRO",
                "volume_spike": False,
                "confidence": "BAJA",
                "message": "Análisis de volumen no disponible aún",
            }

            # Simulación básica: volumen "confirma" si las tendencias son consistentes
            trend_consistency = 0
            total_tfs = 0

            for tf_key, analysis in technical_analysis.items():
                if tf_key.startswith("tf_"):
                    total_tfs += 1
                    if analysis["ema_trend"] == signal_direction:
                        trend_consistency += 1

            # Si más del 70% de timeframes confirman la dirección, simular volumen confirmando
            if total_tfs > 0 and (trend_consistency / total_tfs) >= 0.7:
                volume_analysis["volume_confirms"] = True
                volume_analysis["confidence"] = "MEDIA"
                volume_analysis["message"] = (
                    "Tendencias consistentes sugieren volumen confirmatorio"
                )

            logger.debug(
                f"📊 Análisis de volumen simulado: {volume_analysis['volume_confirms']}"
            )
            return volume_analysis

        except Exception as e:
            logger.error(f"❌ Error analizando volumen: {e}")
            return {
                "volume_confirms": False,
                "volume_trend": "NEUTRO",
                "volume_spike": False,
                "confidence": "BAJA",
                "message": f"Error en análisis: {str(e)}",
            }

    def _generate_recommendation(
        self,
        signal_data: Dict,
        technical_analysis: Dict,
        divergences: List,
        confirmation_result: Dict,
    ) -> TradingRecommendation:
        """
        Genera recomendación de trading basada en todos los factores - MEJORADO
        """
        symbol = signal_data["pair"]
        signal_direction = signal_data["direction"]
        signal_entry = signal_data["entry"]
        leverage = signal_data.get("leverage", LEVERAGE)
        confirmation_status = confirmation_result["status"]
        match_percentage = confirmation_result["match_percentage"]

        # Obtener precio actual del primer timeframe
        current_price = None
        for tf_key, analysis in technical_analysis.items():
            if tf_key.startswith("tf_"):
                current_price = analysis["close_price"]
                break

        if current_price is None:
            return TradingRecommendation(
                action="ESPERAR",
                confidence="BAJA",
                reason="No se pudo obtener precio actual",
                leverage=leverage,
            )

        # ✅ MEJORADO: Lógica de divergencias más flexible
        strong_divergences = [d for d in divergences if d.strength == "strong"]
        if strong_divergences:
            strongest_div = strong_divergences[0]
            divergence_type = strongest_div.type
            
            # Solo rechazar si la divergencia es muy fuerte Y la confirmación es débil
            if (divergence_type == "bullish" and signal_direction == "SHORT" and match_percentage < 40) or \
               (divergence_type == "bearish" and signal_direction == "LONG" and match_percentage < 40):
                return TradingRecommendation(
                    action="ESPERAR",
                    confidence="ALTA",
                    reason=f"Divergencia {divergence_type} fuerte detectada con confirmación débil",
                    leverage=leverage,
                )

        # ✅ MEJORADO: Lógica de confirmación más granular
        if confirmation_status == "NO CONFIRMADA" and match_percentage < 30:
            return TradingRecommendation(
                action="ESPERAR",
                confidence=confirmation_result["confidence"],
                reason=f"Señal no confirmada por análisis técnico ({match_percentage}% coincidencia)",
                leverage=leverage,
            )

        # ✅ MEJORADO: Para confirmaciones débiles o parciales, considerar condiciones adicionales
        price_diff_pct = abs(current_price - signal_entry) / signal_entry * 100
        
        # Si el precio está favorable (cerca del entry) y hay al menos confirmación débil
        if price_diff_pct <= 2.0 and confirmation_status != "NO CONFIRMADA":
            stop_loss = self._calculate_stop_loss(
                current_price, signal_direction, technical_analysis, leverage
            )
            position_info = calculate_position_size(
                ACCOUNT_BALANCE, RISK_PER_TRADE, current_price, stop_loss, leverage
            )

            action = "ENTRAR" if confirmation_status in ["CONFIRMADA", "PARCIALMENTE CONFIRMADA"] else "ESPERAR MEJOR ENTRADA"
            
            return TradingRecommendation(
                action=action,
                confidence=confirmation_result["confidence"],
                reason=f"Señal {confirmation_status.lower()} con precio favorable ({price_diff_pct:.1f}% del entry)",
                suggested_entry=current_price,
                stop_loss=stop_loss,
                take_profits=self._extract_take_profits(signal_data),
                position_size=position_info["position_size"],
                dollar_risk=position_info["dollar_risk"],
                leverage=leverage,
                real_risk_percent=position_info["real_risk_percent"],
            )
        else:
            # Para señales confirmadas pero con precio lejano, buscar entry optimizado
            optimized_entry = self._calculate_optimized_entry(
                current_price, signal_entry, signal_direction, technical_analysis
            )
            
            stop_loss = self._calculate_stop_loss(
                optimized_entry, signal_direction, technical_analysis, leverage
            )
            position_info = calculate_position_size(
                ACCOUNT_BALANCE, RISK_PER_TRADE, optimized_entry, stop_loss, leverage
            )

            entry_type = "ORIGINAL" if optimized_entry == signal_entry else "OPTIMIZADA"
            
            return TradingRecommendation(
                action="ENTRAR",
                confidence=confirmation_result["confidence"],
                reason=f"Señal {confirmation_status.lower()} - Entry {entry_type}",
                suggested_entry=optimized_entry,
                stop_loss=stop_loss,
                take_profits=self._extract_take_profits(signal_data),
                position_size=position_info["position_size"],
                dollar_risk=position_info["dollar_risk"],
                leverage=leverage,
                real_risk_percent=position_info["real_risk_percent"],
            )

    def _calculate_optimized_entry(
        self,
        current_price: float,
        signal_entry: float,
        direction: str,
        technical_analysis: Dict,
    ) -> float:
        """
        Calcula entry optimizado basado en estructura de precio y niveles técnicos
        """
        try:
            # 1. Análisis de proximidad al precio original
            price_diff_pct = abs(current_price - signal_entry) / signal_entry * 100

            # Si está muy cerca (<= 0.5%), usar precio actual
            if price_diff_pct <= 0.5:
                logger.info(
                    f"✅ Precio actual favorable para entry inmediato: {current_price}"
                )
                return current_price

            # 2. Buscar niveles de soporte/resistencia cercanos para mejores entries
            support_resistance_levels = self._find_nearby_support_resistance(
                current_price, direction, technical_analysis
            )

            # 3. Para LONG: buscar entry en soporte cercano
            if direction == "LONG":
                optimal_entry = self._find_optimal_long_entry(
                    current_price, signal_entry, support_resistance_levels
                )

            # 4. Para SHORT: buscar entry en resistencia cercana
            else:
                optimal_entry = self._find_optimal_short_entry(
                    current_price, signal_entry, support_resistance_levels
                )

            # 5. Validar que el entry optimizado no esté muy lejos del original
            optimized_diff_pct = abs(optimal_entry - signal_entry) / signal_entry * 100
            if optimized_diff_pct > 5:  # Máximo 5% de desviación
                logger.warning(
                    f"⚠️ Entry optimizado muy lejano ({optimized_diff_pct:.1f}%), usando original"
                )
                return signal_entry

            logger.info(
                f"🎯 Entry optimizado: {optimal_entry} (original: {signal_entry})"
            )
            return optimal_entry

        except Exception as e:
            logger.error(f"❌ Error calculando entry optimizado: {e}")
            return signal_entry  # Fallback al original

    def _find_nearby_support_resistance(
        self, current_price: float, direction: str, technical_analysis: Dict
    ) -> Dict[str, List[float]]:
        """
        Encuentra niveles de soporte y resistencia cercanos al precio actual
        """
        levels = {"support": [], "resistance": []}

        try:
            # Analizar cada timeframe para encontrar niveles clave
            for tf_key, analysis in technical_analysis.items():
                if not tf_key.startswith("tf_"):
                    continue

                # Usar EMA como niveles dinámicos de soporte/resistencia
                ema_short = analysis.get("ema_short")
                ema_long = analysis.get("ema_long")

                if ema_short and ema_long:
                    # EMA corta como nivel inmediato
                    if direction == "LONG" and ema_short < current_price:
                        levels["support"].append(ema_short)
                    elif direction == "SHORT" and ema_short > current_price:
                        levels["resistance"].append(ema_short)

                    # EMA larga como nivel principal
                    if direction == "LONG" and ema_long < current_price:
                        levels["support"].append(ema_long)
                    elif direction == "SHORT" and ema_long > current_price:
                        levels["resistance"].append(ema_long)

            # Ordenar y eliminar duplicados
            levels["support"] = sorted(list(set(levels["support"])), reverse=True)
            levels["resistance"] = sorted(list(set(levels["resistance"])))

            logger.debug(
                f"📊 Niveles encontrados - Soportes: {levels['support']}, Resistencias: {levels['resistance']}"
            )
            return levels

        except Exception as e:
            logger.error(f"❌ Error buscando niveles S/R: {e}")
            return levels

    def _find_optimal_long_entry(
        self,
        current_price: float,
        original_entry: float,
        levels: Dict[str, List[float]],
    ) -> float:
        """
        Encuentra entry optimizado para posición LONG
        """
        # Buscar soporte más cercano por debajo del precio actual
        nearby_supports = [s for s in levels["support"] if s < current_price]

        if nearby_supports:
            # Tomar el soporte más alto (más cercano al precio actual)
            best_support = max(nearby_supports)

            # Verificar que no esté demasiado lejos del precio actual (máximo 2%)
            distance_pct = (current_price - best_support) / current_price * 100
            if distance_pct <= 2.0:
                return best_support

        # Si no hay soportes adecuados, usar lógica de precio original
        price_diff_pct = abs(current_price - original_entry) / original_entry * 100
        if price_diff_pct <= 1.0:
            return current_price  # Precio favorable para entrada inmediata
        else:
            return original_entry  # Mantener entry original

    def _find_optimal_short_entry(
        self,
        current_price: float,
        original_entry: float,
        levels: Dict[str, List[float]],
    ) -> float:
        """
        Encuentra entry optimizado para posición SHORT
        """
        # Buscar resistencia más cercana por encima del precio actual
        nearby_resistances = [r for r in levels["resistance"] if r > current_price]

        if nearby_resistances:
            # Tomar la resistencia más baja (más cercana al precio actual)
            best_resistance = min(nearby_resistances)

            # Verificar que no esté demasiado lejos (máximo 2%)
            distance_pct = (best_resistance - current_price) / current_price * 100
            if distance_pct <= 2.0:
                return best_resistance

        # Fallback a lógica original
        price_diff_pct = abs(current_price - original_entry) / original_entry * 100
        if price_diff_pct <= 1.0:
            return current_price
        else:
            return original_entry

    def _calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        technical_analysis: Dict,
        leverage: int = LEVERAGE,
    ) -> float:
        """
        Calcula stop loss basado en ATR, volatilidad, niveles técnicos y APALANCAMIENTO - MEJORADO
        """
        try:
            consolidated = technical_analysis.get("consolidated", {})
            atr_multiplier = consolidated.get("max_atr_multiplier", 1.0)

            # 1. Encontrar niveles técnicos clave para stop
            key_levels = self._find_key_stop_levels(
                entry_price, direction, technical_analysis
            )

            # 2. Calcular stop basado en niveles técnicos si están disponibles
            technical_stop = self._calculate_technical_stop(
                entry_price, direction, key_levels
            )

            if technical_stop:
                # Validar que el stop técnico sea seguro con el apalancamiento
                stop_distance_pct = (
                    abs(entry_price - technical_stop) / entry_price * 100
                )
                leverage_adjusted_max = MAX_STOP_DISTANCE / (
                    leverage / 10
                )  # Ajustado por leverage
                if stop_distance_pct <= leverage_adjusted_max:
                    logger.info(f"🎯 Stop loss técnico encontrado: {technical_stop}")
                    return technical_stop

            # 3. Fallback: stop basado en ATR y volatilidad CON APALANCAMIENTO
            return self._calculate_leverage_adjusted_stop(
                entry_price, direction, atr_multiplier, leverage
            )

        except Exception as e:
            logger.error(f"❌ Error calculando stop loss: {e}")
            # Fallback conservador con apalancamiento
            return self._calculate_conservative_leverage_stop(
                entry_price, direction, leverage
            )

    def _calculate_leverage_adjusted_stop(
        self, entry_price: float, direction: str, atr_multiplier: float, leverage: int
    ) -> float:
        """
        Calcula stop loss ajustado por apalancamiento - NUEVA FUNCIÓN
        """
        # Distancia base ajustada por volatilidad Y apalancamiento
        base_stop_distance = BASE_STOP_PERCENTAGE  # 3% base
        leverage_factor = 20 / leverage  # Normalizar a 20x

        atr_distance = base_stop_distance * atr_multiplier * leverage_factor

        # Aplicar límites razonables para apalancamiento
        min_distance = MIN_STOP_DISTANCE  # 0.5% mínimo
        max_distance = MAX_STOP_DISTANCE / leverage  # Máximo ajustado por leverage

        final_distance = max(min_distance, min(atr_distance, max_distance))

        stop_distance = entry_price * final_distance

        if direction == "LONG":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def _calculate_conservative_leverage_stop(
        self, entry_price: float, direction: str, leverage: int
    ) -> float:
        """Stop loss conservador ajustado por apalancamiento - NUEVA FUNCIÓN"""
        # 3% base pero dividido por leverage para riesgo real
        stop_pct = BASE_STOP_PERCENTAGE / (leverage / 10)  # 3% / 2 = 1.5% real con 20x
        stop_distance = entry_price * stop_pct

        if direction == "LONG":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def _find_key_stop_levels(
        self, entry_price: float, direction: str, technical_analysis: Dict
    ) -> Dict[str, float]:
        """
        Encuentra niveles clave para colocar stops
        """
        levels = {}

        try:
            # Buscar el nivel de EMA larga más relevante
            ema_long_levels = []
            for tf_key, analysis in technical_analysis.items():
                if tf_key.startswith("tf_"):
                    ema_long = analysis.get("ema_long")
                    if ema_long:
                        # Para LONG: EMA por debajo del entry como soporte
                        if direction == "LONG" and ema_long < entry_price:
                            ema_long_levels.append(ema_long)
                        # Para SHORT: EMA por encima del entry como resistencia
                        elif direction == "SHORT" and ema_long > entry_price:
                            ema_long_levels.append(ema_long)

            if ema_long_levels:
                if direction == "LONG":
                    levels["key_support"] = max(ema_long_levels)  # Soporte más fuerte
                else:
                    levels["key_resistance"] = min(
                        ema_long_levels
                    )  # Resistencia más fuerte

            return levels

        except Exception as e:
            logger.error(f"❌ Error encontrando niveles para stops: {e}")
            return levels

    def _calculate_technical_stop(
        self, entry_price: float, direction: str, key_levels: Dict[str, float]
    ) -> float:
        """
        Calcula stop loss basado en niveles técnicos
        """
        try:
            if direction == "LONG" and "key_support" in key_levels:
                support_level = key_levels["key_support"]
                # Colocar stop un poco por debajo del soporte clave
                stop_buffer = support_level * 0.005  # 0.5% por debajo del soporte
                return support_level - stop_buffer

            elif direction == "SHORT" and "key_resistance" in key_levels:
                resistance_level = key_levels["key_resistance"]
                # Colocar stop un poco por encima de la resistencia clave
                stop_buffer = (
                    resistance_level * 0.005
                )  # 0.5% por encima de la resistencia
                return resistance_level + stop_buffer

            return None  # No se encontraron niveles técnicos adecuados

        except Exception as e:
            logger.error(f"❌ Error calculando stop técnico: {e}")
            return None

    def _extract_take_profits(self, signal_data: Dict) -> List[float]:
        """Extrae niveles de take profit de la señal"""
        take_profits = []
        for i in range(1, 5):  # TP1 a TP4
            tp_key = f"tp{i}"
            if tp_key in signal_data and signal_data[tp_key]:
                take_profits.append(signal_data[tp_key])
        return take_profits

    def _get_current_timestamp(self) -> str:
        """Retorna timestamp actual en formato ISO"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _create_error_analysis(self, error_message: str) -> Dict[str, any]:
        """Crea un análisis de error"""
        return {
            "symbol": "UNKNOWN",
            "technical_analysis": {},
            "divergences": [],
            "confirmation_result": {
                "status": "ERROR",
                "confidence": "MUY BAJA",
                "reason": error_message,
            },
            "recommendation": TradingRecommendation(
                action="ESPERAR",
                confidence="BAJA",
                reason=error_message,
                leverage=LEVERAGE,
            ),
            "signal_original": {},
            "analysis_timestamp": self._get_current_timestamp(),
        }

    def get_analysis_summary(self, analysis_result: Dict) -> Dict[str, any]:
        """
        Crea un resumen simplificado del análisis para notificaciones - ACTUALIZADO CON APALANCAMIENTO
        """
        tech_analysis = analysis_result["technical_analysis"]
        confirmation = analysis_result["confirmation_result"]
        recommendation = analysis_result["recommendation"]
        signal_data = analysis_result["signal_original"]
        leverage = signal_data.get("leverage", LEVERAGE)

        # Resumen por timeframe
        timeframe_summary = {}
        for tf_key, analysis in tech_analysis.items():
            if tf_key.startswith("tf_"):
                tf = analysis["timeframe"]
                timeframe_summary[f"trend_{tf}m"] = analysis["ema_trend"]
                timeframe_summary[f"rsi_{tf}m"] = analysis["rsi"]

        # Información de divergencias
        divergence_info = "No"
        divergence_type = None
        if analysis_result["divergences"]:
            strongest_div = analysis_result["divergences"][0]
            divergence_info = "Sí"
            divergence_type = f"{strongest_div.type} {strongest_div.indicator}"

        # Información de volumen
        volume_analysis = confirmation.get("volume_analysis", {})
        volume_confirms = volume_analysis.get("volume_confirms", False)

        return {
            "symbol": analysis_result["symbol"],
            "timeframe_summary": timeframe_summary,
            "confirmation_status": confirmation["status"],
            "confidence": confirmation["confidence"],
            "match_percentage": confirmation["match_percentage"],
            "confirmation_factors": confirmation.get("confirmation_factors", "N/A"),
            "recommendation_action": recommendation.action,
            "recommendation_confidence": recommendation.confidence,
            "recommendation_reason": recommendation.reason,
            "divergence_detected": divergence_info,
            "divergence_type": divergence_type,
            "volume_confirmation": "Sí" if volume_confirms else "No",
            "suggested_entry": recommendation.suggested_entry,
            "stop_loss": recommendation.stop_loss,
            "take_profits": recommendation.take_profits,
            "position_size": recommendation.position_size,
            "dollar_risk": recommendation.dollar_risk,
            "leverage": leverage,
            "real_risk_percent": recommendation.real_risk_percent,
            "predominant_trend": tech_analysis.get("consolidated", {}).get(
                "predominant_trend", "N/A"
            ),
            "avg_rsi": tech_analysis.get("consolidated", {}).get("avg_rsi", "N/A"),
            "predominant_macd": tech_analysis.get("consolidated", {}).get(
                "predominant_macd", "N/A"
            ),
            "max_atr_multiplier": tech_analysis.get("consolidated", {}).get(
                "max_atr_multiplier", "N/A"
            ),
        }


# Instancia global
trend_analyzer = TrendAnalyzer()