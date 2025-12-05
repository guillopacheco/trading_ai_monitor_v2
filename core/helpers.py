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
from services.bybit_client import get_ohlcv_data
import logging

logger = logging.getLogger("helpers")


# ============================================================
# 🔤 Normalización básica
# ============================================================

def normalize_symbol(raw: str) -> str:
    """
    Normaliza símbolos del canal VIP que vienen como:
      BOBBOB/USDT → BOBBOBUSDT (pero puede no existir)
    
    Nueva lógica inteligente:
      1) Normalización estándar.
      2) Intentar variantes para encontrar un par REAL en Bybit.
    """

    # 1) Limpieza estándar
    clean = raw.upper().replace("/", "").replace(" ", "")
    if clean.endswith("USDT"):
        base = clean[:-4]
    else:
        base = clean

    candidates = []

    # Variante A: usar el símbolo limpio tal cual
    candidates.append(base + "USDT")

    # Variante B: si el nombre tiene duplicaciones tipo BOBBOB → BOBO
    m = re.match(r"(.+?)\1+$", base)
    if m:
        candidates.append(m.group(1).upper() + "USDT")

    # Variante C: si termina repetido (BOBBOB → BOBBO → BOB)
    if len(base) > 4 and base[-3:] == base[-6:-3]:
        candidates.append(base[:-3] + "USDT")

    # Variante D: quitar última letra (fallback genérico)
    if len(base) > 3:
        candidates.append(base[:-1] + "USDT")

    # Evitar duplicados
    candidates = list(dict.fromkeys(candidates))

    # 2) Probar variantes consultando OHLCV real
    for sym in candidates:
        try:
            df = get_ohlcv_data(sym, "15")  # timeframe pequeño para validar rápido
            if df is not None and not df.empty:
                return sym  # ¡símbolo válido encontrado!
        except Exception:
            pass

    # 3) Fallback: devolver la versión limpia original
    return candidates[0]


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
