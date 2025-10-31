"""
Helpers y utilities para el Trading Bot - CORREGIDO SIN CIRCULAR IMPORTS
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_signal_message(message_text: str) -> Optional[Dict]:
    """
    Parsea mensajes de señal de trading - OPTIMIZADO PARA ANDY INSIDER
    """
    try:
        if not message_text or len(message_text.strip()) < 10:
            return None
        
        logger.debug(f"📨 Mensaje original: {message_text[:200]}...")
        
        # Limpieza agresiva de formato Markdown y emojis
        clean_text = re.sub(r'\*+', '', message_text)  # Elimina **
        clean_text = re.sub(r'`', '', clean_text)      # Elimina `
        clean_text = re.sub(r'[🔥🎯📈📉⚡️️🟢🔴🟡🟠🔵🟣🟤⚫⚪]', '', clean_text)  # Elimina emojis comunes
        clean_text = clean_text.replace('$', '').replace('/', ' / ')  # Normaliza separadores
        
        logger.debug(f"🔧 Texto limpio: {clean_text[:200]}...")
        
        # PATRONES ESPECÍFICOS PARA ANDY INSIDER
        patterns = [
            # Patrón 1: Formato con par entre ** y dirección con emoji
            r'\*{0,2}#?(\w+)\*{0,2}.*?\/?USDT.*?(LONG|SHORT).*?x(\d+)',
            
            # Patrón 2: Formato con emojis de dirección
            r'#?(\w+).*?\/?USDT.*?(LONG|SHORT)[📈📉].*?x(\d+)',
            
            # Patrón 3: Formato con entry explícito
            r'#?(\w+).*?(LONG|SHORT).*?[Ee]ntr[yi][\s:\-]*(\d+\.?\d*)',
            
            # Patrón 4: Formato simple con par y dirección
            r'#?(\w+).*?\/?USDT.*?(LONG|SHORT)',
            
            # Patrón 5: Formato alternativo
            r'(\w+)\s+(LONG|SHORT)\s+(\d+\.?\d*)'
        ]
        
        pair = None
        direction = None
        leverage = 20  # Default
        entry_price = None
        stop_loss = None
        take_profits = []
        
        # Buscar patrón que coincida
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, clean_text, re.IGNORECASE | re.DOTALL)
            if match:
                logger.debug(f"🎯 Patrón {i+1} coincidió: {match.groups()}")
                
                # Extraer información básica según el patrón
                if i == 0:  # Patrón 1: **#PAR**/USDT (Direction📈, x20)
                    pair = match.group(1).upper() + 'USDT'
                    direction = match.group(2).upper()
                    leverage = int(match.group(3))
                elif i == 1:  # Patrón 2: #PAR/USDT Direction📈 x20
                    pair = match.group(1).upper() + 'USDT'
                    direction = match.group(2).upper()
                    leverage = int(match.group(3))
                elif i == 2:  # Patrón 3: Con entry explícito
                    pair = match.group(1).upper() + 'USDT'
                    direction = match.group(2).upper()
                    entry_price = float(match.group(3))
                elif i == 3:  # Patrón 4: Solo par y dirección
                    pair = match.group(1).upper() + 'USDT'
                    direction = match.group(2).upper()
                elif i == 4:  # Patrón 5: Formato simple
                    pair = match.group(1).upper() + 'USDT'
                    direction = match.group(2).upper()
                    entry_price = float(match.group(3))
                
                break
        
        if not pair or not direction:
            logger.warning("❌ No se pudo extraer par o dirección")
            return None
        
        # EXTRACCIÓN DE PRECIOS - MÁS ROBUSTA
        price_patterns = [
            r'[Ee]ntr[yi][\s:\-]*(\d+\.?\d*)',                    # Entry: 1.538
            r'[Ee]ntr[yi][\s\-]*(\d+\.?\d*)',                     # Entry - 1.538
            r'[Pp]rice[\s:\-]*(\d+\.?\d*)',                       # Price - 9.054
            r'(\d+\.\d{3,})',                                     # Números con 3+ decimales
            r'(\d+\.\d+)',                                        # Números con decimales
        ]
        
        # Buscar entry price
        if not entry_price:
            for price_pattern in price_patterns:
                price_match = re.search(price_pattern, clean_text)
                if price_match:
                    try:
                        entry_price = float(price_match.group(1))
                        logger.debug(f"💰 Entry price encontrado: {entry_price}")
                        break
                    except (ValueError, IndexError):
                        continue
        
        # Buscar take profits
        tp_patterns = [
            r'[Tt]ake[-\\s]?[Pp]rofit[:\s]*([\d\.\s\/]+)',        # Take-Profit: 1.5072 / 1.4919
            r'[Tt][Pp][:\s]*([\d\.\s\/]+)',                       # TP: 1.5072 / 1.4919
            r'🥉\s*(\d+\.?\d*).*?🥈\s*(\d+\.?\d*)',              # Emojis de medallas
            r'(\d+\.\d+)\s*\([^)]*\)',                           # 1.5072 (40% of profit)
        ]
        
        for tp_pattern in tp_patterns:
            tp_match = re.search(tp_pattern, clean_text)
            if tp_match:
                try:
                    # Manejar múltiples formatos de take profits
                    if len(tp_match.groups()) > 1:
                        # Múltiples TPs en grupos separados
                        for group in tp_match.groups():
                            if group:
                                take_profits.append(float(group))
                    else:
                        # TPs en formato 1.5072/1.4919
                        tps_text = tp_match.group(1)
                        for tp in re.findall(r'\d+\.\d+', tps_text):
                            take_profits.append(float(tp))
                    
                    logger.debug(f"🎯 Take profits encontrados: {take_profits}")
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"⚠️ Error parseando TPs: {e}")
                    continue
        
        # CALCULAR STOP LOSS si no se encontró
        if entry_price and not stop_loss:
            if direction == 'LONG':
                stop_loss = entry_price * 0.98  # -2% para LONG
            else:  # SHORT
                stop_loss = entry_price * 1.02  # +2% para SHORT
            logger.debug(f"🛑 Stop loss calculado: {stop_loss}")
        
        # Si no se encontraron take profits, calcular algunos
        if entry_price and not take_profits:
            if direction == 'LONG':
                take_profits = [
                    entry_price * 1.02,  # +2%
                    entry_price * 1.04,  # +4%
                    entry_price * 1.06   # +6%
                ]
            else:  # SHORT
                take_profits = [
                    entry_price * 0.98,  # -2%
                    entry_price * 0.96,  # -4%
                    entry_price * 0.94   # -6%
                ]
            logger.debug(f"🎯 Take profits calculados: {take_profits}")
        
        # Validar que tenemos los datos mínimos
        if not entry_price:
            logger.warning("⚠️ No se pudo determinar entry price, usando fallback")
            # Podríamos obtener el precio actual desde Bybit aquí
            entry_price = 1.0  # Fallback
        
        # ✅ CORREGIDO: Nombres de campos actualizados
        signal_data = {
            'pair': pair,
            'direction': direction,
            'entry': entry_price,  # ✅ Cambiado de 'entry_price' a 'entry'
            'stop_loss': stop_loss,
            'take_profits': take_profits,  # ✅ Cambiado de 'take_profit' a 'take_profits'
            'leverage': leverage,
            'timestamp': datetime.now(),
            'message_text': message_text[:500],  # ✅ Cambiado de 'raw_message' a 'message_text'
            'source': 'andy_insider'
        }
        
        logger.info(f"✅ Señal parseada: {pair} {direction} @ {entry_price} "
                   f"SL: {stop_loss} TP: {take_profits} Leverage: {leverage}x")
        
        return signal_data
        
    except Exception as e:
        logger.error(f"💥 Error parseando señal: {e}")
        logger.debug(f"Mensaje problemático: {message_text}")
        return None

def validate_signal_data(signal_data: Dict) -> Tuple[bool, str]:
    """
    Valida los datos de una señal de trading - CORREGIDO
    """
    try:
        if not signal_data:
            return False, "Datos de señal vacíos"
        
        # ✅ CORREGIDO: Usar los nombres correctos de campos
        required_fields = ['pair', 'direction', 'entry', 'stop_loss', 'take_profits']
        for field in required_fields:
            if field not in signal_data:
                return False, f"Campo requerido faltante: {field}"
        
        # Validar pair
        pair = signal_data['pair']
        if not isinstance(pair, str) or len(pair) < 4 or 'USDT' not in pair:
            return False, f"Par inválido: {pair}"
        
        # Validar dirección
        direction = signal_data['direction']
        if direction not in ['LONG', 'SHORT']:
            return False, f"Dirección inválida: {direction}"
        
        # ✅ CORREGIDO: Usar nombres actualizados
        entry = signal_data['entry']
        stop_loss = signal_data['stop_loss']
        take_profits = signal_data['take_profits']
        
        if not isinstance(entry, (int, float)) or entry <= 0:
            return False, f"Precio de entrada inválido: {entry}"
        
        if not isinstance(stop_loss, (int, float)) or stop_loss <= 0:
            return False, f"Stop loss inválido: {stop_loss}"
        
        if not isinstance(take_profits, list) or not take_profits:
            return False, "Take profits inválidos"
        
        for tp in take_profits:
            if not isinstance(tp, (int, float)) or tp <= 0:
                return False, f"Take profit inválido: {tp}"
        
        # Validar leverage
        leverage = signal_data.get('leverage', 20)
        if not isinstance(leverage, int) or leverage < 1 or leverage > 100:
            return False, f"Leverage inválido: {leverage}"
        
        # Validar lógica de precios
        if direction == 'LONG':
            if stop_loss >= entry:
                return False, "Stop loss debe ser menor que entry en LONG"
            if any(tp <= entry for tp in take_profits):
                return False, "Take profits deben ser mayores que entry en LONG"
        else:  # SHORT
            if stop_loss <= entry:
                return False, "Stop loss debe ser mayor que entry en SHORT"
            if any(tp >= entry for tp in take_profits):
                return False, "Take profits deben ser menores que entry en SHORT"
        
        return True, "Señal válida"
        
    except Exception as e:
        return False, f"Error en validación: {str(e)}"

def format_telegram_message(signal_data: Dict, analysis_summary: Dict) -> str:
    """
    Formatea mensaje para Telegram con análisis completo
    """
    try:
        pair = signal_data.get('pair', 'N/A')
        direction = signal_data.get('direction', 'N/A')
        leverage = signal_data.get('leverage', 20)
        entry = signal_data.get('entry', 'N/A')  # ✅ Usar 'entry' en lugar de 'entry_price'
        stop_loss = signal_data.get('stop_loss', 'N/A')
        take_profits = signal_data.get('take_profits', [])  # ✅ Usar 'take_profits' en lugar de 'take_profit'
        
        # Emojis según dirección
        direction_emoji = "📈" if direction == "LONG" else "📉"
        leverage_emoji = "⚡" if leverage > 30 else "🔸"
        
        # Formatear take profits
        tp_text = " / ".join([f"{tp:.4f}" for tp in take_profits]) if take_profits else "N/A"
        
        message = f"""
{direction_emoji} **SEÑAL DE TRADING DETECTADA** {direction_emoji}

**Par:** {pair}
**Dirección:** {direction} {leverage_emoji} (x{leverage})
**Entry:** `{entry}`
**Stop Loss:** `{stop_loss}`
**Take Profits:** `{tp_text}`

**📊 ANÁLISIS:**
• Confianza: {analysis_summary.get('confidence', 0)}%
• Riesgo: {analysis_summary.get('risk_score', 'N/A')}/100
• Decisión: {analysis_summary.get('trading_decision', 'PENDING')}
• Volatilidad: {analysis_summary.get('volatility_alert', 'N/A')}

**🔍 DETALLES:**
• Momentum: {analysis_summary.get('momentum_strength', 'N/A')}
• Divergencia: {analysis_summary.get('divergence_detected', 'No')}
• Condición: {analysis_summary.get('market_condition', 'N/A')}

**⚠️ RIESGO CALCULADO:** {analysis_summary.get('real_risk_percent', 0):.1f}%
"""
        
        return message.strip()
        
    except Exception as e:
        logger.error(f"❌ Error formateando mensaje Telegram: {e}")
        return f"❌ Error generando análisis para {signal_data.get('pair', 'N/A')}"

def calculate_position_size(account_balance: float, risk_percent: float, 
                          entry_price: float, stop_loss: float) -> float:
    """
    Calcula el tamaño de posición basado en riesgo
    """
    try:
        risk_amount = account_balance * (risk_percent / 100)
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff == 0:
            return 0
        
        position_size = risk_amount / (price_diff / entry_price)
        return round(position_size, 2)
        
    except Exception as e:
        logger.error(f"❌ Error calculando tamaño de posición: {e}")
        return 0

def extract_hashtags(text: str) -> List[str]:
    """
    Extrae hashtags de un texto
    """
    try:
        hashtags = re.findall(r'#(\w+)', text)
        return [tag.upper() for tag in hashtags]
    except Exception as e:
        logger.error(f"❌ Error extrayendo hashtags: {e}")
        return []

def safe_float_conversion(value: str) -> Optional[float]:
    """
    Conversión segura a float
    """
    try:
        # Limpiar caracteres no numéricos excepto punto y negativo
        clean_value = re.sub(r'[^\d\.\-]', '', str(value))
        return float(clean_value) if clean_value else None
    except (ValueError, TypeError):
        return None

# ✅ ELIMINADO: El circular import que estaba aquí