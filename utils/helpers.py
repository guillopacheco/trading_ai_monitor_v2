"""
utils/helpers.py
-----------------
Funciones pequeñas y reutilizables para toda la aplicación.
"""

import re
from typing import Tuple, List
from datetime import datetime, timezone
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

# ============================================================
# 🔵 Detectar si un texto es un comando (/start, /help, etc.)
# ============================================================

def is_command(text: str) -> bool:
    """
    Determina si un mensaje es un comando de Telegram.
    Un comando válido comienza por '/' y contiene solo letras o letras+números.

    Ejemplos aceptados:
        /start
        /help
        /analizar
        /historial
        /signal
        /revisar
        /detener

    Retorna True / False.
    """
    if not text:
        return False

    text = text.strip()

    # Comienza por "/"
    if not text.startswith("/"):
        return False

    # Estructura mínima /palabra
    if len(text) < 2:
        return False

    # Comando válido: /algo
    command = text.split()[0]

    # Ejemplo: "/analizar", "/state", "/ping"
    return command[1:].isalnum()

# ============================================================
# 🔧 Extraer comando y argumentos
# ============================================================

def extract_command(text: str):
    """
    Convierte un mensaje como:
        '/analizar BTCUSDT'
        '/help'
        '/signal #CUDISUSDT long 0.00234'

    En:
        cmd  = 'analizar'
        args = ['BTCUSDT']
    """

    if not text or not text.startswith("/"):
        return "", []

    parts = text.strip().split()

    # Comando sin '/'
    cmd = parts[0][1:].lower()

    # Argumentos restantes
    args = parts[1:] if len(parts) > 1 else []

    return cmd, args

def now_ts() -> str:
    """Devuelve timestamp ISO en UTC (para logs/DB)."""
    return datetime.now(timezone.utc).isoformat()


def is_command(text: str) -> bool:
    """Devuelve True si el mensaje parece un comando (/algo)."""
    return text.strip().startswith("/")


def extract_command(text: str) -> Tuple[str, List[str]]:
    """
    Extrae el comando y argumentos de un mensaje tipo:
        /analizar CUDISUSDT
    """
    parts = text.strip().split()
    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args