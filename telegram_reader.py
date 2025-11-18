"""
telegram_reader.py
------------------------------------------------------------
Lector oficial de señales del canal VIP usando Telethon.

Funciones:
✔ Detecta mensajes de señales (GIGGLEUSDT, LONG, entry, TPs, leverage)
✔ Los guarda en la base de datos moderna
✔ Ejecuta el análisis técnico inicial
✔ Notifica al usuario con el reporte técnico
✔ Deja la señal en estado “pending” para reactivación

Requiere:
- config.TG_API_ID
- config.TG_API_HASH
- config.TG_SESSION
- config.TG_CHANNEL_SOURCE
------------------------------------------------------------
"""

import re
import logging
from datetime import datetime

from telethon import events
from telethon.sync import TelegramClient

from config import (
    TG_API_ID,
    TG_API_HASH,
    TG_SESSION,
    TG_CHANNEL_SOURCE,
)

from signal_manager_db import save_new_signal
from trend_system_final import analyze_and_format
from notifier import send_message


logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 REGEX robusto para parsear señales
# ============================================================

HEADER = re.compile(
    r"#([A-Z0-9]+\/USDT)\s*\((Long|Short).*?x(\d+)\)",
    re.IGNORECASE
)

ENTRY = re.compile(r"Entry\s*[-:]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)

TP = re.compile(
    r"TP\d?\s*[:\-]\s*([0-9]*\.?[0-9]+)|🥉\s*([0-9]*\.?[0-9]+)|🥈\s*([0-9]*\.?[0-9]+)|🥇\s*([0-9]*\.?[0-9]+)|🚀\s*([0-9]*\.?[0-9]+)"
)


# ============================================================
# 🧩 Parseo de señal
# ============================================================

def parse_signal(text: str):
    header = HEADER.search(text)
    if not header:
        return None

    raw_symbol = header.group(1)
    direction = header.group(2).lower()
    leverage = int(header.group(3))

    symbol = raw_symbol.replace("/", "").upper()

    # Entry
    m_entry = ENTRY.search(text)
    if not m_entry:
        return None

    entry_price = float(m_entry.group(1))

    # TPs
    tps = []
    for t in TP.findall(text):
        for v in t:
            if v:
                tps.append(float(v))

    tps = tps[:4]
    while len(tps) < 4:
        tps.append(None)

    return {
        "symbol": symbol,
        "direction": direction,
        "leverage": leverage,
        "entry_price": entry_price,
        "tp1": tps[0],
        "tp2": tps[1],
        "tp3": tps[2],
        "tp4": tps[3],
        "raw": text,
    }


# ============================================================
# 💾 Guardar señal + análisis inicial
# ============================================================

def process_signal(parsed: dict):
    symbol = parsed["symbol"]
    direction = parsed["direction"]
    leverage = parsed["leverage"]

    logger.info(f"📥 Señal capturada: {symbol} ({direction.upper()}) x{leverage}")

    # 1) Guardar señal en DB principal
    signal_id = save_new_signal(
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        entry_price=parsed["entry_price"],
        tp1=parsed["tp1"],
        tp2=parsed["tp2"],
        tp3=parsed["tp3"],
        tp4=parsed["tp4"],
        original_message=parsed["raw"]
    )

    # 2) Ejecutar análisis técnico inicial
    result, report = analyze_and_format(
        symbol,
        direction_hint=direction
    )

    # 3) Enviar mensaje al usuario
    send_message(
        f"📥 *Nueva señal detectada: {symbol}*\n"
        f"📌 Dirección: *{direction.upper()}* x{leverage}\n"
        f"💵 Entry: {parsed['entry_price']}\n\n"
        f"{report}"
    )

    return signal_id


# ============================================================
# 👂 Listener de Telethon
# ============================================================

def attach_listeners(client: TelegramClient):

    @client.on(events.NewMessage(chats=[TG_CHANNEL_SOURCE]))
    async def handler(event):
        text = event.message.message

        parsed = parse_signal(text)
        if not parsed:
            return

        try:
            process_signal(parsed)
        except Exception as e:
            logger.error(f"❌ Error procesando señal: {e}")


# ============================================================
# 🚀 Iniciar lector
# ============================================================

async def start_telegram_reader():
    client = TelegramClient(
        TG_SESSION,
        TG_API_ID,
        TG_API_HASH
    )

    await client.start()

    attach_listeners(client)
    logger.info("📡 Lector de señales activo en Telethon.")

    await client.run_until_disconnected()
