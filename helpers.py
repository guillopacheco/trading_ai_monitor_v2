"""
helpers.py — utilidades generales del Trading AI Monitor
--------------------------------------------------------
Incluye:
- Normalización de símbolos y direcciones
- Cálculos básicos de ROI y cambio porcentual
--------------------------------------------------------
"""

import logging

logger = logging.getLogger("helpers")


# ============================================================
# 🔤 Normalización de símbolos / direcciones
# ============================================================

def normalize_symbol(symbol: str) -> str:
    """
    Normaliza un símbolo tipo:
    - 'btc/usdt' → 'BTCUSDT'
    - 'BTC-USDT' → 'BTCUSDT'
    - ' btcusdt ' → 'BTCUSDT'
    """
    if not symbol:
        return ""
    s = symbol.strip().upper()
    for ch in ["/", "-", " "]:
        s = s.replace(ch, "")
    return s


def normalize_direction(d: str | None) -> str | None:
    if not d:
        return None
    d = d.strip().lower()
    if d in ["long", "buy", "compra"]:
        return "long"
    if d in ["short", "sell", "venta"]:
        return "short"
    return None


# ============================================================
# 📈 Cálculos de ROI y cambio porcentual
# ============================================================

def calculate_price_change(entry_price: float, current_price: float, direction: str) -> float:
    """
    Cambio porcentual SIN apalancamiento, según dirección.
    direction ∈ {'long','short'}
    """
    try:
        if entry_price <= 0:
            return 0.0
        change = ((current_price - entry_price) / entry_price) * 100.0
        if direction.lower() == "short":
            change *= -1
        return change
    except Exception as e:
        logger.error(f"❌ Error en calculate_price_change: {e}")
        return 0.0


def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int) -> float:
    """
    ROI real incluyendo apalancamiento.
    """
    change = calculate_price_change(entry_price, current_price, direction)
    try:
        lev = int(leverage) if leverage else 1
    except Exception:
        lev = 1
    return change * lev
