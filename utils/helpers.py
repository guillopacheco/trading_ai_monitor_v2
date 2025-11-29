"""
utils/helpers.py
-----------------
Funciones pequeñas y reutilizables para toda la aplicación.
"""
from datetime import datetime

# ============================================================
# 🔤 Normalizar símbolo
# ============================================================
def normalize_symbol(text: str) -> str:
    """
    Convierte: GIGGLE/USDT → GIGGLEUSDT
    """
    text = text.replace("/", "").replace("#", "").upper()
    if not text.endswith("USDT"):
        text += "USDT"
    return text


# ============================================================
# ⬆️⬇️ Validar dirección
# ============================================================
def normalize_direction(text: str) -> str:
    """
    Convierte cualquier formato a:
      - long
      - short
    """
    t = text.lower()
    if "long" in t or "buy" in t:
        return "long"
    if "short" in t or "sell" in t:
        return "short"
    return ""


# ============================================================
# 🔢 Validar si es float
# ============================================================
def safe_float(value):
    try:
        return float(value)
    except:
        return None


# ============================================================
# 🔢 Redondeo estándar
# ============================================================
def round6(n: float) -> float:
    return round(n, 6)


# ============================================================
# 📜 Conversión de TP crudos a lista numérica
# ============================================================
def parse_tp_list(values):
    """
    Convierte una lista cruda en floats válidos.
    """
    out = []
    for v in values:
        try:
            out.append(float(v))
        except:
            pass
    return sorted(list(set(out)))

# ============================================================
# 🔵 Timestamp utilitario
# ============================================================

def now_ts() -> str:
    """
    Devuelve timestamp estándar para logs y DB
    Formato: 'YYYY-MM-DD HH:MM:SS'
    """
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
