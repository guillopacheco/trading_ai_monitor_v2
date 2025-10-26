"""
Cliente de Telegram usando Telethon para leer canales como usuario - MEJORADO
"""
import logging
import re
from telethon import TelegramClient
from telethon import events  # ✅ AGREGAR ESTE IMPORT
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, SIGNALS_CHANNEL_ID

logger = logging.getLogger(__name__)

class TelegramUserClient:
    """Cliente de Telegram para leer mensajes como usuario - MEJORADO"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.signal_callback = None  # ✅ AGREGAR ESTA LÍNEA
        
    def set_signal_callback(self, callback):
        """Establece el callback para procesar señales recibidas - ✅ NUEVO MÉTODO"""
        self.signal_callback = callback
    
    async def connect(self):
        """Conecta el cliente de Telegram"""
        try:
            if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
                raise ValueError("Faltan credenciales de Telegram User API")
            
            self.client = TelegramClient(
                session='user_session',
                api_id=int(TELEGRAM_API_ID),
                api_hash=TELEGRAM_API_HASH
            )
            
            await self.client.start(phone=TELEGRAM_PHONE)
            
            # Verificar autenticación
            if not await self.client.is_user_authorized():
                raise SessionPasswordNeededError("Se requiere verificación en dos pasos")
            
            self.is_connected = True
            logger.info("✅ Cliente de Telegram (Usuario) conectado correctamente")
            return True
            
        except SessionPasswordNeededError:
            logger.error("❌ Se requiere verificación en dos pasos. Configura la contraseña.")
            return False
        except Exception as e:
            logger.error(f"❌ Error conectando cliente de Telegram: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta el cliente"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            logger.info("✅ Cliente de Telegram desconectado")
    
    def _extract_message_text(self, message):
        """Extrae texto de diferentes tipos de mensajes"""
        try:
            if message.text:
                return message.text
            
            # Mensajes con media que pueden contener texto
            if message.media:
                if hasattr(message.media, 'document'):
                    caption = message.text or ""
                    return f"[MEDIA] {caption}"
                elif isinstance(message.media, MessageMediaPhoto):
                    caption = message.text or ""
                    return f"[PHOTO] {caption}"
            
            return ""
        except Exception as e:
            logger.error(f"Error extrayendo texto del mensaje: {e}")
            return ""
    
    async def _handle_channel_message(self, event):
        """Maneja mensajes recibidos del canal"""
        try:
            message_text = self._extract_message_text(event.message)
            if not message_text:
                return
            
            logger.info(f"📨 Mensaje recibido del canal: {message_text[:100]}...")
            
            # Verificar si es una señal de trading
            if self._is_trading_signal(message_text):
                logger.info(f"🔍 Señal potencial detectada")
                if self.signal_callback:  # ✅ AHORA USA EL CALLBACK
                    await self.signal_callback({'message_text': message_text})
            else:
                logger.debug("Mensaje no reconocido como señal de trading")
                
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje del canal: {e}")
    
    def _is_trading_signal(self, text: str) -> bool:
        """Verifica si el texto parece una señal de trading"""
        signal_keywords = [
            'BUY', 'SELL', 'LONG', 'SHORT', 'ENTRY', 'TP', 'SL',
            '🔥', '🎯', '⭐', '✨', 'TAKE-PROFIT', 'STOP-LOSS'
        ]
        return any(keyword.lower() in text.lower() for keyword in signal_keywords)
    
    async def start_listening(self):
        """Inicia la escucha del canal de señales"""
        try:
            if not await self.connect():
                raise Exception("No se pudo conectar a Telegram")
            
            # ✅ CORREGIDO: Usar events.NewMessage en lugar de self.client.NewMessage
            @self.client.on(events.NewMessage(chats=int(SIGNALS_CHANNEL_ID)))
            async def handler(event):
                await self._handle_channel_message(event)
            
            logger.info(f"🎧 Escuchando canal de señales: {SIGNALS_CHANNEL_ID}")
            
            # Mantener la conexión activa
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"❌ Error iniciando listener de Telegram: {e}")
            raise

# Instancia global
telegram_user_client = TelegramUserClient()