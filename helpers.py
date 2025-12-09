"""
helpers.py — utilidades 100% compatibles con el motor técnico unificado
-----------------------------------------------------------------------
Incluye:
- Normalización de símbolos / direcciones
- Cálculo de ROI apalancado
- Cálculo de pérdida real (sin apalancamiento)
- Cálculo de PnL absoluto
- Cambio porcentual adaptado para long/short
- Normalización segura de leverage
"""
import re
import logging

logger = logging.getLogger("helpers")


# ============================================================
# 🔤 Normalización básica
# ============================================================

"""
helpers.py — utilidades 100% compatibles con el motor técnico unificado
-----------------------------------------------------------------------
Incluye:
- Normalización de símbolos / direcciones
- Cálculo de ROI apalancado
- Cálculo de pérdida real (sin apalancamiento)
- Cálculo de PnL absoluto
- Cambio porcentual adaptado para long/short
- Normalización segura de leverage
"""
import re
from services.bybit_service.bybit_client import get_ohlcv_data
import logging

logger = logging.getLogger("helpers")


# ============================================================
# 🔤 Normalización básica MEJORADA Y SIMPLIFICADA
# ============================================================

def normalize_symbol(raw: str) -> str:
    """
    Normaliza símbolos del canal VIP que vienen como:
      #SYN/USDT → SYNUSDT
      #PIPPIN/USDT → PIPPINUSDT
      🔥 → EPIC (pero mejor rechazar emojis)
    """
    if not raw or not isinstance(raw, str):
        return "UNKNOWN"
    
    # 1) Remover TODOS los caracteres no alfanuméricos excepto /
    # Esto quita: #, 🔥, emojis, etc.
    clean = re.sub(r'[^a-zA-Z0-9/]', '', raw)
    
    # 2) Si tiene /, tomar parte antes del /
    if '/' in clean:
        parts = clean.split('/')
        base = parts[0].strip().upper()
        # Si base está vacío después de limpiar, usar un fallback
        if not base:
            return "UNKNOWNUSDT"
        return f"{base}USDT"
    
    # 3) Si ya termina en USDT, dejarlo
    if clean.upper().endswith("USDT"):
        return clean.upper()
    
    # 4) Si es muy corto o parece inválido, rechazar
    if len(clean) < 2:
        return "UNKNOWNUSDT"
    
    # 5) Añadir USDT
    return f"{clean.upper()}USDT"


def normalize_direction(d: str | None) -> str | None:
    if not d:
        return None
    d = d.strip().lower()
    if d in ["long", "buy", "compra", "📈", "long📈"]:
        return "long"
    if d in ["short", "sell", "venta", "📉", "short📉"]:
        return "short"
    return None


# ============================================================
# 📉 Normalización de apalancamiento
# ============================================================

def normalize_leverage(leverage) -> int:
    try:
        lev = int(leverage)
        if lev <= 0:
            return 1
        return lev
    except Exception:
        return 1


# ============================================================
# 📈 Cálculo de cambio porcentual SIN apalancamiento
# ============================================================

def calculate_price_change(entry_price: float, current_price: float, direction: str) -> float:
    """Cambio porcentual real (sin apalancamiento)."""
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


# ============================================================
# 💹 ROI REAL APALANCADO
# ============================================================

def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int):
    """
    ROI usando apalancamiento real.
    """
    lev = normalize_leverage(leverage)
    change = calculate_price_change(entry_price, current_price, direction)
    return change * lev


# ============================================================
# 🔻 Pérdida real SIN apalancamiento (requerido por motor único)
# ============================================================

def calculate_loss_pct_from_roi(roi: float, leverage: int):
    """
    Convierte ROI apalancado → pérdida real sin apalancamiento.
    Ejemplo:
        ROI = -60% con x20 → pérdida real = -3%
    """
    lev = normalize_leverage(leverage)

    try:
        return roi / lev
    except Exception:
        return 0.0


# ============================================================
# 💰 PnL ABSOLUTO (dependiendo del tamaño nominal de la posición)
# ============================================================

def calculate_pnl(entry_price: float, current_price: float, size_usdt: float, direction: str):
    """
    Cálculo simple de PnL absoluto en USDT.
    """
    try:
        if entry_price <= 0:
            return 0.0

        price_change_pct = calculate_price_change(entry_price, current_price, direction)
        return (price_change_pct / 100) * size_usdt

    except Exception as e:
        logger.error(f"❌ Error en calculate_pnl: {e}")
        return 0.0


# ============================================================
# 📉 Movimientos en PIPs / puntos normalizados
# ============================================================

def calculate_pips(entry_price: float, current_price: float):
    """
    Cálculo aproximado de pips.
    Útil para pares no-FX (ej: GIGGLE, PARTI) solo como métrica relativa.
    """
    try:
        return abs(current_price - entry_price)
    except Exception:
        return 0.0
