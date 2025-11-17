"""
signal_manager.py — Procesador de señales del canal
---------------------------------------------------
- Limpia y extrae datos básicos de la señal (par, dirección, apalancamiento)
- Ejecuta el análisis avanzado con trend_system_final
- Envía reporte unificado a Telegram
- Guarda resultados en la base de datos
---------------------------------------------------
"""

import re
import logging
import asyncio
from typing import Optional, Dict, Any

from notifier import send_message
from trend_system_final import analyze_and_format
from database import save_signal, execute_query, fetch_all, fetch_one

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧼 Limpieza de texto
# ================================================================
def clean_signal_text(text: str) -> str:
    """
    Elimina emojis y caracteres no deseados.
    Conserva letras, números, ., -, /, _ y espacios.
    """
    return re.sub(r"[^\w\s/.\-]+", "", text or "")


# ================================================================
# 🔍 Extracción de datos de una señal
# ================================================================
def extract_basic_details(message: str) -> Optional[Dict[str, Any]]:
    """
    Extrae los datos esenciales de una señal del canal:
      - par (ATOMUSDT)
      - dirección (long/short)
      - leverage
      - entry
      - take profits []

    Retorna dict o None si falla.
    """
    try:
        if not message:
            return None

        raw = message.strip()
        cleaned = clean_signal_text(raw).upper()

        # Detectar par (#TRUTH/USDT, TRUTH-USDT, TRUTHUSDT)
        pair_match = re.search(r"#?([A-Z0-9]+)[/\-]?USDT", cleaned)
        direction_match = re.search(r"(LONG|SHORT)", cleaned)
        leverage_match = re.search(r"[xX](\d+)", cleaned)

        if not pair_match or not direction_match:
            logger.warning(f"⚠️ No se pudo extraer par o dirección: {raw}")
            return None

        pair = f"{pair_match.group(1)}USDT"
        direction = direction_match.group(1).lower()
        leverage = int(leverage_match.group(1)) if leverage_match else 20

        # Entry
        entry_match = re.search(r"ENTRY\s*[-:]\s*([0-9]*\.?[0-9]+)", raw, re.IGNORECASE)
        entry = float(entry_match.group(1)) if entry_match else None

        # Take profits
        take_profits = []
        tp_block = re.search(r"TAKE\-?PROFIT\s*:?(.*)", raw, re.IGNORECASE | re.DOTALL)
        if tp_block:
            block = tp_block.group(1)
            for num in re.findall(r"([0-9]*\.[0-9]+)", block):
                try:
                    take_profits.append(float(num))
                except ValueError:
                    pass

        details = {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
        }

        logger.info(
            f"🧩 Señal parseada: {pair} ({direction.upper()} x{leverage}) "
            f"Entry={entry} TP={take_profits}"
        )

        return details

    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de señal: {e}")
        return None


# ================================================================
# 📊 Procesador principal
# ================================================================
async def process_signal(signal_message: str):
    """
    Procesa una señal recibida desde Telegram:

      1. Extrae datos (par, dirección, apalancamiento…)
      2. Llama a trend_system_final.analyze_and_format
      3. Envía análisis a Telegram
      4. Guarda señal + análisis en la base de datos

    La decisión final (confirmada / esperar / parcial)
    proviene del motor trend_system_final.
    """
    try:
        details = extract_basic_details(signal_message)

        if not details:
            await asyncio.to_thread(
                send_message,
                "⚠️ No se pudo interpretar la señal recibida. Verifica el formato."
            )
            return

        pair = details["pair"]
        direction = details["direction"]
        leverage = details["leverage"]
        entry = details["entry"]
        take_profits = details["take_profits"]

        logger.info(f"📊 Procesando señal: {pair} ({direction.upper()} x{leverage})")

        # ============================================================
        # 🔍 1. Análisis técnico completo (motor unificado)
        # ============================================================
        result, report_message = analyze_and_format(pair, direction_hint=direction)

        # ============================================================
        # 📤 2. Enviar mensaje al usuario
        # (sin bloquear el loop principal)
        # ============================================================
        await asyncio.to_thread(send_message, report_message)

        # ============================================================
        # 💾 3. Guardar en DB
        # ============================================================
        record = {
            "pair": pair,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
            "match_ratio": result.get("match_ratio", 0.0),
            "recommendation": result.get("recommendation", "Sin datos"),
        }

        await save_signal(record)

        logger.info(
            f"💾 Señal guardada: {pair} — match={result.get('match_ratio', 0.0):.1f}% "
            f"| rec='{result.get('recommendation')}'"
        )

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await asyncio.to_thread(
            send_message,
            f"⚠️ Ocurrió un error procesando la señal: {e}"
        )

# ================================================================
# 📦 FUNCIONES PARA REACTIVACIÓN DE SEÑALES
# ================================================================

def get_pending_signals_for_reactivation():
    """
    Devuelve todas las señales que NO han sido reactivadas y cuya
    recomendación quedó como:
        - "⚠️ Esperar mejor entrada"
        - "🟡 Señal parcialmente confirmada"
        - "DESCARTAR"
    """
    query = """
        SELECT id, pair AS symbol, direction, leverage, entry, recommendation
        FROM signals
        WHERE reactivated = 0
        AND (
            LOWER(recommendation) LIKE '%esperar%'
            OR LOWER(recommendation) LIKE '%parcialmente%'
            OR LOWER(recommendation) LIKE '%descartar%'
        )
        ORDER BY id DESC;
    """
    return fetch_all(query)


def mark_signal_reactivated(signal_id: int):
    """
    Marca una señal como reactivada.
    """
    query = """
        UPDATE signals
        SET reactivated = 1,
            reactivated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
    """
    execute_query(query, (signal_id,))

