import logging
import asyncio
from telethon import TelegramClient, events
from datetime import datetime
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_SIGNAL_CHANNEL_ID,
)
from notifier import send_message

logger = logging.getLogger("telegram_reader")

# ================================================================
# 🧩 Parser de texto de señal NeuroTrader
# ================================================================
def parse_signal_text(text: str):
    """
    Parsea una señal en formato NeuroTrader y devuelve un diccionario con:
    pair, direction, entry, leverage.
    """
    import re

    text = text.replace("\n", " ").replace("\r", " ").strip()

    # Buscar símbolo (#BTC/USDT o #BTCUSDT)
    pair_match = re.search(r"#([A-Z0-9]+)(?:/USDT|USDT)", text)
    if not pair_match:
        return None
    pair = pair_match.group(1).upper() + "USDT"

    # Dirección (Long📈 o Short📉)
    if "long" in text.lower():
        direction = "long"
    elif "short" in text.lower():
        direction = "short"
    else:
        direction = None

    # Entry
    entry_match = re.search(r"(?:Entry|Price)\s*[-:]?\s*([\d\.]+)", text, re.IGNORECASE)
    entry = float(entry_match.group(1)) if entry_match else None

    # Leverage (x20, x10, etc.)
    lev_match = re.search(r"x\s?(\d+)", text.lower())
    leverage = int(lev_match.group(1)) if lev_match else 0

    if not pair or not direction or not entry:
        return None

    return {
        "pair": pair,
        "direction": direction,
        "entry": entry,
        "leverage": leverage,
    }


# ================================================================
# 📡 Lector principal de Telegram
# ================================================================
async def start_telegram_reader(callback=None):
    """
    Conecta a Telegram y escucha señales del canal configurado.
    Si se proporciona un callback (por ejemplo, process_signal),
    se invoca automáticamente con la señal parseada.
    """
    try:
        client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ Conectado como {me.first_name} ({me.id})")

        if TELEGRAM_SIGNAL_CHANNEL_ID is None:
            logger.error("❌ TELEGRAM_SIGNAL_CHANNEL_ID no definido en .env")
            return

        @client.on(events.NewMessage(chats=int(TELEGRAM_SIGNAL_CHANNEL_ID)))
        async def handler(event):
            try:
                text = event.raw_text.strip()
                logger.info(f"📥 Señal recibida ({datetime.now():%Y-%m-%d %H:%M:%S}):\n{text[:120]}...")
                parsed = parse_signal_text(text)

                if not parsed:
                    logger.error(f"❌ Error procesando señal desconocida: {text[:80]}...")
                    send_message(f"⚠️ Señal no reconocida:\n{text[:200]}")
                    return

                # Si se pasa callback (ej. process_signal), se invoca
                if callback:
                    await callback(parsed)
                else:
                    logger.info(f"ℹ️ Señal parseada sin callback: {parsed}")
                    send_message(f"✅ Señal parseada correctamente: {parsed}")

            except Exception as e:
                logger.error(f"❌ Error procesando mensaje: {e}")
                send_message(f"⚠️ Error procesando mensaje: {e}")

        logger.info("📡 TelegramSignalReader iniciado en modo escucha...")
        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"❌ Error iniciando TelegramSignalReader: {e}")
        send_message(f"❌ Error crítico en lector de señales: {e}")
