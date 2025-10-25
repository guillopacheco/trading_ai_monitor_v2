# telegram_client.py
"""
Cliente de Telegram usando Telethon para leer canales como usuario - CON RECONEXIÓN COMPLETA
"""
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError, AuthKeyError
from telethon.network import ConnectionError as TelethonConnectionError
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, SIGNALS_CHANNEL_ID
from reconnection_manager import reconnection_manager
from health_monitor import health_monitor

logger = logging.getLogger(__name__)

class TelegramUserClient:
    """Cliente de Telegram para leer mensajes como usuario - CON RECONEXIÓN COMPLETA"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.signal_callback = None
        self.is_listening = False
        self.reconnect_task = None
        self.message_handler = None
        
    def set_signal_callback(self, callback):
        """Establece el callback para procesar señales recibidas"""
        self.signal_callback = callback
    
    async def connect(self) -> bool:
        """Conecta el cliente de Telegram con reconexión automática"""
        try:
            logger.info("🔗 Conectando cliente de Telegram...")
            
            if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
                raise ValueError("Faltan credenciales de Telegram User API")
            
            self.client = TelegramClient(
                session='user_session',
                api_id=int(TELEGRAM_API_ID),
                api_hash=TELEGRAM_API_HASH
            )
            
            await self.client.start(phone=TELEGRAM_PHONE)
            
            if not await self.client.is_user_authorized():
                raise SessionPasswordNeededError("Se requiere verificación en dos pasos")
            
            self.is_connected = True
            logger.info("✅ Cliente de Telegram (Usuario) conectado correctamente")
            
            # Registrar actividad en health monitor
            health_monitor.record_telegram_activity()
            
            return True
            
        except SessionPasswordNeededError:
            logger.error("❌ Se requiere verificación en dos pasos. Configura la contraseña.")
            return False
        except FloodWaitError as e:
            logger.error(f"⏳ Flood wait de Telegram: {e.seconds} segundos")
            await asyncio.sleep(e.seconds)
            return False
        except (ConnectionError, TelethonConnectionError) as e:
            logger.error(f"🌐 Error de conexión de red: {e}")
            return False
        except AuthKeyError as e:
            logger.error(f"🔑 Error de autenticación: {e}. Es posible que necesites reautenticar.")
            return False
        except Exception as e:
            logger.error(f"❌ Error conectando cliente de Telegram: {e}")
            return False
    
    async def resilient_connect(self) -> bool:
        """Conexión con reintentos automáticos"""
        success = await reconnection_manager.execute_with_retry(
            "telegram_user",
            self.connect
        )
        
        if success:
            logger.info("🎉 Reconexión exitosa de Telegram User")
            # Limpiar cualquier alerta de salud relacionada
            health_monitor.record_telegram_activity()
        else:
            logger.error("💥 No se pudo reconectar Telegram User después de múltiples intentos")
            
        return success
    
    async def start_listening_with_reconnection(self):
        """Inicia la escucha con supervisión de conexión"""
        self.is_listening = True
        
        logger.info("🚀 Iniciando sistema de escucha con reconexión automática")
        
        while self.is_listening:
            try:
                # Intentar conectar con reconexión
                if await self.resilient_connect():
                    # Configurar handler de mensajes
                    await self._setup_message_handler()
                    
                    logger.info(f"🎧 Escuchando canal: {SIGNALS_CHANNEL_ID}")
                    
                    # Notificar reconexión exitosa
                    await self._notify_reconnection_success()
                    
                    # Mantener conexión activa - esta llamada bloquea hasta desconexión
                    await self.client.run_until_disconnected()
                
                # Si llegamos aquí, la conexión se cayó
                logger.warning("🔌 Conexión de Telegram perdida, intentando reconectar...")
                await self._safe_disconnect()
                
                # Esperar antes del próximo intento de reconexión
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                logger.info("🛑 Escucha cancelada por el sistema")
                break
            except Exception as e:
                logger.error(f"❌ Error en loop de escucha: {e}")
                await self._safe_disconnect()
                await asyncio.sleep(30)  # Esperar más tiempo por errores graves
    
    async def _setup_message_handler(self):
        """Configura el manejador de mensajes"""
        # Remover handler anterior si existe
        if self.message_handler:
            self.client.remove_event_handler(self.message_handler)
        
        @self.client.on(events.NewMessage(chats=int(SIGNALS_CHANNEL_ID)))
        async def handler(event):
            await self._handle_channel_message(event)
        
        self.message_handler = handler
        logger.debug("📝 Handler de mensajes configurado")
    
    async def _notify_reconnection_success(self):
        """Notifica reconexión exitosa"""
        try:
            from notifier import telegram_notifier
            status = reconnection_manager.get_component_status("telegram_user")
            
            message = f"""
🔄 **RECONEXIÓN EXITOSA - Telegram User**

✅ Conexión restablecida correctamente
📊 Estadísticas:
- Reintentos: {status.get('retry_count', 0)}
- Éxitos consecutivos: {status.get('success_count', 0)}
- Estado: CONECTADO

Continuando con el monitoreo de señales...
"""
            await telegram_notifier.send_alert("Reconexión Exitosa", message, "success")
            
        except Exception as e:
            logger.warning(f"No se pudo enviar notificación de reconexión: {e}")
    
    async def _safe_disconnect(self):
        """Desconexión segura"""
        try:
            if self.client:
                await self.client.disconnect()
            self.is_connected = False
            self.message_handler = None
            logger.debug("🔒 Cliente de Telegram desconectado de forma segura")
        except Exception as e:
            logger.error(f"Error en desconexión segura: {e}")
    
    async def _handle_channel_message(self, event):
        """Maneja mensajes recibidos del canal"""
        try:
            message_text = self._extract_message_text(event.message)
            if not message_text:
                return
            
            logger.info(f"📨 Mensaje recibido del canal: {message_text[:100]}...")
            
            # Registrar actividad para health monitor
            health_monitor.record_telegram_activity()
            
            if self._is_trading_signal(message_text) and self.signal_callback:
                await self.signal_callback({'message_text': message_text})
            else:
                logger.debug("Mensaje no reconocido como señal de trading")
                
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
    
    def _extract_message_text(self, message):
        """Extrae texto de diferentes tipos de mensajes"""
        try:
            if message.text:
                return message.text
            
            if message.media:
                caption = message.text or ""
                return f"[MEDIA] {caption}"
            
            return ""
        except Exception as e:
            logger.error(f"Error extrayendo texto: {e}")
            return ""
    
    def _is_trading_signal(self, text: str) -> bool:
        """Verifica si el texto parece una señal de trading"""
        signal_keywords = [
            'BUY', 'SELL', 'LONG', 'SHORT', 'ENTRY', 'TP', 'SL',
            '🔥', '🎯', '⭐', '✨', 'TAKE-PROFIT', 'STOP-LOSS'
        ]
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in signal_keywords)
    
    async def start_listening(self):
        """Inicia la escucha del canal de señales (método principal)"""
        if self.is_listening:
            logger.warning("⚠️ El sistema de escucha ya está activo")
            return
            
        logger.info("🚀 Iniciando sistema de escucha con reconexión automática")
        await self.start_listening_with_reconnection()
    
    async def stop_listening(self):
        """Detiene la escucha de manera controlada"""
        self.is_listening = False
        await self._safe_disconnect()
        logger.info("🛑 Sistema de escucha detenido")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Obtiene el estado de conexión actual"""
        status = reconnection_manager.get_component_status("telegram_user")
        status.update({
            'is_connected': self.is_connected,
            'is_listening': self.is_listening,
            'has_callback': self.signal_callback is not None
        })
        return status

# Instancia global
telegram_user_client = TelegramUserClient()