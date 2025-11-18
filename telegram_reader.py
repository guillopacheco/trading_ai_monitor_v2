"""
telegram_reader.py
------------------------------------------------------------
Lector de señales desde el canal VIP (Telethon).

Funciones:
✔ Detecta señales tipo:
    🔥 #TRUTH/USDT (Long📈, x20)
    Entry - 0.03223
    🥉 0.03287
    🥈 0.03320
    🥇 0.03352
    🚀 0.03384

✔ Parseo robusto tolerante a variaciones.
✔ Guarda señal en DB nueva (tabla signals).
✔ Ejecuta análisis técnico inicial con trend_system_final.
✔ Envía reporte automático al usuario.

------------------------------------------------------------
"""

import re
import logging
from datetime import datetime

from telethon import events
from telethon.sync import TelegramClient

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_USER_ID,
)
from database import save_signal
from notifier import send_message
from trend_system_final import analyze_and_format

logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 Regex para detección de señales del canal
# ============================================================

SIGNAL_HEADER = re.compile(
    r"#([A-Z0-9]+\/USDT)\s*\((Long|Short)[^)]*\)",
    re.IGNORECASE
)

ENTRY_REGEX = re.compile(
    r"Entry\s*[-:]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE
)

TP_REGEX = re.compile(
    r"TP\d?\s*[:\-]\s*([0-9]*\.?[0-9]+)|🥉\s*([0-9]*\.?[0-9]+)|🥈\s*([0-9]*\.?[0-9]+)|🥇\s*([0-9]*\.?[0-9]+)|🚀\s*([0-9]*\.?[0-9]+)"
)

LEV_REGEX = re.compile(
    r"x(\d+)", re.IGNORECASE
)


# ============================================================
# 📥 Función principal: parsear señal
# ============================================================

def parse_signal(text: str):
    """
    Extrae:
    - symbol
    - direction
    - leverage
    - entry_price
    - take_profits (lista TP1–TP4)
    """
    header = SIGNAL_HEADER.search(text)
    if not header:
        return None

    symbol = header.group(1).replace("/", "")
    direction = header.group(2).lower()

    # Leverage
    lev_match = LEV_REGEX.search(text)
    leverage = int(lev_match.group(1)) if lev_match else 20

    # Entry
    entry_match = ENTRY_REGEX.search(text)
    if not entry_match:
        return None

    entry_price = float(entry_match.group(1))

    # TPs
    tps = []
    for match in TP_REGEX.findall(text):
        # match = tuple like ('0.0328','',...,'')
        for group in match:
            if group:
                tps.append(float(group))

    # Limitar a 4 TP
    tps = tps[:4]
    while len(tps) < 4:
        tps.append(None)

    result = {
        "symbol": symbol.upper(),
        "direction": direction,
        "leverage": leverage,
        "entry_price": entry_price,
        "tp1": tps[0],
        "tp2": tps[1],
        "tp3": tps[2],
        "tp4": tps[3],
        "raw": text,
    }

    return result



# ============================================================
# 💾 Guardar señal + análisis técnico
# ============================================================

def process_signal(parsed: dict):
    """
    Guarda en DB y ejecuta análisis inicial.
    """
    symbol = parsed["symbol"]
    direction = parsed["direction"]
    leverage = parsed["leverage"]
    entry = parsed["entry_price"]

    logger.info(f"📥 Nueva señal capturada: {symbol} ({direction}) x{leverage}")

    # 1) Guardar en DB
    save_signal(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        tp1=parsed["tp1"],
        tp2=parsed["tp2"],
        tp3=parsed["tp3"],
        tp4=parsed["tp4"],
        leverage=leverage,
        original_message=parsed["raw"]
    )

    # 2) Ejecutar análisis técnico inicial
    result, formatted = analyze_and_format(symbol, direction_hint=direction)

    # 3) Notificar por Telegram
    send_message(
        f"📥 *Nueva señal detectada: {symbol}*\n"
        f"📈 Dirección: *{direction.upper()}* x{leverage}\n"
        f"💵 Entry: {entry}\n"
        f"\n"
        f"{formatted}"
    )


# ============================================================
# 👂 Listener de Telethon
# ============================================================

def attach_listeners(client: TelegramClient):

    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
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
# 🚀 Inicializar lector
# ============================================================

def start_telegram_reader(client: TelegramClient):
    attach_listeners(client)
    logger.info("📡 Lector de señales activo y escuchando canal VIP.")
