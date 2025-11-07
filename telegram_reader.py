"""
telegram_reader.py
------------------------------------------------------------
Lector asincrónico de señales desde el canal de Telegram.
Usa Telethon para conectarse a la cuenta del usuario y escuchar
mensajes en el canal de señales configurado en el archivo .env.

Cada mensaje nuevo detectado se pasa al callback `process_signal()`
para su análisis técnico y almacenamiento.
------------------------------------------------------------
"""

import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION,
    TELEGRAM_SIGNAL_CHANNEL_ID,
)
from datetime import datetime

logger = logging.getLogger("telegram_reader")

# ================================================================
# 🧠 Clase principal del lector de señales
# ================================================================
class TelegramSignalReader:
    def __init__(self, callback):
        """
        callback: función que procesa las señales (ej: process_signal)
        """
        self.callback = callback
        self.client = None
        self.connected = False

    # ------------------------------------------------------------
    async def connect(self):
        """Inicia sesión en Telegram y configura el cliente."""
        try:
            self.client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.info("🔑 Autenticación requerida. Solicitando código de verificación...")
                await self.client.send_code_request(TELEGRAM_PHONE)
                code = input("📲 Ingresa el código recibido por Telegram: ")
                await self.client.sign_in(TELEGRAM_PHONE, code)

            self.connected = True
            me = await self.client.get_me()
            logger.info(f"✅ Conectado como {me.first_name} ({me.id})")
        except SessionPasswordNeededError:
            logger.error("🔐 La cuenta tiene 2FA habilitado. Ingresa tu contraseña de Telegram.")
            password = input("🔑 Contraseña: ")
            await self.client.sign_in(password=password)
        except Exception as e:
            logger.error(f"❌ Error al conectar con Telegram: {e}")

    # ------------------------------------------------------------
    async def listen_signals(self):
        """Escucha nuevos mensajes en el canal de señales configurado."""
        if not self.client or not self.connected:
            await self.connect()

        logger.info("📡 TelegramSignalReader iniciado en modo escucha...")

        @self.client.on(events.NewMessage(chats=int(TELEGRAM_SIGNAL_CHANNEL_ID)))
        async def handler(event):
            try:
                text = event.raw_text.strip()
                if not text:
                    return

                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"📥 Señal recibida ({timestamp}):\n{text[:80]}...")

                # Ejecutar análisis de señal en una tarea separada
                asyncio.create_task(self.callback(text))

            except Exception as e:
                logger.error(f"❌ Error procesando mensaje recibido: {e}")

        # Mantener la sesión viva
        try:
            await self.client.run_until_disconnected()
        except FloodWaitError as e:
            logger.warning(f"⏳ FloodWait: esperando {e.seconds} segundos antes de reconectar...")
            await asyncio.sleep(e.seconds)
            await self.listen_signals()
        except Exception as e:
            logger.error(f"❌ Error en listener: {e}")
            await asyncio.sleep(10)
            await self.listen_signals()


# ================================================================
# 🚀 Función de arranque principal
# ================================================================
async def start_telegram_reader(callback):
    """
    Inicializa el cliente y lanza el modo escucha del canal de señales.
    """
    reader = TelegramSignalReader(callback)
    await reader.connect()
    await reader.listen_signals()
