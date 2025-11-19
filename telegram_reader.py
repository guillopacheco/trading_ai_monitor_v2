"""
telegram_reader.py — versión FINAL integrada con trend_system_final
--------------------------------------------------------------------
Flujo oficial:
1) Detecta señales en el canal VIP (regex robustas)
2) Parsea símbolo, dirección, entrada, TPs, leverage
3) Guarda la señal en DB
4) Ejecuta análisis trend_system_final.analyze_and_format()
5) Envía reporte técnico formateado al usuario vía notifier.send_message()

Este módulo es el lector OFICIAL de señales.
--------------------------------------------------------------------
"""

import re
import logging
from telethon import events, TelegramClient

from config import (
    TELEGRAM_CHANNEL_ID,
)

from helpers import normalize_symbol, normalize_direction
from database import save_signal
from notifier import send_message
from trend_system_final import analyze_and_format


logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 Expresiones regulares robustas (Compatibles con tu canal)
# ============================================================

HEADER_REGEX = re.compile(
    r"#([A-Z0-9]+\/USDT)\s*\((Long|Short)",
    re.IGNORECASE
)

ENTRY_REGEX = re.compile(
    r"(Entry|Entrada)\s*[-:]\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE
)

LEV_REGEX = re.compile(
    r"x\s?(\d+)",
    re.IGNORECASE
)

TP_REGEX = re.compile(
    r"(TP\d?|🥉|🥈|🥇|🚀)\s*[:\-]?\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE
)


# ============================================================
# 🧩 Parser de señales detectadas
# ============================================================

def parse_signal(text: str):
    """
    Extrae datos de la señal del canal VIP.
    Retorna dict con la señal o None si no coincide.
    """

    header = HEADER_REGEX.search(text)
    if not header:
        return None

    symbol_raw = header.group(1)          # Ej: GIGGLE/USDT
    direction_raw = header.group(2)       # Long / Short

    entry_match = ENTRY_REGEX.search(text)
    if not entry_match:
        return None

    entry_price = float(entry_match.group(2))

    # Leverage
    lev_match = LEV_REGEX.search(text)
    leverage = int(lev_match.group(1)) if lev_match else 20

    # TP list
    tps = []
    for _, price in TP_REGEX.findall(text):
        if price:
            tps.append(float(price))

    # Normalizamos a mínimo 4 TP
    while len(tps) < 4:
        tps.append(None)

    symbol = normalize_symbol(symbol_raw)
    direction = normalize_direction(direction_raw)

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "leverage": leverage,
        "tps": tps,
        "raw": text,
    }


# ============================================================
# 💾 Guardar + análisis + notificación
# ============================================================

async def process_signal(parsed: dict):
    symbol = parsed["symbol"]
    direction = parsed["direction"]
    entry = parsed["entry_price"]
    lev = parsed["leverage"]
    tps = parsed["tps"]

    logger.info(f"📥 Nueva señal detectada: {symbol} ({direction}) x{lev}")

    # 1) Guardar señal en BD
    save_signal({
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "take_profits": tps,
        "leverage": lev,
        "recommendation": "",
        "match_ratio": 0.0,
    })

    # 2) Analizar con trend_system_final
    result, tech_msg = analyze_and_format(
        symbol=symbol,
        direction_hint=direction
    )

    # 3) Mensaje final al usuario
    msg = (
        f"📥 *Nueva señal detectada*\n"
        f"• **{symbol}** ({direction.upper()} x{lev})\n"
        f"• Entry: `{entry}`\n\n"
        f"🌀 *Análisis técnico inicial:* \n"
        f"{tech_msg}\n\n"
        f"📌 El sistema continuará monitoreando esta señal."
    )

    # 4) Enviar por Telegram (async)
    await send_message(msg)


# ============================================================
# 👂 Listener de Telethon
# ============================================================

def attach_listeners(client: TelegramClient):
    """
    Adjunta el listener al cliente Telethon.
    """

    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
    async def handler(event):
        text = event.message.message

        parsed = parse_signal(text)
        if not parsed:
            return

        try:
            await process_signal(parsed)
        except Exception as e:
            logger.error(f"❌ Error procesando señal: {e}")


# ============================================================
# 🚀 Activar lector
# ============================================================

def start_telegram_reader(client: TelegramClient):
    attach_listeners(client)
    logger.info("📡 Lector de señales activo y escuchando canal VIP.")
