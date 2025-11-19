"""
telegram_reader.py — versión final integrada con trend_system_final
--------------------------------------------------------------------
Flujo:
1) Detecta señales con regex robustas del canal VIP.
2) Parsea símbolo, dirección, entry, leverage, TP.
3) Guarda la señal en DB con database.save_signal().
4) Llama al motor técnico trend_system_final.analyze_and_format().
5) Envía reporte técnico al usuario por Telegram.

Este módulo es el lector OFICIAL de señales.
--------------------------------------------------------------------
"""

import re
import logging
import asyncio
from telethon import events, TelegramClient

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
)

from helpers import normalize_symbol, normalize_direction
from database import save_signal
from notifier import send_message
from trend_system_final import analyze_and_format


logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 Expresiones regulares robustas
# ============================================================

HEADER_REGEX = re.compile(
    r"#([A-Z0-9]+/USDT)\s*\((Long|Short)[^)]+\)",
    re.IGNORECASE
)

ENTRY_REGEX = re.compile(
    r"(Entry|Entrada)\s*[-:]\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE
)

LEV_REGEX = re.compile(
    r"x(\d+)",
    re.IGNORECASE
)

TP_REGEX = re.compile(
    r"(TP\d?|🥉|🥈|🥇|🚀)\s*[:\-]?\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE
)


# ============================================================
# 🧩 Parser de señales del canal
# ============================================================

def parse_signal(text: str):
    header = HEADER_REGEX.search(text)
    if not header:
        return None

    symbol_raw = header.group(1)          # Ej: GIGGLE/USDT
    direction_raw = header.group(2)       # Long / Short

    entry_match = ENTRY_REGEX.search(text)
    if not entry_match:
        return None

    entry_price = float(entry_match.group(2))

    lev_match = LEV_REGEX.search(text)
    leverage = int(lev_match.group(1)) if lev_match else 20

    # Extraer TPs
    tps = []
    for _, price in TP_REGEX.findall(text):
        if price:
            tps.append(float(price))

    # Normalizar mínimo 4 TP
    while len(tps) < 4:
        tps.append(None)

    # Normalizar símbolo y dirección
    symbol = normalize_symbol(symbol_raw)
    direction = normalize_direction(direction_raw)

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "leverage": leverage,
        "tp": tps,
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
    tps = parsed["tp"]
    raw = parsed["raw"]

    logger.info(f"📥 Nueva señal detectada: {symbol} ({direction}) x{lev}")

    # 1) Guardar señal en BD usando database.save_signal
    save_signal({
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "take_profits": tps,
        "leverage": lev,
        "recommendation": "",
        "match_ratio": 0.0,  # se actualiza con análisis
    })

    # 2) Ejecutar análisis técnico con trend_system_final
    result, tech_msg = analyze_and_format(
        symbol=symbol,
        direction_hint=direction
    )

    match_ratio = result.get("match_ratio", 0.0)
    recommendation = result.get("recommendation", "")

    # 3) Preparar mensaje final al usuario
    msg = [
        f"📥 *Nueva señal detectada*: **{symbol}**",
        f"📈 Dirección: *{direction.upper()}* x{lev}",
        f"💵 Entry: `{entry}`",
        "",
        "🌀 *Análisis técnico inicial:*",
        tech_msg,
        "",
        "📌 El monitor automático seguirá evaluando condiciones óptimas "
        "para entrada y reactivación.",
    ]

    # 4) Enviar por Telegram (función síncrona → usar to_thread)
    await asyncio.to_thread(send_message, "\n".join(msg))


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
            await process_signal(parsed)
        except Exception as e:
            logger.error(f"❌ Error procesando señal: {e}")


# ============================================================
# 🚀 Inicializar lector
# ============================================================

def start_telegram_reader(client: TelegramClient):
    attach_listeners(client)
    logger.info("📡 Lector de señales activo y escuchando canal VIP.")
