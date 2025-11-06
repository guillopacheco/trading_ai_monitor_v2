import logging
import re
from telethon import TelegramClient, events
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION, TELEGRAM_SIGNAL_CHANNEL_ID
from notifier import send_message
from signal_manager import process_signal

logger = logging.getLogger("telegram_reader")

# ==================== Cliente Telethon ===========================
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = TelegramClient(TELEGRAM_SESSION, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    return _client

# ==================== Parser de señales ==========================
signal_regex = re.compile(
    r"#([A-Z0-9]+)/USDT\s*\((Long|Short)[^x]*x(\d+)\).*?Entry\s*-\s*([\d.]+).*?"
    r"Take-Profit:\s*(?:🥉\s*([\d.]+).*?🥈\s*([\d.]+).*?🥇\s*([\d.]+).*?🚀\s*([\d.]+))?",
    re.S
)

profit_update_regex = re.compile(r'✅\s*Price\s*-\s*\d', re.I)

def parse_message(text: str):
    if profit_update_regex.search(text):
        logger.info("💰 Mensaje de profit — ignorado")
        return None
    m = signal_regex.search(text)
    if not m:
        return None
    pair, direction, leverage, entry, tp1, tp2, tp3, tp4 = m.groups()
    tps = [float(x) for x in (tp1, tp2, tp3, tp4) if x]
    data = {
        "pair": pair.strip(),
        "direction": direction.lower(),
        "leverage": int(leverage),
        "entry": float(entry),
        "take_profits": tps,
        "message_text": text,
    }
    logger.info(f"✅ Señal parseada: {data['pair']} ({data['direction']}) x{data['leverage']}")
    return data

# ==================== Listener del canal =========================
async def start_telegram_reader():
    """
    Conecta con la cuenta personal y escucha el canal de señales.
    Cuando llega una señal válida, llama a process_signal(data).
    """
    client = _get_client()
    await client.start()
    logger.info("✅ Telethon conectado. Escuchando canal de señales...")

    @client.on(events.NewMessage(chats=[int(TELEGRAM_SIGNAL_CHANNEL_ID)]))
    async def handler(event):
        try:
            text = event.message.message or ""
            data = parse_message(text)
            if data:
                await send_message(f"🛰️ *Señal detectada*: #{data['pair']}/USDT ({data['direction']} x{data['leverage']})")
                # process_signal puede ser sync o async; soportamos ambos
                try:
                    res = process_signal(data)
                    if hasattr(res, "__await__"):
                        await res
                except Exception as e:
                    logger.error(f"❌ Error en process_signal(): {e}")
        except Exception as e:
            logger.error(f"❌ Error manejando mensaje de Telegram: {e}")

    await client.run_until_disconnected()
