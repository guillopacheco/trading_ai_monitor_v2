"""
telegram_reader.py — versión final integrada
------------------------------------------------------------
Lector avanzado para señales del canal VIP (Telethon).

Flujo:
1) Detecta señales con expresiones regulares robustas.
2) Las parsea en un dict uniforme.
3) Guarda la señal en DB usando save_signal().
4) Ejecuta análisis técnico inicial mediante technical_brain.
5) Envía reporte técnico completo al usuario.

Este módulo trabaja SOLO con el motor technical_brain,
no usa trend_system_final.
------------------------------------------------------------
"""

import re
import logging
from telethon import events
from telethon.sync import TelegramClient

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SIGNAL_CHANNEL_ID,
    TELEGRAM_USER_ID,
)

from database import save_signal
from notifier import send_message
from technical_brain import analyze_for_entry

logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 Expresiones regulares para detectar señales
# ============================================================

HEADER_REGEX = re.compile(
    r"#([A-Z0-9]+/USDT)\s*\((Long|Short)[^)]+\)",
    re.IGNORECASE
)

ENTRY_REGEX = re.compile(
    r"Entry\s*[-:]\s*([0-9]*\.?[0-9]+)",
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

    symbol = header.group(1).replace("/", "")
    direction = header.group(2).lower()

    entry_match = ENTRY_REGEX.search(text)
    if not entry_match:
        return None

    entry_price = float(entry_match.group(1))

    # Leverage
    lev_match = LEV_REGEX.search(text)
    leverage = int(lev_match.group(1)) if lev_match else 20

    # TPs
    tps = []
    for _, price in TP_REGEX.findall(text):
        if price:
            tps.append(float(price))

    # Limitar a 4 TP
    while len(tps) < 4:
        tps.append(None)

    return {
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


# ============================================================
# 💾 Guardar + análisis técnico + notificación
# ============================================================

async def process_signal(parsed: dict):
    symbol = parsed["symbol"]
    direction = parsed["direction"]
    entry = parsed["entry_price"]
    lev = parsed["leverage"]

    logger.info(f"📥 Nueva señal detectada: {symbol} ({direction}) x{lev}")

    # 1) Guardar en DB
    save_signal(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        tp1=parsed["tp1"],
        tp2=parsed["tp2"],
        tp3=parsed["tp3"],
        tp4=parsed["tp4"],
        leverage=lev,
        original_message=parsed["raw"]
    )

    # 2) Análisis técnico inicial usando technical_brain
    analysis = analyze_for_entry(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        leverage=lev
    )

    # 3) Preparar mensaje para el usuario
    msg = [
        f"📥 *Nueva señal detectada: {symbol}*",
        f"📈 Dirección: *{direction.upper()}* x{lev}",
        f"💵 Entry: {entry}",
        "",
        "📊 *Tendencias:*",
        f"• 1m: {analysis['trend_multi']['1m']}",
        f"• 5m: {analysis['trend_multi']['5m']}",
        f"• 15m: {analysis['trend_multi']['15m']}",
        f"• 1h: {analysis['trend_multi']['1h']}",
        "",
        "🧪 *Divergencias:*",
        f"• RSI: {analysis['divergences']['RSI']}",
        f"• MACD: {analysis['divergences']['MACD']}",
        "",
        f"🌡️ ATR: {analysis['atr']}",
        "",
        f"🔎 Sesgo corto: {analysis['short_bias']}",
        "",
        f"🧠 *Conclusión técnica:* {analysis['summary']}",
        "",
        "📌 Si el mercado confirma condiciones favorables, el monitor automático sugerirá entrada óptima."
    ]

    await send_message("\n".join(msg))


# ============================================================
# 👂 Listener de Telethon
# ============================================================

def attach_listeners(client: TelegramClient):
    @client.on(events.NewMessage(chats=[TELEGRAM_SIGNAL_CHANNEL_ID]))
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
