"""
signal_manager.py (sincronizado 2025)
-------------------------------------
Gestión de señales Telegram → Análisis técnico → Recomendación.
Integrado con indicators.py y bybit_client_v13_signals_fix.py.
"""

import re
import logging
import asyncio
from indicators import get_technical_data
from notifier import send_message

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧠 Limpieza y extracción de señales
# ================================================================
def clean_signal_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9/._-]", "", text)
    return text.replace(" ", "").strip()


def extract_signal_details(message: str):
    """Extrae par, dirección y apalancamiento de la señal."""
    try:
        msg = clean_signal_text(message.upper())
        pair_match = re.search(r"#?([A-Z0-9]+)[/\\-]?USDT", msg)
        direction_match = re.search(r"(LONG|SHORT)", msg)
        leverage_match = re.search(r"X(\d+)", msg)

        if not pair_match or not direction_match:
            logger.warning(f"⚠️ Señal no reconocida: {message}")
            return None

        pair = f"{pair_match.group(1)}USDT"
        direction = direction_match.group(1).lower()
        leverage = int(leverage_match.group(1)) if leverage_match else 20
        return pair, direction, leverage

    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de señal: {e}")
        return None


# ================================================================
# 📊 Procesamiento de señales
# ================================================================
async def process_signal(signal_message: str):
    """Analiza una señal recibida desde Telegram y envía una recomendación."""
    try:
        details = extract_signal_details(signal_message)
        if not details:
            await send_message("⚠️ No se pudo interpretar la señal recibida.")
            return

        pair, direction, leverage = details
        logger.info(f"📊 Analizando señal: {pair} ({direction.upper()} x{leverage})")

        data = get_technical_data(pair, intervals=["1m", "5m", "15m"])
        if not data:
            await send_message(f"⚠️ No se pudieron obtener indicadores para {pair}")
            return

        summary = []
        matches = 0
        for tf, res in data.items():
            trend = res.get("trend", "indefinida").lower()
            summary.append(f"🔹 **{tf}m:** {trend.upper()}")
            if direction in trend:
                matches += 1

        recommendation = (
            "✅ Señal confirmada por la tendencia." if matches >= 2 else "⚠️ Señal no confirmada por indicadores."
        )

        message = (
            f"📊 **Análisis de {pair}**\n"
            + "\n".join(summary)
            + f"\n📌 **Recomendación:** {recommendation}"
        )
        await send_message(message)

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await send_message(f"⚠️ Error analizando la señal: {e}")
