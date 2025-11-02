# trend_analysis.py - VERSIÓN COMPLETA CON ENTRADA INMEDIATA
"""
Análisis de tendencias - ENFOQUE ENTRADA INMEDIATA CON PRECIO ACTUAL
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from config import *
from indicators import indicators_calculator
from divergence_detector import evaluate_divergences
from helpers import calculate_position_size
from datetime import datetime

logger = logging.getLogger(__name__)

# Parámetros de ChatGPT - MEJORADOS
MIN_MATCH_TO_ENTER = 0.5      # 50% para entrada
MIN_MATCH_TO_CAUTION = 0.33   # 33% para entrada con precaución
PRICE_MOVE_THRESHOLD = 0.003  # 0.3% price move considered confirmation
VOLATILITY_PENALTY = 0.15     # penalización por alta volatilidad

@dataclass
class TradingRecommendation:
    """Estructura para recomendaciones de trading - MANTIENE TU ESTRUCTURA"""
    action: str  # ENTRAR, ESPERAR, CERRAR, REVERTIR
    confidence: str  # ALTA, MEDIA, BAJA
    reason: str
    suggested_entry: float = None
    stop_loss: float = None
    take_profits: List[float] = None
    position_size: float = None
    dollar_risk: float = None
    leverage: int = LEVERAGE
    real_risk_percent: float = None

class TrendAnalyzer:
    """Analizador de tendencias - ENTRADA INMEDIATA CON PRECIO ACTUAL"""

    def __init__(self):
        self.indicators = indicators_calculator

    async def analyze_signal(self, signal_data: Dict, symbol: str) -> Dict[str, any]:
        """
        Analiza una señal completa - ENTRADA INMEDIATA
        """
        try:
            # 1. Análisis técnico de todas las temporalidades (tu método existente)
            logger.info(f"🔍 Iniciando análisis ChatGPT para {symbol}")
            technical_analysis = self.indicators.analyze_all_timeframes(symbol)
            if not technical_analysis:
                return self._create_error_analysis("No se pudo obtener análisis técnico")

            # 2. Convertir estructura para ChatGPT
            indicators_by_tf = self._convert_to_chatgpt_format(technical_analysis)
            
            # 3. Análisis principal con núcleo ChatGPT
            analysis_result = await self._chatgpt_analysis(symbol, signal_data, indicators_by_tf)

            # 4. Convertir resultado a tu estructura
            final_result = self._convert_to_your_format(signal_data, symbol, technical_analysis, analysis_result)

            logger.info(f"✅ Análisis ChatGPT completado para {symbol}: {final_result['recommendation'].action}")
            return final_result

        except Exception as e:
            logger.error(f"❌ Error en análisis de {symbol}: {e}")
            return self._create_error_analysis(str(e))

    async def _chatgpt_analysis(self, symbol: str, signal_data: Dict, indicators_by_tf: Dict) -> Dict:
        """
        Núcleo de análisis de ChatGPT - ENTRADA INMEDIATA
        """
        signal_direction = signal_data["direction"].lower()  # 'long' o 'short'
        entry_price = signal_data["entry"]
        leverage = signal_data.get("leverage", LEVERAGE)

        logger.info(f"📊 ChatGPT analyzing {symbol} direction={signal_direction}")

        # 1. Basic match from indicators
        basic_match = self._compute_basic_match(indicators_by_tf, signal_direction)
        logger.info(f"📊 Basic match: {basic_match:.3f}")

        # 2. Divergence impact 
        div_summary = evaluate_divergences(indicators_by_tf, signal_data["direction"], leverage=leverage)
        div_impact = div_summary.get("confidence_impact", 0.0)
        logger.info(f"📊 Divergence impact: {div_impact:.3f}")
        
        # ✅ ENVÍO DE ALERTAS DE DIVERGENCIAS
        await self._send_divergence_alerts(symbol, div_summary)

        # 3. Volatility check
        vol_penalty = 0.0
        for tf, data in indicators_by_tf.items():
            # Usar ATR de tu análisis técnico si está disponible
            atr_rel = data.get("atr_multiplier", 1.0)
            if atr_rel > 1.5:  # Alta volatilidad
                vol_penalty += VOLATILITY_PENALTY * 0.3
                logger.info(f"📊 High volatility detected in {tf}: ATR multiplier {atr_rel}")

        # 4. Combine
        match_ratio = basic_match + div_impact - vol_penalty
        match_ratio = max(0.0, min(1.0, match_ratio))

        logger.info(f"📊 Pre-re-eval match_ratio: {match_ratio:.3f} (basic: {basic_match:.3f}, div: {div_impact:.3f}, vol_pen: {vol_penalty:.3f})")

        # 5. Fast re-evaluation with price confirmation
        recommendation = "DESCARTAR"
        details = {
            "basic_match": basic_match,
            "div_impact": div_impact,
            "vol_penalty": vol_penalty,
            "match_ratio_before_reeval": match_ratio,
            "reeval": {}
        }

        # ✅ LÓGICA MEJORADA: Entrada basada en confirmación, NO en precio de entrada
        if match_ratio >= MIN_MATCH_TO_ENTER:
            recommendation = "ENTRADA"
            logger.info(f"🎯 Strong match - Direct ENTRADA recommendation")
        elif match_ratio >= MIN_MATCH_TO_CAUTION:
            # attempt quick re-eval via price move
            current_price = self._get_current_price_from_data(indicators_by_tf)
            if current_price is not None:
                details["current_price"] = current_price
                if signal_direction == "short":
                    if current_price <= entry_price * (1 - PRICE_MOVE_THRESHOLD):
                        match_ratio += 0.15
                        details["reeval"]["price_confirm"] = True
                        logger.info(f"🚀 Price confirmation BOOST: price moved down to {current_price} -> +15% match")
                    else:
                        details["reeval"]["price_confirm"] = False
                else:
                    if current_price >= entry_price * (1 + PRICE_MOVE_THRESHOLD):
                        match_ratio += 0.15
                        details["reeval"]["price_confirm"] = True
                        logger.info(f"🚀 Price confirmation BOOST: price moved up to {current_price} -> +15% match")
                    else:
                        details["reeval"]["price_confirm"] = False

            # re-normalize
            match_ratio = max(0.0, min(1.0, match_ratio))

            # after re-eval thresholds
            if match_ratio >= MIN_MATCH_TO_ENTER:
                recommendation = "ENTRADA_CON_PRECAUCION"
                logger.info(f"🎯 Post-re-eval: ENTRADA_CON_PRECAUCION (match: {match_ratio:.3f})")
            else:
                recommendation = "ESPERAR"
                logger.info(f"⏸️ Post-re-eval: ESPERAR (match: {match_ratio:.3f})")
        else:
            recommendation = "DESCARTAR"
            logger.info(f"❌ Low match: DESCARTAR (match: {match_ratio:.3f})")

        # 6. Adjust for leverage
        if leverage >= 20:
            if recommendation == "ENTRADA" and match_ratio < (MIN_MATCH_TO_ENTER + 0.1):
                recommendation = "ENTRADA_CON_PRECAUCION"
                logger.info(f"⚡ Downgraded to ENTRADA_CON_PRECAUCION due to high leverage ({leverage}x)")

        details["match_ratio"] = match_ratio
        details["recommendation"] = recommendation
        details["divergence_notes"] = div_summary.get("notes", [])
        details["divergences"] = div_summary.get("divergences", {})

        logger.info(f"✅ ChatGPT final: {symbol} match={match_ratio:.3f} recommendation={recommendation}")
        
        return {
            "symbol": symbol,
            "match_ratio": float(match_ratio),
            "recommendation": recommendation,
            "details": details
        }

    async def _send_divergence_alerts(self, symbol: str, div_summary: Dict):
        """Envía alertas de divergencias relevantes"""
        try:
            from notifier import telegram_notifier
            
            divergences = div_summary.get("divergences", {})
            notes = div_summary.get("notes", [])
            
            # Contar divergencias por tipo y fuerza
            strong_divergences = []
            
            for tf, div_data in divergences.items():
                for indicator, div_info in div_data.items():
                    if indicator in ['rsi', 'macd']:
                        div_type = div_info.get('type')
                        strength = div_info.get('strength', 0)
                        
                        # Solo alertar sobre divergencias moderadas o fuertes
                        if strength > 0.6 and div_type:
                            strong_divergences.append({
                                'type': div_type,
                                'indicator': indicator.upper(),
                                'timeframe': tf,
                                'strength': 'strong' if strength > 0.8 else 'moderate',
                                'confidence': strength
                            })
            
            # Enviar alerta si hay divergencias fuertes
            if strong_divergences:
                strongest = max(strong_divergences, key=lambda x: x['confidence'])
                
                # Determinar si es contraria a la tendencia actual (más importante)
                is_contrary = any(note.endswith('contrary') for note in notes)
                
                if is_contrary or strongest['confidence'] > 0.8:
                    await telegram_notifier.send_divergence_alert(
                        symbol=symbol,
                        divergence_type=strongest['type'],
                        strength=strongest['strength'],
                        timeframe=strongest['timeframe'],
                        confidence=strongest['confidence']
                    )
                    logger.info(f"📢 Alerta de divergencia enviada para {symbol}")
                    
        except Exception as e:
            logger.error(f"❌ Error enviando alertas de divergencia: {e}")

    def _compute_basic_match(self, indicators_by_tf: Dict, signal_direction: str):
        """ChatGPT's basic match calculation"""
        scores = []
        for tf, ind in indicators_by_tf.items():
            tf_score = 0.0
            # EMA trend
            try:
                ema_short = ind.get("ema_short")
                ema_long = ind.get("ema_long")
                if ema_short is not None and ema_long is not None:
                    if ema_short > ema_long and signal_direction == "long":
                        tf_score += 0.35
                        logger.debug(f"✅ {tf}: EMA trend supports LONG")
                    elif ema_short < ema_long and signal_direction == "short":
                        tf_score += 0.35
                        logger.debug(f"✅ {tf}: EMA trend supports SHORT")
            except Exception as e:
                logger.debug(f"❌ {tf}: EMA trend error: {e}")

            # RSI bias
            rsi = ind.get("rsi", None)
            if rsi is not None:
                if signal_direction == "long":
                    if rsi > 55:
                        tf_score += 0.2
                        logger.debug(f"✅ {tf}: RSI supports LONG (>55)")
                    elif rsi > 50:
                        tf_score += 0.1
                        logger.debug(f"⚠️ {tf}: RSI neutral for LONG (50-55)")
                else:
                    if rsi < 45:
                        tf_score += 0.2
                        logger.debug(f"✅ {tf}: RSI supports SHORT (<45)")
                    elif rsi < 50:
                        tf_score += 0.1
                        logger.debug(f"⚠️ {tf}: RSI neutral for SHORT (45-50)")

            # MACD histogram
            macd_hist = ind.get("macd_hist", None)
            if macd_hist is not None:
                if signal_direction == "long" and macd_hist > 0:
                    tf_score += 0.25
                    logger.debug(f"✅ {tf}: MACD supports LONG (positive)")
                elif signal_direction == "short" and macd_hist < 0:
                    tf_score += 0.25
                    logger.debug(f"✅ {tf}: MACD supports SHORT (negative)")

            # limit tf_score to 1.0
            tf_score = max(0.0, min(1.0, tf_score))
            scores.append(tf_score)
            logger.debug(f"📊 {tf} timeframe score: {tf_score:.3f}")

        if not scores:
            return 0.0
        
        final_score = sum(scores) / len(scores)
        logger.info(f"📊 Average timeframe score: {final_score:.3f}")
        return final_score

    def _get_current_price_from_data(self, indicators_by_tf: Dict):
        """Obtiene precio actual"""
        for tf, data in indicators_by_tf.items():
            if "close_price" in data:
                return float(data["close_price"])
        return None

    def _convert_to_chatgpt_format(self, technical_analysis: Dict) -> Dict:
        """Convierte tu estructura a formato ChatGPT"""
        indicators_by_tf = {}
        
        for tf_key, analysis in technical_analysis.items():
            if tf_key.startswith('tf_'):
                indicators_by_tf[tf_key] = {
                    'close_price': analysis.get('close_price', 0),
                    'ema_short': analysis.get('ema_short', 0),
                    'ema_long': analysis.get('ema_long', 0),
                    'rsi': analysis.get('rsi', 50),
                    'macd_hist': analysis.get('macd_histogram', 0) if 'macd_histogram' in analysis else analysis.get('macd_signal', 0),
                    'atr_multiplier': analysis.get('atr_multiplier', 1.0)
                }
                
        return indicators_by_tf

    def _convert_to_your_format(self, signal_data: Dict, symbol: str, technical_analysis: Dict, chatgpt_result: Dict) -> Dict:
        """Convierte resultado ChatGPT a tu formato"""
        
        match_ratio = chatgpt_result["match_ratio"]
        chatgpt_recommendation = chatgpt_result["recommendation"]
        details = chatgpt_result["details"]
        
        # Mapear recomendaciones ChatGPT a tus acciones
        if chatgpt_recommendation == "ENTRADA":
            action = "ENTRAR"
            confidence = "ALTA"
        elif chatgpt_recommendation == "ENTRADA_CON_PRECAUCION":
            action = "ENTRAR" 
            confidence = "MEDIA"
        elif chatgpt_recommendation == "ESPERAR":
            action = "ESPERAR"
            confidence = "BAJA"
        else:  # DESCARTAR
            action = "ESPERAR"
            confidence = "MUY BAJA"

        # ✅ OBTENER PRECIO ACTUAL (NUNCA esperar al entry original)
        current_price = self._get_current_price_from_data(self._convert_to_chatgpt_format(technical_analysis))
        leverage = signal_data.get("leverage", LEVERAGE)
        
        # Calcular stop loss y posición con precio ACTUAL
        stop_loss = self._calculate_stop_loss(current_price, signal_data["direction"], technical_analysis, leverage)
        position_info = calculate_position_size(
            ACCOUNT_BALANCE, RISK_PER_TRADE, current_price, stop_loss, leverage
        ) if current_price and stop_loss else {"position_size": 0, "dollar_risk": 0, "real_risk_percent": 0}

        # Crear razón descriptiva
        reason_parts = []
        reason_parts.append(f"Match: {match_ratio:.1%}")
        
        if details.get('reeval', {}).get('price_confirm'):
            reason_parts.append("Precio confirmó dirección")
            
        divergence_notes = details.get('divergence_notes', [])
        if divergence_notes:
            reason_parts.append(divergence_notes[0])
        else:
            reason_parts.append("Análisis técnico favorable")

        # ✅ CALCULAR TPs DINÁMICOS con precio actual
        take_profits = self._calculate_dynamic_take_profits(
            current_price, signal_data["direction"], leverage
        ) if current_price else []

        recommendation = TradingRecommendation(
            action=action,
            confidence=confidence,
            reason=" - ".join(reason_parts),
            suggested_entry=current_price,  # ✅ SIEMPRE precio ACTUAL
            stop_loss=stop_loss,
            take_profits=take_profits,     # ✅ TPs dinámicos
            position_size=position_info["position_size"],
            dollar_risk=position_info["dollar_risk"],
            leverage=leverage,
            real_risk_percent=position_info["real_risk_percent"],
        )

        # Crear confirmation_result en tu formato
        confirmation_status = "CONFIRMADA" if action == "ENTRAR" else "NO CONFIRMADA"
        confirmation_result = {
            "status": confirmation_status,
            "confidence": confidence,
            "match_percentage": match_ratio * 100,  # Convertir a porcentaje
            "reason": recommendation.reason,
            "consistency_ratio": 0.8,  # Placeholder
            "consistent_timeframes": "3/3",  # Placeholder
            "trend_aligned": True,  # Placeholder
            "macd_aligned": True,  # Placeholder
            "predominant_trend": signal_data["direction"],
            "avg_rsi": 50,  # Placeholder
        }

        return {
            "symbol": symbol,
            "technical_analysis": technical_analysis,
            "divergences": [],  # ChatGPT maneja divergencias internamente
            "confirmation_result": confirmation_result,
            "recommendation": recommendation,
            "signal_original": signal_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "leverage": leverage,
        }

    def _calculate_stop_loss(self, entry_price: float, direction: str, technical_analysis: Dict, leverage: int):
        """Calcula stop loss con precio actual"""
        try:
            if not entry_price:
                return None
                
            # Stop loss base del 2% ajustado por leverage
            base_stop_pct = 0.02 / (leverage / 10)  # Ajustar por leverage
            stop_distance = entry_price * base_stop_pct
            
            if direction == "LONG":
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance
                
        except Exception as e:
            logger.error(f"❌ Error calculando stop loss: {e}")
            return None

    def _calculate_dynamic_take_profits(self, entry_price: float, direction: str, leverage: int) -> List[float]:
        """
        Calcula take profits dinámicos basados en precio actual y leverage - NUEVO MÉTODO
        """
        try:
            if not entry_price:
                return []

            # Ajustar objetivos según leverage (más agresivo con mayor leverage)
            leverage_factor = min(leverage / 10, 2.0)  # Factor 1-2x según leverage
            
            base_multipliers = [0.008, 0.016, 0.024, 0.032]  # 0.8%, 1.6%, 2.4%, 3.2% base
            adjusted_multipliers = [m * leverage_factor for m in base_multipliers]
            
            take_profits = []
            
            for multiplier in adjusted_multipliers:
                if direction == "LONG":
                    tp = entry_price * (1 + multiplier)
                else:
                    tp = entry_price * (1 - multiplier)
                take_profits.append(round(tp, 6))
            
            logger.info(f"🎯 TPs dinámicos calculados para {direction} @ {entry_price}: {take_profits}")
            return take_profits
            
        except Exception as e:
            logger.error(f"❌ Error calculando TPs dinámicos: {e}")
            # Fallback a TPs conservadores
            return self._calculate_conservative_take_profits(entry_price, direction)

    def _calculate_conservative_take_profits(self, entry_price: float, direction: str) -> List[float]:
        """TPs conservadores de respaldo"""
        try:
            multipliers = [0.01, 0.02, 0.03, 0.04]  # 1%, 2%, 3%, 4%
            take_profits = []
            
            for multiplier in multipliers:
                if direction == "LONG":
                    tp = entry_price * (1 + multiplier)
                else:
                    tp = entry_price * (1 - multiplier)
                take_profits.append(round(tp, 6))
            
            return take_profits
        except Exception as e:
            logger.error(f"❌ Error en TPs conservadores: {e}")
            return []

    def _extract_take_profits(self, signal_data: Dict):
        """Extrae take profits de la señal (método legacy)"""
        take_profits = []
        for i in range(1, 5):
            tp_key = f"tp{i}"
            if tp_key in signal_data and signal_data[tp_key]:
                take_profits.append(signal_data[tp_key])
        return take_profits

    def _create_error_analysis(self, error_message: str) -> Dict[str, any]:
        """Crea análisis de error"""
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
            "analysis_timestamp": datetime.now().isoformat(),
        }

# Instancia global
trend_analyzer = TrendAnalyzer()