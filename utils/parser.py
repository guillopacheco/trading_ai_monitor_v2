"""
utils/parser.py
----------------
Parser oficial de señales del canal VIP.

Convierte texto crudo en un diccionario estructurado:
{
    "symbol": "BTCUSDT",
    "direction": "long",
    "entry": 12345.0,
    "tp_list": [...],
    "sl": 0.0  (si existe)
}

Esta versión es estable, tolerante a errores
y compatible con la arquitectura v2.
"""

import re


# =============================================================
# 🔵 Parser principal
# =============================================================

def parse_signal_text(text: str) -> dict:
    """
    Extrae symbol, direction, entry, TP list y SL desde una señal cruda.

    Ejemplos soportados:

    🔥 #GIGGLE/USDT (Long📈, x20) 🔥
    Entry - 259.49
    TP1 - 264.67
    TP2 - ...
    SL - ...

    Retorna un dict limpio. Si falta algo esencial, retorna None.
    """

    text = text.replace("\n", " ").replace("\t", " ").strip()

    # ---------------------------------------------
    # Símbolo (#TOKEN/USDT)
    # ---------------------------------------------
    symbol_match = re.search(r"#?([A-Za-z0-9]+\/?USDT)", text, re.IGNORECASE)
    if symbol_match:
        raw_symbol = symbol_match.group(1)
        symbol = raw_symbol.replace("/", "").upper()
    else:
        return None

    # ---------------------------------------------
    # Dirección (long / short)
    # ---------------------------------------------
    direction_match = re.search(r"(long|short)", text, re.IGNORECASE)
    if direction_match:
        direction = direction_match.group(1).lower()
    else:
        direction = None

    # ---------------------------------------------
    # Entry
    # ---------------------------------------------
    entry_match = re.search(r"Entry[\s:-]+([0-9]+\.?[0-9]*)", text, re.IGNORECASE)
    if entry_match:
        entry = float(entry_match.group(1))
    else:
        entry = None

    # ---------------------------------------------
    # TPs (TP1, TP2, TP3...)
    # ---------------------------------------------
    tp_matches = re.findall(r"TP[0-9]+[\s:-]+([0-9]+\.?[0-9]*)", text, re.IGNORECASE)
    tp_list = [float(tp) for tp in tp_matches]

    # ---------------------------------------------
    # Stop Loss
    # ---------------------------------------------
    sl_match = re.search(r"SL[\s:-]+([0-9]+\.?[0-9]*)", text, re.IGNORECASE)
    sl = float(sl_match.group(1)) if sl_match else None

    if not entry or not direction:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp_list": tp_list,
        "sl": sl,
    }
