# telegram_client.py - VERSIÓN COMPLETA Y CORREGIDA
"""
Cliente de Telegram para leer señales de canales - VERSIÓN COMPLETA
"""
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta

# ✅ Importaciones actualizadas para Telethon
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    FloodWaitError,
    AuthKeyError,
    RPCError,
    ChannelPrivateError
)
from telethon.tl.types import Message, Channel, InputPeerChannel
from telethon.tl.functions.messages import GetHistoryRequest

# ✅ Sistema de reconexión
from connection_monitor import connection_monitor
from health_monitor import health_monitor

logger = logging.getLogger(__name__)

class TelegramUserClient:
    """Cliente de usuario de Telegram para leer señales - VERSIÓN COMPLETA"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.session_name = "telegram_user_session"
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.available_channels = {}  # Cache de canales disponibles
        
        # Configuración desde config.py
        from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
        
        self.api_id = TELEGRAM_API_ID
        self.api_hash = TELEGRAM_API_HASH
        self.phone = TELEGRAM_PHONE
        
        logger.info("✅ Cliente de usuario de Telegram inicializado")
    
    async def connect(self) -> bool:
        """Conecta el cliente de usuario - CON CACHE DE CANALES"""
        try:
            if self.is_connected and self.client:
                logger.info("✅ Cliente ya conectado")
                return True
            
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash
            )
            
            await self.client.start(phone=self.phone)
            
            if await self.client.is_user_authorized():
                self.is_connected = True
                self.reconnect_attempts = 0
                
                # ✅ ACTUALIZAR CACHE DE CANALES DISPONIBLES
                await self._update_available_channels()
                
                # ✅ REGISTRAR EN HEALTH MONITOR
                health_monitor.record_telegram_bot_activity()
                
                logger.info("✅ Cliente de usuario conectado y autorizado")
                return True
            else:
                logger.error("❌ Cliente no autorizado")
                return False
                
        except AuthKeyError as e:
            logger.error(f"❌ Error de autenticación: {e}")
            # Eliminar sesión corrupta y reintentar
            import os
            if os.path.exists(f"{self.session_name}.session"):
                os.remove(f"{self.session_name}.session")
            logger.info("🗑️ Sesión corrupta eliminada, reintentando...")
            return await self._handle_reconnection()
            
        except SessionPasswordNeededError:
            logger.error("❌ Sesión requiere contraseña 2FA")
            return False
            
        except FloodWaitError as e:
            logger.error(f"⏳ Flood wait: {e.seconds} segundos")
            await asyncio.sleep(e.seconds)
            return await self._handle_reconnection()
            
        except Exception as e:
            logger.error(f"❌ Error conectando cliente: {e}")
            return await self._handle_reconnection()
    
    async def _update_available_channels(self):
        """Actualiza la cache de canales disponibles"""
        try:
            dialogs = await self.client.get_dialogs()
            self.available_channels = {}
            
            for dialog in dialogs:
                if dialog.is_channel or dialog.is_group:
                    channel_info = {
                        'id': dialog.id,
                        'name': dialog.name,
                        'entity': dialog.entity,
                        'access_hash': getattr(dialog.entity, 'access_hash', None) if dialog.entity else None
                    }
                    self.available_channels[dialog.id] = channel_info
                    
                    # También mapear por nombre para búsqueda flexible
                    if dialog.name:
                        self.available_channels[dialog.name.lower()] = channel_info
            
            logger.info(f"📊 Cache actualizada: {len([c for c in self.available_channels.values() if isinstance(c, dict)])} canales disponibles")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando cache de canales: {e}")
    
    async def _handle_reconnection(self) -> bool:
        """Maneja la reconexión con backoff exponential"""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error("🚨 Máximos intentos de reconexión alcanzados")
            health_monitor.record_connection_issue('telegram_bot', 
                                                 f"Máximos intentos de reconexión: {self.max_reconnect_attempts}")
            return False
        
        # Backoff exponential
        delay = min(60, 5 * (2 ** (self.reconnect_attempts - 1)))
        logger.info(f"🔄 Reintentando conexión en {delay} segundos (intento {self.reconnect_attempts})")
        
        await asyncio.sleep(delay)
        return await self.connect()
    
    async def get_available_channels(self) -> List[Dict]:
        """Obtiene lista de canales disponibles - ✅ MÉTODO NUEVO"""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Actualizar cache si está vacía
            if not self.available_channels:
                await self._update_available_channels()
            
            # Filtrar solo los canales (excluir entradas de nombre)
            channels = []
            for key, channel_info in self.available_channels.items():
                if isinstance(key, int) and isinstance(channel_info, dict):
                    channels.append(channel_info)
            
            # Ordenar por nombre
            channels.sort(key=lambda x: x.get('name', '').lower())
            
            logger.info(f"📊 {len(channels)} canales disponibles en cache")
            return channels
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo canales disponibles: {e}")
            return []
    
    async def get_channel_messages(self, channel_identifier: str, limit: int = 50) -> List[Message]:
        """
        Obtiene mensajes de un canal/grupo - CON MÚLTIPLES MÉTODOS DE ACCESO
        """
        try:
            if not self.is_connected or not self.client:
                logger.warning("🔌 Cliente no conectado, intentando reconectar...")
                if not await self.connect():
                    logger.error("❌ No se pudo reconectar el cliente")
                    return []
            
            # ✅ MÉTODO 1: Buscar en cache de canales disponibles
            channel_info = await self._find_channel_in_cache(channel_identifier)
            
            if channel_info:
                logger.info(f"🎯 Canal encontrado en cache: {channel_info['name']} (ID: {channel_info['id']})")
                return await self._get_messages_from_entity(channel_info['entity'], limit)
            
            # ✅ MÉTODO 2: Intentar acceso directo por ID/username
            try:
                entity = await self.client.get_entity(channel_identifier)
                return await self._get_messages_from_entity(entity, limit)
            except (ValueError, ChannelPrivateError) as e:
                logger.warning(f"⚠️ No se puede acceder directamente a {channel_identifier}: {e}")
            
            # ✅ MÉTODO 3: Usar InputPeerChannel si tenemos access_hash
            if channel_identifier.lstrip('-').isdigit():
                try:
                    channel_id = int(channel_identifier)
                    # Buscar en cache para obtener access_hash
                    for channel in self.available_channels.values():
                        if isinstance(channel, dict) and channel['id'] == channel_id:
                            if channel.get('access_hash'):
                                entity = InputPeerChannel(
                                    channel_id=channel_id,
                                    access_hash=channel['access_hash']
                                )
                                return await self._get_messages_from_entity(entity, limit)
                except Exception as e:
                    logger.debug(f"⚠️ Método InputPeerChannel falló: {e}")
            
            logger.error(f"❌ No se pudo acceder al canal: {channel_identifier}")
            logger.info(f"💡 Canales disponibles: {[c.get('name', 'N/A') for c in self.available_channels.values() if isinstance(c, dict)]}")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes: {e}")
            return []
    
    async def _find_channel_in_cache(self, identifier: str) -> Optional[Dict]:
        """Busca un canal en la cache por ID o nombre"""
        # Buscar por ID exacto
        if identifier.lstrip('-').isdigit():
            channel_id = int(identifier)
            if channel_id in self.available_channels:
                return self.available_channels[channel_id]
        
        # Buscar por nombre (case insensitive)
        identifier_lower = identifier.lower()
        for channel in self.available_channels.values():
            if isinstance(channel, dict) and channel.get('name'):
                if identifier_lower in channel['name'].lower():
                    return channel
        
        # Buscar por nombre parcial
        for channel in self.available_channels.values():
            if isinstance(channel, dict) and channel.get('name'):
                if any(word in channel['name'].lower() for word in identifier_lower.split()):
                    return channel
        
        return None
    
    async def _get_messages_from_entity(self, entity, limit: int) -> List[Message]:
        """Obtiene mensajes desde una entidad"""
        try:
            messages = await self.client.get_messages(entity, limit=limit)
            
            # ✅ REGISTRAR ACTIVIDAD
            health_monitor.record_telegram_bot_activity()
            
            logger.info(f"✅ Obtenidos {len(messages)} mensajes")
            return messages
            
        except ChannelPrivateError:
            logger.error("🔒 Canal privado - sin permisos de acceso")
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes desde entidad: {e}")
            return []
    
    async def get_recent_signals(self, channel_identifier: str, hours: int = 24) -> List[dict]:
        """
        Obtiene señales recientes del canal - CON ACCESO MEJORADO
        """
        try:
            messages = await self.get_channel_messages(channel_identifier, limit=100)
            recent_signals = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for message in messages:
                if message.date.replace(tzinfo=None) > cutoff_time and message.text:
                    signal_data = {
                        'id': message.id,
                        'date': message.date,
                        'text': message.text,
                        'raw': message
                    }
                    recent_signals.append(signal_data)
            
            logger.info(f"📡 {len(recent_signals)} señales recientes encontradas en {channel_identifier}")
            return recent_signals
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo señales recientes: {e}")
            return []
    
    async def test_channel_access(self, channel_identifier: str) -> Dict:
        """Testea el acceso a un canal específico - ✅ MÉTODO NUEVO"""
        result = {
            'accessible': False,
            'channel_info': None,
            'message_count': 0,
            'error': None
        }
        
        try:
            # Buscar en cache
            channel_info = await self._find_channel_in_cache(channel_identifier)
            if channel_info:
                result['channel_info'] = channel_info
            
            # Intentar obtener mensajes
            messages = await self.get_channel_messages(channel_identifier, limit=5)
            
            if messages:
                result['accessible'] = True
                result['message_count'] = len(messages)
                result['channel_info'] = channel_info or {
                    'id': getattr(messages[0].chat, 'id', None),
                    'name': getattr(messages[0].chat, 'title', 'Unknown')
                }
            else:
                result['error'] = "No se pudieron obtener mensajes"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result

    async def disconnect(self):
        """Desconecta el cliente"""
        try:
            if self.client:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("✅ Cliente de usuario desconectado")
        except Exception as e:
            logger.error(f"❌ Error desconectando cliente: {e}")
    
    async def test_connection(self) -> bool:
        """Testea la conexión del cliente"""
        try:
            if not await self.connect():
                return False
            
            # Intentar una operación simple
            await self.client.get_me()
            
            logger.info("✅ Conexión de usuario Telegram verificada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testeando conexión: {e}")
            health_monitor.record_connection_issue('telegram_bot', f"Test fallido: {e}")
            return False

# Instancia global
telegram_user_client = TelegramUserClient()