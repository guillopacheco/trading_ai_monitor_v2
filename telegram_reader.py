# telegram_reader.py
import asyncio
import logging
import re
from telethon import TelegramClient, events
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION,
    TELEGRAM_SIGNAL_CHANNEL_ID,
)
from notifier import send_message, notify_profit_update

logger = logging.getLogger("telegram_reader")

# ---------------------------
# Parsers
# ---------------------------

PAIR_RE = re.compile(r"#?([A-Z0-9]+)\s*/\s*([A-Z]{3,5})")
DIR_RE = re.compile(r"\b(Long|Short)\b", re.IGNORECASE)
LEV_RE = re.compile(r"x\s?(\d{1,3})")
ENTRY_RE = re.compile(r"(?:Entry\s*[-:]?\s*)([0-9]*\.?[0-9]+)", re.IGNORECASE)

PROFIT_UPDATE_RE = re.compile(
    r"^#?[A-Z0-9]+/USDT.*?(?:Price\s*[-:]\s*[0-9]*\.?[0-9]+).*?(?:Profit\s*[-:]\s*\d+%)",
    re.IGNORECASE | re.DOTALL,
)

def parse_signal_text(text: str):
    """
    Devuelve dict con {pair, direction, entry, leverage} o None si no es señal válida.
    """
    # Detectar y descartar profit updates
    if PROFIT_UPDATE_RE.search(text):
        return {"type": "profit_update"}

    m_pair = PAIR_RE.search(text)
    m_dir = DIR_RE.search(text)
    m_lev = LEV_RE.search(text)
    m_ent = ENTRY_RE.search(text)

    if not (m_pair and m_dir and m_ent):
        return None

    base, quote = m_pair.group(1), m_pair.group(2)
    direction = m_dir.group(1).lower()
    entry = float(m_ent.group(1))
    leverage = int(m_lev.group(1)) if m_lev else 0

    return {
        "type": "signal",
        "pair": f"{base}{quote}".upper(),  # NORMALIZADO A SIN '/'
        "direction": direction,
        "entry": entry,
        "leverage": leverage,
    }

# ---------------------------
# Runner
# ---------------------------

async def start_telegram_reader():
    """
    Inicia el lector de señales (async). No recibe callback por compatibilidad con tu main.py actual.
    Llama internamente a signal_manager.process_signal sin await (desde un hilo).
    """
    from signal_manager import process_signal  # import diferido para evitar ciclos

    chat_id = int(str(TELEGRAM_SIGNAL_CHANNEL_ID).replace(" ", ""))

    logger.info("📡 TelegramSignalReader iniciado en modo escucha...")

    client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start(phone=TELEGRAM_PHONE)

    me = await client.get_me()
    logger.info(f"✅ Conectado como {me.first_name} ({me.id})")

    @client.on(events.NewMessage(chats=chat_id))
    async def handler(event):
        try:
            text = (event.message.message or "").strip()
            if not text:
                return

            logger.info(f"📥 Señal recibida ({event.message.date}):\n{text[:120]}{'...' if len(text)>120 else ''}")

            parsed = parse_signal_text(text)
            if not parsed:
                logger.debug("ℹ️ Mensaje ignorado (no coincide con formato de señal).")
                return

            if parsed.get("type") == "profit_update":
                # No relanzar análisis; solo notificar opcionalmente.
                notify_profit_update(text)
                return

            # Señal válida → procesar en hilo sync
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, process_signal, {
                "pair": parsed["pair"],
                "direction": parsed["direction"],
                "entry": parsed["entry"],
                "leverage": parsed["leverage"],
                "timestamp": str(event.message.date)
            })

        except Exception as e:
            logger.error(f"❌ Error en handler de señales: {e}")
            send_message(f"⚠️ Error leyendo una señal: {e}")

    await client.run_until_disconnected()
