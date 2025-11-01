# emergency_fix.py
import asyncio
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmergencySignalProcessor:
    """Procesador de emergencia - SIMPLE Y FUNCIONAL"""
    
    def __init__(self):
        self.processed_count = 0
        self.last_signal = None
    
    async def process_signal_direct(self, message_text: str):
        """Procesa señales DIRECTAMENTE sin dependencias complejas"""
        try:
            logger.info(f"🚨 PROCESANDO SEÑAL DE EMERGENCIA: {message_text[:100]}...")
            
            # 1. Parseo directo (sin helpers complejos)
            signal_data = self.parse_signal_emergency(message_text)
            if not signal_data:
                logger.error("❌ No se pudo parsear la señal")
                return False
            
            logger.info(f"✅ Señal parseada: {signal_data}")
            
            # 2. Análisis básico
            analysis = await self.basic_analysis(signal_data)
            
            # 3. Notificación inmediata
            await self.emergency_notification(signal_data, analysis)
            
            self.processed_count += 1
            self.last_signal = signal_data
            
            logger.info(f"🎯 Señal procesada exitosamente (#{self.processed_count})")
            return True
            
        except Exception as e:
            logger.error(f"💥 Error en procesamiento de emergencia: {e}")
            return False
    
    def parse_signal_emergency(self, text: str):
        """Parser de emergencia - MÍNIMO Y FUNCIONAL"""
        try:
            # Extraer símbolo
            symbol = None
            if "#BTC" in text.upper():
                symbol = "BTCUSDT"
            elif "#ETH" in text.upper():
                symbol = "ETHUSDT" 
            elif "#ADA" in text.upper():
                symbol = "ADAUSDT"
            else:
                # Buscar cualquier #SYMBOL
                import re
                match = re.search(r'#(\w+)', text)
                if match:
                    symbol = match.group(1).upper() + "USDT"
            
            if not symbol:
                return None
            
            # Extraer dirección
            direction = "LONG" if "LONG" in text.upper() else "SHORT" if "SHORT" in text.upper() else "LONG"
            
            # Extraer precios básicos
            import re
            prices = re.findall(r'(\d+\.?\d*)', text)
            entry = float(prices[0]) if prices else 1.0
            
            return {
                'pair': symbol,
                'direction': direction,
                'entry': entry,
                'stop_loss': entry * 0.98,
                'take_profits': [entry * 1.02, entry * 1.04],
                'leverage': 20,
                'timestamp': datetime.now(),
                'emergency_processed': True
            }
            
        except Exception as e:
            logger.error(f"Error en parser de emergencia: {e}")
            return None
    
    async def basic_analysis(self, signal_data):
        """Análisis básico de emergencia"""
        return {
            'action': 'ENTRAR',
            'confidence': 'ALTA', 
            'reason': 'Procesamiento de emergencia activado',
            'timestamp': datetime.now().isoformat()
        }
    
    async def emergency_notification(self, signal_data, analysis):
        """Notificación de emergencia"""
        try:
            from notifier import telegram_notifier
            
            message = f"""
🚨 **SEÑAL PROCESADA - MODO EMERGENCIA**

**Par:** {signal_data['pair']}
**Dirección:** {signal_data['direction']}
**Entry:** {signal_data['entry']}
**Análisis:** {analysis['reason']}

⚠️ Sistema operando en modo de emergencia
"""
            await telegram_notifier.send_alert(
                "Señal de Emergencia", 
                message, 
                "warning"
            )
            
        except Exception as e:
            logger.error(f"No se pudo enviar notificación: {e}")

# Instancia global de emergencia
emergency_processor = EmergencySignalProcessor()

async def test_emergency_system():
    """Prueba el sistema de emergencia"""
    test_signals = [
        "🔥 #BTCUSDT LONG Entry: 50000",
        "🎯 #ETHUSDT SHORT Price: 3500",
        "⚡ #ADAUSDT LONG 0.45"
    ]
    
    for signal in test_signals:
        success = await emergency_processor.process_signal_direct(signal)
        print(f"Señal: {signal[:30]}... -> {'✅' if success else '❌'}")
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("🧪 Probando sistema de emergencia...")
    asyncio.run(test_emergency_system())