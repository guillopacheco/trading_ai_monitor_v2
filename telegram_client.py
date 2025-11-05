import asyncio
import logging
import re
from telethon import TelegramClient, events
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_SIGNAL_CHANNEL_ID,
)
from helpers import clean_text, normalize_symbol
from signal_manager import process_signal
from notifier import send_message

logger = logging.getLogger("telegram_client")

# ================================================================
# ⚙️ Inicialización del cliente
# ================================================================
client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)


# ================================================================
# 🔍 Detección de señal de trading
# ================================================================
def parse_signal(message_text: str):
    """
    Analiza un mensaje y extrae datos de la señal si es válida.
    Ejemplo:
        🔥 #ICP/USDT (Long📈, x20) 🔥
        Entry - 5.311
        Take-Profit:
        🥉 5.4172 ...
    """
    try:
        text = clean_text(message_text)

        # Filtrar mensajes irrelevantes
        if "profit" in text.lower() or "✅" in text:
            logger.debug("📭 Ignorando mensaje de profit.")
            return None

        # Buscar estructura principal
        match = re.search(
            r"#?([\w\-]+)/USDT.*?\((Long|Short).*?x(\d+)\).*?Entry\s*-\s*([\d\.]+)",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            logger.debug("⚠️ No coincide con formato de señal.")
            return None

        pair, direction, leverage, entry = match.groups()
        pair = normalize_symbol(pair)
        direction = direction.lower()
        leverage = int(leverage)
        entry = float(entry)

        # Buscar take profits
        tps = re.findall(r"([\d\.]+)\s*\(", text)
        take_profits = [float(tp) for tp in tps if float(tp) != entry]

        return {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits[:4],
        }

    except Exception as e:
        logger.error(f"❌ Error parseando señal: {e}")
        return None


# ================================================================
# 📨 Evento: Mensaje nuevo en el canal de señales
# ================================================================
@client.on(events.NewMessage(chats=TELEGRAM_SIGNAL_CHANNEL_ID))
async def handler_new_signal(event):
    try:
        msg_text = event.raw_text.strip()
        logger.info(f"📩 Mensaje recibido: {msg_text[:60]}...")

        signal = parse_signal(msg_text)
        if not signal:
            return

        logger.info(f"🔍 Señal potencial detectada: {signal['pair']} ({signal['direction']} x{signal['leverage']})")
        await send_message(
            f"📡 *Señal detectada*\n"
            f"💱 {signal['pair']} ({signal['direction'].upper()} x{signal['leverage']})\n"
            f"🎯 Entry: {signal['entry']}\n"
            f"📊 Analizando condiciones..."
        )

        # Analizar la señal detectada
        await process_signal(signal)

    except Exception as e:
        logger.error(f"❌ Error procesando mensaje de Telegram: {e}")
        await send_message(f"⚠️ Error procesando señal: {e}")


# ================================================================
# 🚀 Inicio del cliente
# ================================================================
async def run_telegram_listener():
    """
    Inicia el listener de Telegram.
    """
    try:
        await client.start()
        logger.info("✅ Conexión con Telegram establecida (canal de señales activo).")
        await send_message("✅ *Conectado al canal de señales Andy Insider*")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"❌ Error iniciando Telegram listener: {e}")
        await send_message(f"⚠️ Error al conectar con Telegram: {e}")
