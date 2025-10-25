"""
Lector de señales desde canal de Telegram usando Telethon
"""
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, SIGNALS_CHANNEL_ID

logger = logging.getLogger(__name__)

class TelegramSignalReader:
    """Lector de señales de trading desde canal de Telegram usando Telethon"""
    
    def __init__(self):
        self.client = None
        self.signal_callback = None
        self.channel_id = int(SIGNALS_CHANNEL_ID)
        self.is_listening = False
    
    def set_signal_callback(self, callback):
        """Establece el callback para procesar señales recibidas"""
        self.signal_callback = callback
    
    async def connect(self):
        """Conecta el cliente de Telegram"""
        try:
            if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
                raise ValueError("Configuración de Telegram incompleta")
            
            self.client = TelegramClient(
                'trading_session', 
                TELEGRAM_API_ID, 
                TELEGRAM_API_HASH
            )
            
            await self.client.start(phone=TELEGRAM_PHONE)
            logger.info("✅ Cliente de Telegram conectado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando cliente de Telegram: {e}")
            return False
    
    async def _extract_message_text(self, message):
        """Extrae texto de diferentes tipos de mensajes"""
        try:
            if message.text:
                return message.text
            
            # Mensajes con media que pueden contener texto
            if message.media:
                if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
                    # Podría ser una captura de pantalla con texto
                    caption = message.text or ""
                    return f"[MEDIA] {caption}"
            
            return ""
        except Exception as e:
            logger.error(f"Error extrayendo texto del mensaje: {e}")
            return ""
    
    async def _parse_signal_message(self, text):
        """
        Parse básico de señales de trading
        TODO: Implementar lógica específica de tu canal
        """
        try:
            # Palabras clave que indican señales de trading
            signal_keywords = ['BUY', 'SELL', 'LONG', 'SHORT', 'ENTRY', 'TP', 'SL']
            
            if any(keyword in text.upper() for keyword in signal_keywords):
                # Extraer par (ejemplo básico)
                import re
                pairs = re.findall(r'[A-Z]{3,}/[A-Z]{3,}', text)
                if pairs:
                    return {
                        'pair': pairs[0],
                        'direction': 'BUY' if 'BUY' in text.upper() or 'LONG' in text.upper() else 'SELL',
                        'message_text': text,
                        'timestamp': asyncio.get_event_loop().time()
                    }
            return None
        except Exception as e:
            logger.error(f"Error parseando mensaje: {e}")
            return None
    
    async def _handle_channel_message(self, event):
        """Maneja mensajes recibidos del canal"""
        try:
            message_text = await self._extract_message_text(event.message)
            if not message_text:
                return
            
            logger.info(f"📨 Mensaje recibido del canal: {message_text[:100]}...")
            
            # Parsear como señal de trading
            signal_data = await self._parse_signal_message(message_text)
            if signal_data and self.signal_callback:
                logger.info(f"✅ Señal detectada: {signal_data['pair']} - {signal_data['direction']}")
                await self.signal_callback(signal_data)
            else:
                logger.debug("Mensaje no reconocido como señal de trading")
                
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje del canal: {e}")
    
    async def start_listening(self):
        """Inicia la escucha del canal"""
        try:
            if not await self.connect():
                raise Exception("No se pudo conectar a Telegram")
            
            # Configurar handler para mensajes del canal
            @self.client.on(events.NewMessage(chats=self.channel_id))
            async def handler(event):
                await self._handle_channel_message(event)
            
            self.is_listening = True
            logger.info(f"✅ Escuchando canal: {self.channel_id}")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando listener de Telegram: {e}")
            raise
    
    async def stop_listening(self):
        """Detiene la escucha y desconecta el cliente"""
        try:
            self.is_listening = False
            if self.client:
                await self.client.disconnect()
                logger.info("✅ Cliente de Telegram desconectado")
        except Exception as e:
            logger.error(f"❌ Error deteniendo cliente de Telegram: {e}")

# Instancia global
telegram_reader = TelegramSignalReader()