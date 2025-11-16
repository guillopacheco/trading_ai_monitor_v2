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
    Conserva letras, números, /, -, _, ., espacios y saltos de línea.
    """
    return re.sub(r"[^\w\s/.\-]+", "", text)


def extract_basic_details(message: str) -> Optional[Dict[str, Any]]:
    """
    Extrae información básica de una señal de futuros, por ejemplo:

      🔥 #AT/USDT (Short📉, x20) 🔥
      Entry - 0.3053
      Take-Profit:
      🥉 0.2992 (40% of profit)
      🥈 0.2961 (60% of profit)
      🥇 0.2931 (80% of profit)
      🚀 0.29 (100% of profit)

    Devuelve:
      {
        "pair": "ATUSDT",
        "direction": "short",
        "leverage": 20,
        "entry": 0.3053,
        "take_profits": [0.2992, 0.2961, 0.2931, 0.29],
      }
    """
    try:
        raw = message or ""
        upper_raw = raw.upper()

        # Versión limpia para evitar que emojis rompan regex de #PAR/USDT
        cleaned = clean_signal_text(upper_raw)

        # Par: #PIPPIN/USDT, PIPPIN-USDT, PIPPINUSDT
        pair_match = re.search(r"#?([A-Z0-9]+)[/\\-]?USDT", cleaned)
        direction_match = re.search(r"(LONG|SHORT)", cleaned)
        leverage_match = re.search(r"[xX](\d+)", cleaned)

        if not pair_match or not direction_match:
            logger.warning(f"⚠️ Señal no reconocida o incompleta: {message}")
            return None

        pair = f"{pair_match.group(1)}USDT"
        direction = direction_match.group(1).lower()
        leverage = int(leverage_match.group(1)) if leverage_match else 20

        # Entry (usamos el mensaje original para conservar decimales exactos)
        entry_match = re.search(r"Entry\s*[-:]\s*([0-9]*\.?[0-9]+)", raw, re.IGNORECASE)
        entry = float(entry_match.group(1)) if entry_match else None

        # Take Profits: números decimales después de "Take-Profit"
        take_profits: list[float] = []
        tp_block = re.search(r"Take-Profit\s*:?(.*)", raw, re.IGNORECASE | re.DOTALL)
        if tp_block:
            block_text = tp_block.group(1)
            for num in re.findall(r"([0-9]*\.[0-9]+)", block_text):
                try:
                    take_profits.append(float(num))
                except ValueError:
                    continue

        details = {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
        }

        logger.info(
            f"🧩 Señal parseada: {details['pair']} "
            f"({details['direction'].upper()} x{details['leverage']}) "
            f"Entry={details['entry']} TP={details['take_profits']}"
        )

        return details

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
      1. Extrae par / dirección / apalancamiento / entry / TPs
      2. Llama a trend_system_final.analyze_and_format(...)
      3. Envía el reporte a Telegram
      4. Guarda el resultado en la base de datos (tabla signals)

    NOTA:
      - La lógica de "pendiente / descartar / confirmar" se basa en el texto
        de `recommendation` devuelto por trend_system_final.
      - El módulo signal_reactivation_sync revisa esas recomendaciones para
        decidir si una señal puede reactivarse después.
    """
    try:
        details = extract_basic_details(signal_message)
        if not details:
            await asyncio.to_thread(
                send_message,
                "⚠️ No se pudo interpretar la señal recibida. Revisa el formato o el canal.",
            )
            return

        pair = details["pair"]
        direction = details["direction"]
        leverage = details["leverage"]
        entry = details.get("entry")
        take_profits = details.get("take_profits", [])

        logger.info(f"📊 Analizando señal: {pair} ({direction.upper()} x{leverage})")

        # 🔍 Análisis técnico avanzado (motor unificado)
        result, report = analyze_and_format(pair, direction_hint=direction)

        # 📤 Enviar el reporte al usuario (sin bloquear el loop principal)
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
            f"({direction.upper()} x{leverage}) — "
            f"match={result.get('match_ratio', 0.0):.2f}% | "
            f"rec='{result.get('recommendation', '')}'"
        )

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await asyncio.to_thread(
            send_message,
            f"⚠️ Error analizando la señal: {e}",
        )
