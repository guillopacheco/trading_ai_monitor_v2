"""
Funciones auxiliares para Trading AI Monitor v2 - PARSER ULTRA ROBUSTO
"""
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from config import LEVERAGE, RISK_PER_TRADE, ACCOUNT_BALANCE, MAX_POSITION_SIZE
import logging
from helpers import validate_signal_data  # Si está en el mismo archivo, no necesitas este import

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

def parse_signal_message(message_text: str) -> Optional[Dict[str, Any]]:
    """
    Parsea mensajes de señales - VERSIÓN ULTRA ROBUSTA PARA CUALQUIER FORMATO
    """
    try:
        signal_data = {}
        
        # ✅ CORRECCIÓN DEFINITIVA: Limpieza ultra-agresiva de asteriscos
        # Remover TODOS los asteriscos sin importar cuántos haya
        clean_text = re.sub(r'\*+', '', message_text)  # ✅ Esto removerá *, **, ***, etc.
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        # ✅ DEBUG: Log del texto limpio para ver qué está pasando
        logger.debug(f"🔧 Texto después de limpieza: {clean_text[:100]}")
        
        # ✅ MÉTODO MÁS ROBUSTO: Buscar el patrón #PAR/USDT directamente
        # Primero intentar el formato más común
        pair_match = re.search(r'#([A-Za-z0-9]+)/USDT', clean_text)
        if pair_match:
            pair = f"{pair_match.group(1)}/USDT"
        else:
            # Fallback: buscar cualquier par que termine en /USDT
            pair_match = re.search(r'([A-Za-z0-9]+)/USDT', clean_text)
            if pair_match:
                pair = pair_match.group(0)
            else:
                logger.error(f"❌ No se pudo encontrar par /USDT en: {clean_text[:100]}")
                return None
        
        signal_data['pair'] = pair.upper()
        
        # Extraer apalancamiento (x20)
        leverage_match = re.search(r'x(\d+)', clean_text)
        signal_data['leverage'] = int(leverage_match.group(1)) if leverage_match else LEVERAGE
        
        # Extraer dirección
        if 'Short' in clean_text or '📉' in clean_text:
            signal_data['direction'] = 'SHORT'
        elif 'Long' in clean_text or '📈' in clean_text:
            signal_data['direction'] = 'LONG'
        else:
            logger.warning("No se pudo determinar la dirección de la señal")
            return None
        
        # Extraer entry price con múltiples formatos
        entry_match = re.search(r'Entry\s*-\s*([0-9.]+)', clean_text)
        if entry_match:
            signal_data['entry'] = float(entry_match.group(1))
        else:
            # Intentar otros formatos de entry
            entry_alt = re.search(r'Entry[:\s]*([0-9.]+)', clean_text)
            if entry_alt:
                signal_data['entry'] = float(entry_alt.group(1))
            else:
                logger.warning("No se pudo extraer el precio de entrada")
                return None
        
        # Extraer take profits
        tp_matches = re.findall(r'[🥉🥈🥇🚀]\s*([0-9.]+)\s*\(([0-9]+)%', clean_text)
        
        if len(tp_matches) >= 4:
            tp_matches.sort(key=lambda x: int(x[1]))
            signal_data['tp1'] = float(tp_matches[0][0])
            signal_data['tp2'] = float(tp_matches[1][0])
            signal_data['tp3'] = float(tp_matches[2][0])
            signal_data['tp4'] = float(tp_matches[3][0])
            signal_data['tp1_percent'] = int(tp_matches[0][1])
            signal_data['tp2_percent'] = int(tp_matches[1][1])
            signal_data['tp3_percent'] = int(tp_matches[2][1])
            signal_data['tp4_percent'] = int(tp_matches[3][1])
        else:
            # Fallback: buscar TPs sin porcentajes
            tp_matches = re.findall(r'[🥉🥈🥇🚀]\s*([0-9.]+)', clean_text)
            if len(tp_matches) >= 4:
                signal_data['tp1'] = float(tp_matches[0])
                signal_data['tp2'] = float(tp_matches[1])
                signal_data['tp3'] = float(tp_matches[2])
                signal_data['tp4'] = float(tp_matches[3])
                signal_data['tp1_percent'] = 40
                signal_data['tp2_percent'] = 60
                signal_data['tp3_percent'] = 80
                signal_data['tp4_percent'] = 100
            else:
                logger.warning(f"Solo se encontraron {len(tp_matches)} take profits")
                return None
        
        # Validar la señal
        if not validate_signal_data(signal_data):
            logger.error("Señal no pasó validación")
            return None
        
        # Metadata adicional
        signal_data['timestamp'] = datetime.now()
        signal_data['message_text'] = message_text
        signal_data['parsed_successfully'] = True
        
        logger.info(f"✅ Señal parseada CORRECTAMENTE: {signal_data['pair']} {signal_data['direction']} @ {signal_data['entry']} (x{signal_data['leverage']})")
        
        # ✅ AGREGAR AL FINAL DEL TRY, ANTES DEL RETURN:
        if signal_data:
            # Registrar actividad para health monitor
            try:
                from health_monitor import health_monitor
                health_monitor.record_telegram_activity()
            except Exception as e:
                logger.debug(f"No se pudo registrar actividad en health monitor: {e}")
        
        return signal_data  # ✅ SOLO UN RETURN AQUÍ
        
    except Exception as e:
        logger.error(f"❌ Error parseando señal: {e}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error parseando señal: {e}")
        logger.error(f"📝 Mensaje completo: {message_text}")
        return None
    
def validate_signal_data(signal_data: Dict) -> bool:
    """
    Valida que los datos de la señal sean consistentes
    """
    try:
        required_fields = ['pair', 'direction', 'entry', 'tp1', 'tp2', 'tp3', 'tp4', 'leverage']
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in signal_data:
                logger.error(f"Campo requerido faltante: {field}")
                return False
        
        # Validar dirección
        if signal_data['direction'] not in ['LONG', 'SHORT']:
            logger.error(f"Dirección inválida: {signal_data['direction']}")
            return False
        
        # Validar apalancamiento
        if not isinstance(signal_data['leverage'], int) or signal_data['leverage'] <= 0:
            logger.error(f"Apalancamiento inválido: {signal_data['leverage']}")
            return False
        
        # Validar que los precios sean números positivos
        price_fields = ['entry', 'tp1', 'tp2', 'tp3', 'tp4']
        for field in price_fields:
            if not isinstance(signal_data[field], (int, float)) or signal_data[field] <= 0:
                logger.error(f"Precio inválido en {field}: {signal_data[field]}")
                return False
        
        # Validar que los TPs estén en el orden correcto según dirección
        tps = [signal_data['tp1'], signal_data['tp2'], signal_data['tp3'], signal_data['tp4']]
        
        if signal_data['direction'] == 'LONG':
            # Para LONG: TPs deben ser mayores que entry
            if not all(tp > signal_data['entry'] for tp in tps):
                logger.error("Para LONG, todos los TPs deben ser mayores que el entry")
                return False
            # Deben estar en orden ascendente
            if not all(tps[i] < tps[i+1] for i in range(len(tps)-1)):
                logger.error("TPs para LONG deben estar en orden ascendente")
                return False
        else:  # SHORT
            # Para SHORT: TPs deben ser menores que entry
            if not all(tp < signal_data['entry'] for tp in tps):
                logger.error("Para SHORT, todos los TPs deben ser menores que el entry")
                return False
            # Deben estar en orden descendente
            if not all(tps[i] > tps[i+1] for i in range(len(tps)-1)):
                logger.error("TPs para SHORT deben estar en orden descendente")
                return False
        
        # Validar formato del par
        if not re.match(r'^[A-Z0-9]+/[A-Z0-9]+$', signal_data['pair']):
            logger.error(f"Formato de par inválido: {signal_data['pair']}")
            return False
        
        logger.debug(f"✅ Señal validada correctamente: {signal_data['pair']} (x{signal_data['leverage']})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validando señal: {e}")
        return False

def calculate_position_size(entry_price: float, stop_loss: float, 
                          account_balance: float = ACCOUNT_BALANCE, 
                          risk_per_trade: float = RISK_PER_TRADE,
                          leverage: int = LEVERAGE,
                          max_position_size: float = MAX_POSITION_SIZE) -> Dict[str, float]:
    """
    Calcula el tamaño de posición considerando apalancamiento
    """
    try:
        # Calcular riesgo en precio
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk <= 0:
            return {
                'position_size': 0,
                'dollar_risk': 0,
                'risk_reward_ratio': 0,
                'leverage_used': leverage,
                'error': 'Riesgo de precio inválido'
            }
        
        # Calcular riesgo en dinero (2% del balance)
        dollar_risk = account_balance * risk_per_trade
        
        # Calcular tamaño de posición base (sin leverage)
        position_size_base = dollar_risk / price_risk
        
        # Aplicar apalancamiento
        position_size_leveraged = position_size_base * leverage
        
        # Aplicar límite máximo de posición (10% del balance con leverage)
        max_position = account_balance * max_position_size * leverage
        final_position_size = min(position_size_leveraged, max_position)
        
        # Calcular riesgo real considerando leverage
        real_risk_pct = (price_risk / entry_price) * leverage * 100
        
        return {
            'position_size': round(final_position_size, 2),
            'dollar_risk': round(dollar_risk, 2),
            'risk_reward_ratio': round(real_risk_pct, 2),
            'leverage_used': leverage,
            'real_risk_percent': round(real_risk_pct, 2),
            'max_position_allowed': round(max_position, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculando tamaño de posición: {e}")
        return {
            'position_size': 0,
            'dollar_risk': 0,
            'risk_reward_ratio': 0,
            'leverage_used': leverage,
            'error': str(e)
        }

def calculate_atr_multiplier(atr_value: float, base_atr: float = 0.02) -> float:
    """
    Calcula multiplicador para SL basado en ATR
    """
    try:
        if atr_value <= 0:
            return 1.0
            
        volatility_ratio = atr_value / base_atr
        
        if volatility_ratio <= 1.2:
            return 1.0  # Volatilidad normal
        elif volatility_ratio <= 1.5:
            return 1.3  # Volatilidad moderada
        elif volatility_ratio <= 2.0:
            return 1.7  # Volatilidad alta
        else:
            return 2.0  # Volatilidad muy alta
            
    except Exception as e:
        logger.error(f"Error calculando ATR multiplier: {e}")
        return 1.0

def should_review_frequently(atr_value: float, base_atr: float = 0.02) -> bool:
    """
    Determina si se debe revisar frecuentemente (cada 5min) por alta volatilidad
    """
    try:
        return atr_value > base_atr * 1.5
    except Exception as e:
        logger.error(f"Error determinando frecuencia de revisión: {e}")
        return False

def format_telegram_message(signal_data: Dict, analysis_result: Dict) -> str:
    """
    Formatea mensaje para Telegram con emojis y estructura clara
    """
    try:
        pair = signal_data.get('pair', 'N/A')
        direction = signal_data.get('direction', 'N/A')
        leverage = signal_data.get('leverage', LEVERAGE)
        
        # Emojis según dirección
        direction_emoji = "📉" if direction == "SHORT" else "📈"
        
        # Obtener análisis por timeframe
        timeframe_analysis = ""
        for tf in ['1', '5', '15']:
            trend_key = f'trend_{tf}m'
            trend = analysis_result.get(trend_key, 'N/A')
            emoji = "🟢" if trend == "ALCISTA" else "🔴" if trend == "BAJISTA" else "⚪"
            timeframe_analysis += f"{emoji} {tf}m: {trend}\n"
        
        # Información de gestión de riesgo
        risk_info = ""
        if analysis_result.get('position_size'):
            risk_info = f"""
**Gestión de Riesgo (x{leverage}):**
💰 Tamaño posición: {analysis_result.get('position_size', 'N/A')} USDT
🎯 Stop Loss: {analysis_result.get('stop_loss', 'N/A')}
📊 Riesgo/Operación: {analysis_result.get('dollar_risk', 'N/A')} USDT ({RISK_PER_TRADE*100}%)
⚡ Riesgo Real: {analysis_result.get('real_risk_percent', 'N/A')}% (con leverage)
"""
        
        message = f"""
🎯 **ANÁLISIS DE SEÑAL - {pair}** {direction_emoji}

**Señal Original:**
- Par: {pair}
- Dirección: {direction}
- Apalancamiento: x{leverage}
- Entry: {signal_data.get('entry', 'N/A')}

**Take Profits:**
🥉 TP1 ({signal_data.get('tp1_percent', 40)}%): {signal_data.get('tp1', 'N/A')}
🥈 TP2 ({signal_data.get('tp2_percent', 60)}%): {signal_data.get('tp2', 'N/A')}  
🥇 TP3 ({signal_data.get('tp3_percent', 80)}%): {signal_data.get('tp3', 'N/A')}
🚀 TP4 ({signal_data.get('tp4_percent', 100)}%): {signal_data.get('tp4', 'N/A')}

**Análisis Técnico:**
{timeframe_analysis.strip()}

**Indicadores Consolidados:**
📈 Tendencia: {analysis_result.get('predominant_trend', 'N/A')}
⚡ RSI Promedio: {analysis_result.get('avg_rsi', 'N/A')}
🔍 MACD: {analysis_result.get('predominant_macd', 'N/A')}
🌊 Volatilidad: {analysis_result.get('max_atr_multiplier', 'N/A')}x

**Confirmación:**
🔄 Estado: {analysis_result.get('confirmation_status', 'N/A')}
🎯 Coincidencia: {analysis_result.get('match_percentage', 'N/A')}%
💪 Confianza: {analysis_result.get('confidence', 'N/A')}
{risk_info.strip()}

**Recomendación:** {analysis_result.get('recommendation_action', 'N/A')}
"""
        
        # Agregar alerta de divergencia si existe
        if analysis_result.get('divergence_detected') == 'Sí':
            divergence_type = analysis_result.get('divergence_type', '')
            message += f"\n\n⚠️ **ALERTA DE DIVERGENCIA** ⚠️\n{divergence_type}"
        
        return message.strip()
        
    except Exception as e:
        logger.error(f"Error formateando mensaje de Telegram: {e}")
        return f"📊 Análisis para {signal_data.get('pair', 'N/A')} - Error formateando detalles"

def calculate_time_until_review(volatility_high: bool, confirmation_status: str = None) -> int:
    """
    Calcula tiempo hasta próximo re-análisis basado en volatilidad y estado
    """
    try:
        base_interval = 300 if volatility_high else 900  # 5min o 15min
        
        # Ajustar según estado de confirmación
        if confirmation_status:
            if confirmation_status in ["DÉBILMENTE CONFIRMADA", "NO CONFIRMADA"]:
                # Revisar más frecuentemente señales no confirmadas
                return min(base_interval, 600)  # Máximo 10 minutos
            elif confirmation_status == "CONFIRMADA":
                # Señales confirmadas pueden esperar más
                return min(base_interval + 300, 1800)  # Máximo 30 minutos
        
        return base_interval
        
    except Exception as e:
        logger.error(f"Error calculando tiempo de revisión: {e}")
        return 900  # Default 15 minutos

def extract_price_levels(message_text: str) -> List[float]:
    """
    Extrae todos los niveles de precio de un mensaje
    """
    try:
        # Encontrar todos los números decimales
        price_matches = re.findall(r'(\d+\.\d+)', message_text)
        prices = []
        
        for match in price_matches:
            try:
                price = float(match)
                # Filtrar precios razonables (asumiendo trading crypto)
                if 0.000001 <= price <= 100000:
                    prices.append(price)
            except ValueError:
                continue
        
        return sorted(list(set(prices)))  # Ordenar y eliminar duplicados
        
    except Exception as e:
        logger.error(f"Error extrayendo niveles de precio: {e}")
        return []

def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profits: List[float]) -> Dict[str, float]:
    """
    Calcula ratios de riesgo/recompensa para cada TP
    """
    try:
        if not take_profits:
            return {}
        
        risk = abs(entry - stop_loss)
        if risk == 0:
            return {}
        
        ratios = {}
        for i, tp in enumerate(take_profits, 1):
            reward = abs(tp - entry)
            rr_ratio = reward / risk
            ratios[f'tp{i}_rr'] = round(rr_ratio, 2)
        
        return ratios
        
    except Exception as e:
        logger.error(f"Error calculando ratios riesgo/recompensa: {e}")
        return {}

if __name__ == "__main__":
    # Test del parser ultra robusto
    test_messages = [
        """🔥 **#CLANKER**/USDT (Short📉, x20) 🔥
Entry - 50.64
Take-Profit:
🥉 49.6272 (40% of profit)
🥈 49.1208 (60% of profit)
🥇 48.6144 (80% of profit)
🚀 48.108 (100% of profit)""",
        
        """🔥 **#PIPPIN**/USDT (Long📈, x20) 🔥
Entry - 0.0247
Take-Profit:
🥉 0.02519 (40% of profit)
🥈 0.02544 (60% of profit)
🥇 0.02569 (80% of profit)
🚀 0.02593 (100% of profit)""",
        
        """🔥 #LIGHT/USDT (Long📈, x20) 🔥
Entry - 2.3868
Take-Profit:
🥉 2.4345 (40% of profit)
🥈 2.4584 (60% of profit)
🥇 2.4823 (80% of profit)
🚀 2.5061 (100% of profit)"""
    ]
    
    print("🧪 Testeando parser ULTRA ROBUSTO...")
    
    for i, test_msg in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        parsed = parse_signal_message(test_msg)
        if parsed:
            print(f"✅ Parseado: {parsed['pair']} {parsed['direction']} @ {parsed['entry']} (x{parsed['leverage']})")
            print(f"   TPs: {parsed['tp1']} ({parsed['tp1_percent']}%), {parsed['tp2']} ({parsed['tp2_percent']}%), {parsed['tp3']} ({parsed['tp3_percent']}%), {parsed['tp4']} ({parsed['tp4_percent']}%)")
        else:
            print("❌ No se pudo parsear el mensaje")