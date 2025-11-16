# signal_manager.py — Procesador de señales del canal
# ---------------------------------------------------
# - Limpia y extrae datos básicos de la señal (par, dirección, apalancamiento)
# - Ejecuta el análisis avanzado con trend_system_final.analyze_and_format
# - Envía resumen a Telegram
# - Guarda el resultado en la base de datos (signals)
# ---------------------------------------------------

import re
import logging
import asyncio
from typing import Optional, Dict, Any

from notifier import send_message
from trend_system_final import analyze_and_format
from database import save_signal

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧠 Limpieza y extracción de señales
# ================================================================
def clean_signal_text(text: str) -> str:
    """
    Elimina emojis y caracteres raros para facilitar regex.
    """
    # Permitimos letras, números, /, -, _, ., espacio y saltos de línea
    return re.sub(r"[^\w\s/.\-]+", "", text)


def extract_basic_details(message: str) -> Optional[Dict[str, Any]]:
    """
    Extrae:
      - pair (ej: RESOLVUSDT)
      - direction (long/short)
      - leverage (int, default 20)
    """
    try:
        raw = message.upper()
        txt = clean_signal_text(raw)

        pair_match = re.search(r"#?([A-Z0-9]+)[/\\-]?USDT", raw)
        direction_match = re.search(r"(LONG|SHORT)", raw)
        leverage_match = re.search(r"[xX](\d+)", raw)

        if not pair_match or not direction_match:
            logger.warning(f"⚠️ Señal no reconocida: {message}")
            return None

        pair = f"{pair_match.group(1)}USDT"
        direction = direction_match.group(1).lower()
        leverage = int(leverage_match.group(1)) if leverage_match else 20

        # Entry
        entry_match = re.search(r"Entry\s*[-:]\s*([0-9]*\.?[0-9]+)", message, re.IGNORECASE)
        entry = float(entry_match.group(1)) if entry_match else None

        # Take Profits (bloque después de "Take-Profit:")
        take_profits = []
        tp_block = re.search(r"Take-Profit\s*:?(.*)", message, re.IGNORECASE | re.DOTALL)
        if tp_block:
            block_text = tp_block.group(1)
            for num in re.findall(r"([0-9]*\.[0-9]+)", block_text):
                try:
                    take_profits.append(float(num))
                except ValueError:
                    continue

        return {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
        }

    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de señal: {e}")
        return None


# ================================================================
# 📊 Procesamiento de señales
# ================================================================
async def process_signal(signal_message: str):
    """
    Analiza una señal recibida desde Telegram y envía una recomendación.

    Flujo:
      1. Extrae par/dirección/apalancamiento/entry/TPs
      2. Llama a trend_system_final.analyze_and_format(...)
      3. Envía el reporte a Telegram
      4. Guarda el resultado en la base de datos (tabla signals)
    """
    try:
        details = extract_basic_details(signal_message)
        if not details:
            await asyncio.to_thread(
                send_message, "⚠️ No se pudo interpretar la señal recibida."
            )
            return

        pair = details["pair"]
        direction = details["direction"]
        leverage = details["leverage"]
        entry = details.get("entry")
        take_profits = details.get("take_profits", [])

        logger.info(f"📊 Analizando señal: {pair} ({direction.upper()} x{leverage})")

        # 🔍 Análisis técnico avanzado
        result, report = analyze_and_format(pair, direction_hint=direction)

        # 📤 Enviar el reporte al usuario
        await asyncio.to_thread(send_message, report)

        # 💾 Guardar en DB
        signal_record = {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
            "match_ratio": result.get("match_ratio", 0.0),
            "recommendation": result.get("recommendation", "Sin datos"),
        }
        await save_signal(signal_record)

        logger.info(
            f"💾 Señal procesada y guardada: {pair} "
            f"({direction.upper()} x{leverage}) — match={result.get('match_ratio', 0.0):.2f}%"
        )

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await asyncio.to_thread(
            send_message, f"⚠️ Error analizando la señal: {e}"
        )
