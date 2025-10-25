"""
Detección de divergencias RSI y MACD - MEJORADO
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from scipy.signal import argrelextrema

logger = logging.getLogger(__name__)

@dataclass
class Divergence:
    """Estructura para almacenar información de divergencia"""
    type: str  # 'bullish' o 'bearish'
    indicator: str  # 'RSI' o 'MACD'
    timeframe: str
    strength: str  # 'weak', 'moderate', 'strong'
    price_swing_low: float = None
    price_swing_high: float = None
    indicator_swing_low: float = None
    indicator_swing_high: float = None
    confidence: float = 0.0  # NUEVO: Confianza 0-1

class DivergenceDetector:
    """Detector de divergencias RSI y MACD - MEJORADO"""
    
    def __init__(self, lookback_period: int = 30, min_swing_distance: int = 5):
        self.lookback_period = lookback_period
        self.min_swing_distance = min_swing_distance
    
    def find_swing_points(self, data: pd.Series, order: int = 5) -> Tuple[List[int], List[int]]:
        """
        Encuentra puntos de swing usando scipy - MEJORADO
        """
        try:
            if len(data) < order * 2 + 1:
                logger.warning(f"Datos insuficientes para encontrar swings: {len(data)} puntos")
                return [], []
            
            # Usar scipy para encontrar extremos relativos
            minima_indices = argrelextrema(data.values, np.less, order=order)[0]
            maxima_indices = argrelextrema(data.values, np.greater, order=order)[0]
            
            # Filtrar swings muy cercanos
            minima_indices = self._filter_close_swings(minima_indices, data)
            maxima_indices = self._filter_close_swings(maxima_indices, data)
            
            # Convertir a listas de índices
            minima = [int(i) for i in minima_indices]
            maxima = [int(i) for i in maxima_indices]
            
            logger.debug(f"📊 Encontrados {len(minima)} mínimos y {len(maxima)} máximos")
            return minima, maxima
            
        except Exception as e:
            logger.error(f"❌ Error encontrando swing points: {e}")
            return [], []
    
    def _filter_close_swings(self, indices: np.ndarray, data: pd.Series) -> List[int]:
        """Filtra swings que están muy cercanos entre sí"""
        if len(indices) == 0:
            return []
        
        filtered = [indices[0]]
        for i in range(1, len(indices)):
            if indices[i] - filtered[-1] >= self.min_swing_distance:
                filtered.append(indices[i])
        
        return filtered
    
    def detect_rsi_divergence(self, price_data: pd.Series, rsi_data: pd.Series, 
                            timeframe: str) -> List[Divergence]:
        """
        Detecta divergencias RSI - MEJORADO
        """
        divergences = []
        
        try:
            # Validar datos
            if len(price_data) < 30 or len(rsi_data) < 30:
                logger.warning(f"Datos insuficientes para divergencias RSI en {timeframe}m")
                return divergences
            
            # Encontrar swings en precio y RSI (últimos 30 periodos para relevancia)
            recent_data = min(30, len(price_data))
            price_recent = price_data.tail(recent_data)
            rsi_recent = rsi_data.tail(recent_data)
            
            price_minima, price_maxima = self.find_swing_points(price_recent)
            rsi_minima, rsi_maxima = self.find_swing_points(rsi_recent)
            
            # Ajustar índices para datos recientes
            price_minima = [i + (len(price_data) - recent_data) for i in price_minima]
            price_maxima = [i + (len(price_data) - recent_data) for i in price_maxima]
            rsi_minima = [i + (len(rsi_data) - recent_data) for i in rsi_minima]
            rsi_maxima = [i + (len(rsi_data) - recent_data) for i in rsi_maxima]
            
            # Buscar divergencias bajistas (precio hace máximos más altos, RSI máximos más bajos)
            bearish_divs = self._find_bearish_divergence(
                price_data, rsi_data, price_maxima, rsi_maxima, timeframe, 'RSI'
            )
            divergences.extend(bearish_divs)
            
            # Buscar divergencias alcistas (precio hace mínimos más bajos, RSI mínimos más altos)
            bullish_divs = self._find_bullish_divergence(
                price_data, rsi_data, price_minima, rsi_minima, timeframe, 'RSI'
            )
            divergences.extend(bullish_divs)
                        
        except Exception as e:
            logger.error(f"❌ Error detectando divergencias RSI en {timeframe}m: {e}")
        
        return divergences
    
    def detect_macd_divergence(self, price_data: pd.Series, macd_histogram: pd.Series,
                             timeframe: str) -> List[Divergence]:
        """
        Detecta divergencias MACD basadas en el histograma - MEJORADO
        """
        divergences = []
        
        try:
            # Validar datos
            if len(price_data) < 30 or len(macd_histogram) < 30:
                logger.warning(f"Datos insuficientes para divergencias MACD en {timeframe}m")
                return divergences
            
            # Encontrar swings en precio y histograma MACD
            recent_data = min(30, len(price_data))
            price_recent = price_data.tail(recent_data)
            macd_recent = macd_histogram.tail(recent_data)
            
            price_minima, price_maxima = self.find_swing_points(price_recent)
            macd_minima, macd_maxima = self.find_swing_points(macd_recent)
            
            # Ajustar índices
            price_minima = [i + (len(price_data) - recent_data) for i in price_minima]
            price_maxima = [i + (len(price_data) - recent_data) for i in price_maxima]
            macd_minima = [i + (len(macd_histogram) - recent_data) for i in macd_minima]
            macd_maxima = [i + (len(macd_histogram) - recent_data) for i in macd_maxima]
            
            # Buscar divergencias bajistas
            bearish_divs = self._find_bearish_divergence(
                price_data, macd_histogram, price_maxima, macd_maxima, timeframe, 'MACD'
            )
            divergences.extend(bearish_divs)
            
            # Buscar divergencias alcistas
            bullish_divs = self._find_bullish_divergence(
                price_data, macd_histogram, price_minima, macd_minima, timeframe, 'MACD'
            )
            divergences.extend(bullish_divs)
                        
        except Exception as e:
            logger.error(f"❌ Error detectando divergencias MACD en {timeframe}m: {e}")
        
        return divergences
    
    def _find_bearish_divergence(self, price_data: pd.Series, indicator_data: pd.Series,
                               price_swings: List[int], indicator_swings: List[int],
                               timeframe: str, indicator: str) -> List[Divergence]:
        """Busca divergencias bajistas"""
        divergences = []
        
        if len(price_swings) >= 2 and len(indicator_swings) >= 2:
            # Tomar los dos swings más recientes
            price_swing1, price_swing2 = price_swings[-2], price_swings[-1]
            indicator_swing1, indicator_swing2 = indicator_swings[-2], indicator_swings[-1]
            
            price_high1 = price_data.iloc[price_swing1]
            price_high2 = price_data.iloc[price_swing2]
            indicator_high1 = indicator_data.iloc[indicator_swing1]
            indicator_high2 = indicator_data.iloc[indicator_swing2]
            
            # Verificar divergencia bajista
            if (price_high2 > price_high1 and indicator_high2 < indicator_high1):
                strength, confidence = self.calculate_divergence_strength_improved(
                    price_high1, price_high2, indicator_high1, indicator_high2, indicator
                )
                
                if confidence > 0.3:  # Mínima confianza requerida
                    divergence = Divergence(
                        type='bearish',
                        indicator=indicator,
                        timeframe=timeframe,
                        strength=strength,
                        price_swing_high=price_high2,
                        indicator_swing_high=indicator_high2,
                        confidence=confidence
                    )
                    divergences.append(divergence)
                    logger.info(f"🔻 Divergencia {indicator} bajista ({strength}) en {timeframe}m - Conf: {confidence:.2f}")
        
        return divergences
    
    def _find_bullish_divergence(self, price_data: pd.Series, indicator_data: pd.Series,
                               price_swings: List[int], indicator_swings: List[int],
                               timeframe: str, indicator: str) -> List[Divergence]:
        """Busca divergencias alcistas"""
        divergences = []
        
        if len(price_swings) >= 2 and len(indicator_swings) >= 2:
            # Tomar los dos swings más recientes
            price_swing1, price_swing2 = price_swings[-2], price_swings[-1]
            indicator_swing1, indicator_swing2 = indicator_swings[-2], indicator_swings[-1]
            
            price_low1 = price_data.iloc[price_swing1]
            price_low2 = price_data.iloc[price_swing2]
            indicator_low1 = indicator_data.iloc[indicator_swing1]
            indicator_low2 = indicator_data.iloc[indicator_swing2]
            
            # Verificar divergencia alcista
            if (price_low2 < price_low1 and indicator_low2 > indicator_low1):
                strength, confidence = self.calculate_divergence_strength_improved(
                    price_low1, price_low2, indicator_low1, indicator_low2, indicator
                )
                
                if confidence > 0.3:  # Mínima confianza requerida
                    divergence = Divergence(
                        type='bullish',
                        indicator=indicator,
                        timeframe=timeframe,
                        strength=strength,
                        price_swing_low=price_low2,
                        indicator_swing_low=indicator_low2,
                        confidence=confidence
                    )
                    divergences.append(divergence)
                    logger.info(f"🔺 Divergencia {indicator} alcista ({strength}) en {timeframe}m - Conf: {confidence:.2f}")
        
        return divergences
    
    def calculate_divergence_strength_improved(self, val1: float, val2: float, 
                                             indicator_val1: float, indicator_val2: float,
                                             indicator: str) -> Tuple[str, float]:
        """
        Calcula fuerza y confianza de divergencia - MEJORADO
        """
        try:
            # Calcular cambios porcentuales normalizados
            price_change_pct = abs(val2 - val1) / min(val1, val2)
            
            if indicator == 'RSI':
                # RSI está en escala 0-100
                indicator_change = abs(indicator_val2 - indicator_val1)
                # Cambio significativo en RSI es > 5 puntos
                indicator_strength = min(indicator_change / 5.0, 2.0)
            else:  # MACD
                # Para MACD, usar cambio relativo al rango típico
                typical_macd_range = 0.02  # Rango típico del histograma MACD
                indicator_strength = min(abs(indicator_val2 - indicator_val1) / typical_macd_range, 2.0)
            
            # Calcular score combinado
            price_strength = min(price_change_pct / 0.02, 2.0)  # 2% cambio de precio = fuerza 1.0
            combined_score = (price_strength + indicator_strength) / 2.0
            
            # Determinar fuerza y confianza
            if combined_score >= 1.5:
                strength = "strong"
                confidence = min(combined_score / 2.0, 0.95)
            elif combined_score >= 1.0:
                strength = "moderate" 
                confidence = min(combined_score / 1.5, 0.8)
            else:
                strength = "weak"
                confidence = min(combined_score, 0.6)
            
            return strength, confidence
            
        except Exception as e:
            logger.error(f"Error calculando fuerza de divergencia: {e}")
            return "weak", 0.3
    
    def analyze_divergences(self, symbol: str, timeframe_analysis: Dict) -> List[Divergence]:
        """
        Analiza divergencias para todos los timeframes - MEJORADO
        """
        all_divergences = []
        
        try:
            for tf_key, analysis in timeframe_analysis.items():
                if not tf_key.startswith('tf_'):
                    continue
                    
                timeframe = analysis['timeframe']
                
                # Verificar que tenemos dataframe
                if 'dataframe' not in analysis:
                    logger.warning(f"No hay dataframe para {timeframe}m")
                    continue
                
                df = analysis['dataframe']
                
                # Detectar divergencias RSI
                if len(df) >= 30:
                    # Calcular RSI si no está en el dataframe
                    if 'rsi' not in df.columns:
                        from indicators import indicators_calculator
                        df['rsi'] = indicators_calculator.calculate_rsi(df)
                    
                    rsi_divergences = self.detect_rsi_divergence(
                        df['close'], df['rsi'], timeframe
                    )
                    all_divergences.extend(rsi_divergences)
                
                # Detectar divergencias MACD
                if 'macd_histogram' in analysis and len(df) >= 30:
                    macd_histogram = pd.Series(analysis['macd_histogram'])
                    # Asegurar misma longitud
                    if len(macd_histogram) == len(df):
                        macd_divergences = self.detect_macd_divergence(
                            df['close'], macd_histogram, timeframe
                        )
                        all_divergences.extend(macd_divergences)
        
            # Ordenar por confianza (las más confiables primero)
            all_divergences.sort(key=lambda x: x.confidence, reverse=True)
            
            # Filtrar duplicados similares
            all_divergences = self._filter_duplicate_divergences(all_divergences)
            
            if all_divergences:
                strong_count = sum(1 for d in all_divergences if d.strength == 'strong')
                logger.info(f"✅ {len(all_divergences)} divergencias detectadas para {symbol} ({strong_count} fuertes)")
            else:
                logger.debug(f"ℹ️ No se detectaron divergencias significativas para {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error analizando divergencias para {symbol}: {e}")
        
        return all_divergences
    
    def _filter_duplicate_divergences(self, divergences: List[Divergence]) -> List[Divergence]:
        """Filtra divergencias muy similares"""
        filtered = []
        seen = set()
        
        for div in divergences:
            # Crear clave única basada en tipo, indicador y timeframe
            key = (div.type, div.indicator, div.timeframe)
            
            if key not in seen:
                filtered.append(div)
                seen.add(key)
            else:
                # Si ya existe una de este tipo, mantener la de mayor confianza
                existing = next(d for d in filtered if (d.type, d.indicator, d.timeframe) == key)
                if div.confidence > existing.confidence:
                    filtered.remove(existing)
                    filtered.append(div)
        
        return filtered

# Instancia global
divergence_detector = DivergenceDetector()