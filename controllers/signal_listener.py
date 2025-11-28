"""
signal_listener.py
-------------------
Listener oficial para señales del canal VIP.

Este módulo recibe textos crudos desde telegram_service,
los parsea en una estructura limpia y profesional, 
y luego delega el análisis al signal_controller.

Flujo:
    telegram_service → signal_listener → signal_controller → DB / motor técnico / notificaciones

Este módulo NO habla con Bybit ni con la DB directamente.
"""

import re
import logging

from controllers.signal_controller import process_new_signal
from services.telegram_service import send_message

logger = logging.getLogger("signal_listener")


# ============================================================
# 🔵 PARSER DE SEÑALES (PROFESIONAL)
# ============================================================
def parse_signal_text(text: str):
    """
    Convierte una señal textual del canal VIP en una estructura limpia:

    {
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry": 42000.0,
        "tp_list": [43000, 44000, 45000],
        "sl": 40000,
        "raw": "texto original"
    }
    """

    original = text

    # -------------------------------
    # Dirección
    # -------------------------------
    direction = None
    if "long" in text.lower():
        direction = "long"
    elif "short" in text.lower():
        direction = "short"

    # -------------------------------
    # Símbolo
    # -------------------------------
    # Ej: #GIGGLE/USDT  → GIGGLEUSDT
    symbol_match = re.search(r"#?([A-Za-z0-9]+)\/?USDT", text)
    symbol = None

    if symbol_match:
        base = symbol_match.group(1).upper()
        symbol = base + "USDT"

    # -------------------------------
    # Entry
    # -------------------------------
    entry_re = re.findall(r"Entry\s*[-:]?\s*([0-9]*\.?[0-9]+)", text, re.IGNORECASE)
    entry = float(entry_re[0]) if entry_re else None

    # -------------------------------
    # Take Profits
    # -------------------------------
    tp_matches = re.findall(r"([0-9]*\.?[0-9]+)\s*\(", text)
    tp_values = []

    for val in tp_matches:
        try:
            tp_values.append(float(val))
        except:
            pass

    # Limpiar duplicados
    tp_list = sorted(list(set(tp_values)))

    # -------------------------------
    # Stop Loss
    # -------------------------------
    sl_match = re.search(r"SL\s*:?[- ]*\s*([0-9]*\.?[0-9]+)", text, re.IGNORECASE)
    sl = float(sl_match.group(1)) if sl_match else None

    # -------------------------------
    # Estructura final
    # -------------------------------
    parsed = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp_list": tp_list,
        "sl": sl,
        "raw": original,
    }

    return parsed


# ============================================================
# 🔵 CALLBACK PRINCIPAL PARA TELEGRAM_SERVICE
# ============================================================
async def on_new_signal(text: str):
    """
    Handler llamado por telegram_service al recibir un mensaje del canal VIP.
    """

    try:
        parsed = parse_signal_text(text)

        if not parsed["symbol"] or not parsed["direction"]:
            logger.warning("⚠️ Señal recibida pero no válida.")
            await send_message("⚠️ Señal recibida, pero no se pudo interpretar correctamente.")
            return

        logger.info(f"📥 Señal interpretada: {parsed}")
        await send_message(f"📥 Nueva señal detectada: {parsed['symbol']} ({parsed['direction']})\nAnalizando…")

        await process_new_signal(parsed)

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await send_message("❌ Error interno procesando la señal.")


# ============================================================
# 🔵 INTEGRACIÓN FÁCIL CON telegram_service
# ============================================================
async def connect_to_telegram_signals():
    """
    Llama al listener oficial de señales.
    Úsalo desde main.py o desde un inicializador central.
    """
    from services.telegram_service import start_signal_listener
    await start_signal_listener(on_new_signal)


# ============================================================
# 🔵 TEST LOCAL
# ============================================================
if __name__ == "__main__":
    test_text = """
    🔥 #GIGGLE/USDT (Long📈, x20) 🔥
    Entry - 259.49
    Take-Profit:
    🥉 264.67 (40%)
    🥈 267.27 (60%)
    🥇 270.90 (80%)
    🚀 272.50 (100%)
    SL - 248.00
    """
    print(parse_signal_text(test_text))
