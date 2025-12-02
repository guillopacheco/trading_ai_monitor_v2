"""
telegram_reader.py — lector OFICIAL de señales NeuroTrader
--------------------------------------------------------------------
Flujo:
1) Detecta señales con regex robustas del canal VIP.
2) Parsea símbolo, dirección, entry, leverage, TP.
3) Guarda la señal en DB con database.save_signal().
4) Llama al motor técnico (motor_wrapper.analyze_for_signal).
5) Envía reporte técnico + entrada inteligente al usuario por Telegram.

IMPORTANTE:
- notifier.send_message es SINCRÓNICO.
- Aquí SIEMPRE se usa: await asyncio.to_thread(send_message, texto)
--------------------------------------------------------------------
"""

import re
import logging
import asyncio
from telethon import events, TelegramClient

from services.technical_engine.motor_wrapper import (
    analyze_for_signal,
    analyze_and_format,
)
from services.signals_service.signal_manager_db import save_signal
from services.telegram_service.notifier import send_message

from core.helpers import normalize_symbol, normalize_direction

logger = logging.getLogger("telegram_reader")


# ============================================================
# 🔍 Expresiones regulares robustas
# ============================================================
HEADER_REGEX = re.compile(
    r"#([A-Z0-9]+/USDT)\s*\((Long|Short)[^)]+\)",
    re.IGNORECASE,
)

ENTRY_REGEX = re.compile(
    r"(Entry|Entrada)\s*[-:]\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)

LEV_REGEX = re.compile(
    r"x(\d+)",
    re.IGNORECASE,
)

TP_REGEX = re.compile(
    r"(TP\d?|🥉|🥈|🥇|🚀)\s*[:\-]?\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)


# ============================================================
# 🧩 Parser de señales del canal
# ============================================================
def parse_signal(text: str):
    """
    Extrae:
      - symbol: 'HEIUSDT', '4USDT', etc. (normalizado)
      - direction: 'long' / 'short'
      - entry_price: float
      - leverage: int
      - tp: lista de TPs [tp1, tp2, tp3, tp4]
    Devuelve dict o None si el texto no parece ser una señal válida.
    """
    header = HEADER_REGEX.search(text)
    if not header:
        return None

    symbol_raw = header.group(1)          # Ej: HEI/USDT
    direction_raw = header.group(2)       # Long / Short

    entry_match = ENTRY_REGEX.search(text)
    if not entry_match:
        logger.debug("📭 Señal ignorada: no se encontró Entry.")
        return None

    try:
        entry_price = float(entry_match.group(2))
    except Exception:
        logger.debug("📭 Señal ignorada: Entry no numérico.")
        return None

    lev_match = LEV_REGEX.search(text)
    leverage = int(lev_match.group(1)) if lev_match else 20

    # Extraer TPs
    tps = []
    for _, price in TP_REGEX.findall(text):
        if price:
            try:
                tps.append(float(price))
            except Exception:
                continue

    # Normalizar TPs (hasta 4, con None de relleno si faltan)
    while len(tps) < 4:
        tps.append(None)
    if len(tps) > 4:
        tps = tps[:4]

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
    """
    Flujo completo para una señal ya parseada.
    Compatible con el motor único 2025.
    """

    symbol = parsed["symbol"]
    direction = parsed["direction"]
    entry = parsed["entry_price"]
    lev = parsed["leverage"]
    tps = parsed["tp"]

    logger.info(f"📥 Nueva señal detectada: {symbol} ({direction}) x{lev}")

    # 1) Guardar señal en BD
    try:
        save_signal({
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry,
            "take_profits": tps,
            "leverage": lev,
            "recommendation": "",
            "match_ratio": 0.0,
        })
    except Exception as e:
        logger.error(f"❌ Error guardando señal en DB: {e}")

    # 2) Ejecutar análisis técnico
    #    ⚠️ analyze_for_signal ahora devuelve SOLO EL RESULTADO, NO tech_msg
    try:
        result = analyze_for_signal(symbol=symbol, direction=direction)
    except Exception as e:
        logger.error(f"❌ Error en análisis técnico para {symbol}: {e}")
        result = {"allowed": False, "decision": "error"}

    # 3) Mensaje técnico formateado (texto extendido)
    try:
        tech_msg = analyze_and_format(symbol, direction)
    except Exception as e:
        logger.error(f"❌ Error formateando análisis técnico: {e}")
        tech_msg = "❌ Error generando análisis técnico."

    # ------------------------------------------------------------------
    # 🧠 BLOQUE DE ENTRADA INTELIGENTE
    # ------------------------------------------------------------------
    entry_score = result.get("entry_score")
    entry_grade = result.get("entry_grade")
    entry_mode = result.get("entry_mode")
    entry_allowed = result.get("entry_allowed", True)

    # Línea de calidad
    if entry_grade and entry_score is not None:
        calidad_line = f"🎯 Calidad de entrada: *{entry_grade}* ({entry_score:.0f} pts)"
    elif entry_grade:
        calidad_line = f"🎯 Calidad de entrada: *{entry_grade}*"
    elif entry_score is not None:
        calidad_line = f"🎯 Calidad de entrada: {entry_score:.0f} pts"
    else:
        calidad_line = "🎯 Calidad de entrada: _sin evaluar_"

    # Modo sugerido
    modo_line = f"🧭 Modo sugerido: *{entry_mode}*" if entry_mode else ""

    # Estado de riesgo
    estado_line = (
        "✅ Estado: *Apta* (sin bloqueo automático)"
        if entry_allowed
        else "⚠️ Estado: *Riesgo alto* (entrada desaconsejada)"
    )

    entry_block = [
        "🧠 *Entrada inteligente:*",
        calidad_line,
    ]
    if modo_line:
        entry_block.append(modo_line)
    entry_block.append(estado_line)

    # ------------------------------------------------------------------
    # 4) Mensaje final para Telegram
    # ------------------------------------------------------------------
    msg_lines = [
        f"📥 *Nueva señal detectada*: **{symbol}**",
        f"📈 Dirección: *{direction.upper()}* x{lev}",
        f"💵 Entry: `{entry}`",
        "",
        "🌀 *Análisis técnico del mercado:*",
        tech_msg,
        "",
        *entry_block,
        "",
        "📌 El monitor automático seguirá evaluando condiciones óptimas ",
        "para entrada, reactivación y posibles reversiones.",
    ]

    final_msg = "\n".join(msg_lines)

    # 5) Enviar por Telegram
    try:
        await asyncio.to_thread(send_message, final_msg)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje de señal: {e}")

# ============================================================
# 👂 Listener de Telethon
# ============================================================
def attach_listeners(client: TelegramClient):
    """
    Registra el listener de nuevas señales sobre el canal VIP
    definido en TELEGRAM_CHANNEL_ID.
    """

    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
    async def handler(event):
        text = event.message.message or ""
        parsed = parse_signal(text)

        if not parsed:
            return  # Mensaje que no es señal

        try:
            await process_signal(parsed)
        except Exception as e:
            logger.error(f"❌ Error procesando señal del canal: {e}")


# ============================================================
# 🚀 Inicializar lector
# ============================================================
def start_telegram_reader(client: TelegramClient):
    attach_listeners(client)
    logger.info("📡 Lector de señales activo y escuchando canal VIP.")
