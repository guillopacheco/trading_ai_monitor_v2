# indicators.py - MODIFICACIONES
"""
Módulo para cálculo de indicadores técnicos usando datos de Bybit - ACTUALIZADO CON PANDAS-TA
"""
import pandas as pd
import numpy as np
import requests
import logging
from typing import Dict, List, Optional, Tuple
from config import *
import pandas_ta as ta  # CAMBIADO: usar pandas_ta en lugar de ta

# ✅ NUEVO IMPORT
from symbol_utils import normalize_symbol, check_symbol_availability

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Clase para cálculo de indicadores técnicos - ACTUALIZADO CON PANDAS-TA"""
    
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        
    def get_ohlcv_data(self, symbol: str, interval: str = "5", limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtiene datos OHLCV de Bybit - CORREGIDO CON NORMALIZACIÓN
        """
        try:
            # ✅ CORRECCIÓN: Normalizar símbolo y determinar categoría
            symbol_info = check_symbol_availability(symbol)
            normalized_symbol = symbol_info['linear_symbol']
            category = symbol_info['recommended_category']
            
            url = f"{self.base_url}/v5/market/kline"
            params = {
                'category': category,  # ✅ Usar categoría dinámica
                'symbol': normalized_symbol,
                'interval': interval,
                'limit': limit
            }
            
            logger.info(f"🔍 Obteniendo datos para {symbol} -> {normalized_symbol} ({category})")
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if data['retCode'] != 0:
                logger.error(f"Bybit API error: {data['retMsg']}")
                return None
                
            # Procesar los datos
            candles = data['result']['list']
            if not candles:
                logger.warning(f"No hay datos disponibles para {symbol} ({normalized_symbol}) en {interval}m")
                return None
                
            df = pd.DataFrame(candles, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # Convertir tipos de datos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Validar que tenemos datos suficientes
            if len(df) < 30:
                logger.warning(f"Datos insuficientes para {symbol}: {len(df)} velas")
                return None
                
            # Limpiar NaN values
            df = df.dropna()
            
            logger.info(f"✅ Datos OHLCV obtenidos: {symbol} -> {normalized_symbol} {interval}m - {len(df)} velas")
            return df
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout obteniendo datos de Bybit para {symbol}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Bybit para {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado obteniendo datos de Bybit para {symbol}: {e}")
            return None
    
    def calculate_ema(self, df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """Calcula EMA usando pandas_ta"""
        try:
            ema = ta.ema(df[column], length=period)
            if ema is not None:
                return ema
            else:
                # Fallback a cálculo manual si pandas-ta falla
                return df[column].ewm(span=period, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculando EMA{period}: {e}")
            return df[column].ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula RSI usando pandas_ta"""
        try:
            rsi = ta.rsi(df['close'], length=period)
            if rsi is not None:
                return rsi
            else:
                return pd.Series([50.0] * len(df))  # Valor neutro como fallback
        except Exception as e:
            logger.error(f"Error calculando RSI{period}: {e}")
            return pd.Series([50.0] * len(df))
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD usando pandas_ta"""
        try:
            macd_data = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            if macd_data is not None:
                # pandas_ta retorna un DataFrame con múltiples columnas
                macd_line = macd_data.get(f'MACD_{fast}_{slow}_{signal}')
                signal_line = macd_data.get(f'MACDs_{fast}_{slow}_{signal}') 
                histogram = macd_data.get(f'MACDh_{fast}_{slow}_{signal}')
                
                if macd_line is not None and signal_line is not None and histogram is not None:
                    return macd_line, signal_line, histogram
                
            # Fallback si pandas_ta no retorna los datos esperados
            empty_series = pd.Series([0.0] * len(df))
            return empty_series, empty_series, empty_series
            
        except Exception as e:
            logger.error(f"Error calculando MACD: {e}")
            empty_series = pd.Series([0.0] * len(df))
            return empty_series, empty_series, empty_series
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula ATR usando pandas_ta"""
        try:
            atr = ta.atr(df['high'], df['low'], df['close'], length=period)
            if atr is not None:
                return atr
            else:
                return pd.Series([np.nan] * len(df))
        except Exception as e:
            logger.error(f"Error calculando ATR{period}: {e}")
            return pd.Series([np.nan] * len(df))
    
    def analyze_timeframe(self, symbol: str, timeframe: str) -> Optional[Dict[str, any]]:
        """
        Analiza un timeframe específico con todos los indicadores - ACTUALIZADO
        """
        try:
            df = self.get_ohlcv_data(symbol, timeframe, 100)
            if df is None or len(df) < 20:
                logger.warning(f"Datos insuficientes para {symbol} en {timeframe}m")
                return None
            
            # Calcular indicadores CON PANDAS-TA
            ema_short = self.calculate_ema(df, EMA_SHORT_PERIOD)
            ema_long = self.calculate_ema(df, EMA_LONG_PERIOD)
            rsi = self.calculate_rsi(df)
            macd_line, signal_line, histogram = self.calculate_macd(df)
            atr = self.calculate_atr(df)
            
            # Validar que tenemos datos válidos
            if any(series.isna().iloc[-1] if series is not None else True 
                   for series in [ema_short, ema_long, rsi, macd_line, atr]):
                logger.warning(f"Indicadores con NaN para {symbol} en {timeframe}m")
                return None
            
            # Obtener últimos valores
            current_ema_short = ema_short.iloc[-1] if ema_short is not None else 0
            current_ema_long = ema_long.iloc[-1] if ema_long is not None else 0
            current_rsi = rsi.iloc[-1] if rsi is not None else 50
            current_macd = macd_line.iloc[-1] if macd_line is not None else 0
            current_signal = signal_line.iloc[-1] if signal_line is not None else 0
            current_histogram = histogram.iloc[-1] if histogram is not None else 0
            current_atr = atr.iloc[-1] if atr is not None else 0
            current_close = df['close'].iloc[-1]
            
            # Determinar tendencia EMA
            if current_ema_short > current_ema_long:
                ema_trend = "ALCISTA"
            else:
                ema_trend = "BAJISTA"
            
            # Determinar señal MACD
            if current_macd > current_signal and current_histogram > 0:
                macd_signal = "ALCISTA"
            elif current_macd < current_signal and current_histogram < 0:
                macd_signal = "BAJISTA"
            else:
                macd_signal = "NEUTRO"
            
            # Estado RSI
            if current_rsi > RSI_OVERBOUGHT:
                rsi_status = "SOBRECOMPRA"
            elif current_rsi < RSI_OVERSOLD:
                rsi_status = "SOBREVENTA"
            else:
                rsi_status = "NEUTRO"
            
            # Estado ATR (volatilidad) - MEJORADO
            atr_multiplier, atr_status = self._calculate_volatility_status(current_atr, current_close, df)
            
            result = {
                'timeframe': timeframe,
                'close_price': current_close,
                'ema_trend': ema_trend,
                'ema_short': current_ema_short,
                'ema_long': current_ema_long,
                'rsi': round(current_rsi, 2),
                'rsi_status': rsi_status,
                'macd_signal': macd_signal,
                'macd_line': round(current_macd, 6),
                'macd_signal_line': round(current_signal, 6),
                'macd_histogram': round(current_histogram, 6),
                'atr': current_atr,
                'atr_status': atr_status,
                'atr_multiplier': atr_multiplier,
                'dataframe': df,  # Para análisis de divergencias
                'analysis_timestamp': pd.Timestamp.now().isoformat()
            }
            
            logger.debug(f"✅ Análisis {symbol} {timeframe}m: {ema_trend}, RSI: {current_rsi:.1f}, ATRx: {atr_multiplier:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analizando {symbol} en {timeframe}m: {e}")
            return None
    
    def _calculate_volatility_status(self, current_atr: float, current_price: float, df: pd.DataFrame) -> Tuple[float, str]:
        """
        Calcula estado de volatilidad basado en ATR histórico - MEJORADO
        """
        try:
            # Calcular ATR histórico para comparación
            historical_atr = self.calculate_atr(df, ATR_PERIOD)
            
            if historical_atr is None or historical_atr.isna().all():
                return 1.0, "VOLATILIDAD DESCONOCIDA"
            
            recent_atr = historical_atr.tail(30)  # Últimos 30 periodos
            
            if recent_atr.isna().all():
                return 1.0, "VOLATILIDAD DESCONOCIDA"
            
            # Calcular percentiles
            p25 = recent_atr.quantile(0.25)
            p75 = recent_atr.quantile(0.75)
            median_atr = recent_atr.median()
            
            # Determinar multiplicador y estado
            if current_atr <= p25:
                multiplier = 0.8
                status = "BAJA VOLATILIDAD"
            elif current_atr <= median_atr:
                multiplier = 1.0
                status = "VOLATILIDAD NORMAL-BAJA"
            elif current_atr <= p75:
                multiplier = 1.3
                status = "VOLATILIDAD NORMAL-ALTA"
            else:
                multiplier = 1.7
                status = "ALTA VOLATILIDAD"
            
            # Ajuste adicional basado en desviación extrema
            if current_atr > p75 * 1.5:
                multiplier = 2.0
                status = "MUY ALTA VOLATILIDAD"
                
            return multiplier, status
            
        except Exception as e:
            logger.error(f"Error calculando estado de volatilidad: {e}")
            return 1.0, "VOLATILIDAD NORMAL"
    
    def analyze_all_timeframes(self, symbol: str) -> Dict[str, any]:
        """
        Analiza todas las temporalidades configuradas - MEJORADO
        """
        results = {}
        successful_analyses = 0
        
        for timeframe in DEFAULT_TIMEFRAMES:
            result = self.analyze_timeframe(symbol, timeframe)
            if result:
                results[f"tf_{timeframe}"] = result
                successful_analyses += 1
            else:
                logger.warning(f"❌ No se pudo analizar {symbol} en {timeframe}m")
        
        # Análisis consolidado solo si tenemos al menos un timeframe
        if successful_analyses > 0:
            results['consolidated'] = self._consolidate_analysis(results)
            logger.info(f"✅ Análisis completado para {symbol}: {successful_analyses}/{len(DEFAULT_TIMEFRAMES)} timeframes")
        else:
            logger.error(f"❌ No se pudo analizar ningún timeframe para {symbol}")
            return {}
        
        return results
    
    def _consolidate_analysis(self, timeframe_results: Dict) -> Dict[str, any]:
        """Consolida análisis de múltiples temporalidades - MEJORADO"""
        trends = []
        rsi_values = []
        macd_signals = []
        atr_multipliers = []
        
        for tf_key, analysis in timeframe_results.items():
            if tf_key != 'consolidated':
                trends.append(analysis['ema_trend'])
                rsi_values.append(analysis['rsi'])
                macd_signals.append(analysis['macd_signal'])
                atr_multipliers.append(analysis['atr_multiplier'])
        
        if not trends:  # Validar que hay datos
            return {
                'predominant_trend': 'NEUTRO',
                'avg_rsi': 50.0,
                'predominant_macd': 'NEUTRO',
                'max_atr_multiplier': 1.0,
                'timeframes_analyzed': 0,
                'consolidation_quality': 'BAJA'
            }
        
        # Tendencia predominante
        trend_counts = {trend: trends.count(trend) for trend in set(trends)}
        predominant_trend = max(trend_counts.items(), key=lambda x: x[1])[0]
        
        # RSI promedio
        avg_rsi = sum(rsi_values) / len(rsi_values)
        
        # MACD predominante
        macd_counts = {signal: macd_signals.count(signal) for signal in set(macd_signals)}
        predominant_macd = max(macd_counts.items(), key=lambda x: x[1])[0]
        
        # Mayor multiplicador ATR (peor caso)
        max_atr_multiplier = max(atr_multipliers)
        
        # Calidad del análisis consolidado
        quality = "ALTA" if len(trends) >= 2 else "MEDIA" if len(trends) == 1 else "BAJA"
        
        return {
            'predominant_trend': predominant_trend,
            'avg_rsi': round(avg_rsi, 2),
            'predominant_macd': predominant_macd,
            'max_atr_multiplier': max_atr_multiplier,
            'timeframes_analyzed': len(timeframe_results) - 1,
            'consolidation_quality': quality,
            'trend_consistency': f"{trend_counts.get(predominant_trend, 0)}/{len(trends)}"
        }

# Instancia global
indicators_calculator = TechnicalIndicators()

if __name__ == "__main__":
    # Test del módulo actualizado
    test_symbol = "BTCUSDT"
    analysis = indicators_calculator.analyze_all_timeframes(test_symbol)
    print(f"✅ Test indicators para {test_symbol}:")
    for key, value in analysis.items():
        if key != 'consolidated':
            print(f"   {key}: {value.get('ema_trend', 'N/A')}, RSI: {value.get('rsi', 'N/A')}")
        else:
            print(f"   {key}: {value}")