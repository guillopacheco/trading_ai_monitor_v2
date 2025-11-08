"""
telegram_reader.py
----------------------------------
Lee mensajes del canal de Telegram de NeuroTrader y detecta señales o actualizaciones de profit.
Compatible con signal_manager.py (asincronía gestionada externamente).
"""

import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events

from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION, TELEGRAM_SIGNAL_CHANNEL_ID
from notifier import send_message
from signal_manager import process_signal

logger = logging.getLogger("telegram_reader")

# ================================================================
# ⚙️ Inicialización del cliente de Telethon
# ================================================================
client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)


# ================================================================
# 🧠 Parser básico de señales
# ================================================================
def parse_signal_message(message_text: str):
    """
    Interpreta una señal recibida del canal de Telegram.
    Retorna un diccionario con los campos relevantes o None si no es una señal válida.
    """
    try:
        text = message_text.replace("\n", " ").replace("*", "").strip()

        # --- Caso: señales tipo "🔥 #BTC/USDT (Long📈, x20) 🔥 Entry - 71000 ..."
        if "Entry" in text and "/" in text:
            pair = text.split("#")[1].split("(")[0].replace("/", "").strip()
            direction = "long" if "long" in text.lower() else "short"
            leverage = 0
            if "x" in text.lower():
                try:
                    leverage = int(text.lower().split("x")[1].split(")")[0].split()[0])
                except Exception:
                    leverage = 20

            # Buscar entrada (Entry o Price)
            entry = 0.0
            if "entry" in text.lower():
                entry = float(text.lower().split("entry")[1].split()[0].replace("-", "").strip())
            elif "price" in text.lower():
                entry = float(text.lower().split("price")[1].split()[0].replace("-", "").strip())

            return {
                "pair": pair.upper(),
                "direction": direction,
                "entry": entry,
                "leverage": leverage,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }

        # --- Caso: actualizaciones de profit (ej. "✅ Price - 0.08661 🔝 Profit - 60%")
        if "profit" in text.lower() and "price" in text.lower():
            parts = text.split("Price")[1].split("Profit")
            try:
                price_val = float(parts[0].replace("-", "").strip().split()[0])
                profit_val = parts[1].replace("-", "").replace("%", "").strip().split()[0]
            except Exception:
                price_val, profit_val = 0, 0

            return {
                "type": "profit_update",
                "price": price_val,
                "profit": profit_val,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }

        return None

    except Exception as e:
        logger.error(f"❌ Error parseando mensaje: {e}")
        return None


# ================================================================
# 📡 Escucha en tiempo real del canal
# ================================================================
async def start_telegram_reader():
    """Inicia la escucha del canal de señales."""
    @client.on(events.NewMessage(chats=TELEGRAM_SIGNAL_CHANNEL_ID))
    async def handler(event):
        try:
            message = event.message.message.strip()
            logger.info(f"📥 Señal recibida ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}):\n{message[:150]}")

            parsed = parse_signal_message(message)
            if not parsed:
                logger.warning("⚠️ Mensaje ignorado: formato no reconocido.")
                return

            # --- Si es una actualización de profit
            if parsed.get("type") == "profit_update":
                msg = (
                    f"📈 *Actualización de Profit Detectada*\n"
                    f"💰 Precio: {parsed['price']}\n"
                    f"📊 Profit: {parsed['profit']}%\n"
                    f"🕒 {parsed['timestamp']}"
                )
                send_message(msg)
                logger.info(f"💬 Profit update enviada: {parsed['profit']}%")
                return

            # --- Si es una señal nueva
            await process_signal(parsed)

        except Exception as e:
            logger.error(f"❌ Error manejando mensaje de Telegram: {e}")
            send_message(f"❌ Error procesando mensaje: {e}")

    logger.info("📡 TelegramSignalReader iniciado en modo escucha...")
    async with client:
        await client.run_until_disconnected()
