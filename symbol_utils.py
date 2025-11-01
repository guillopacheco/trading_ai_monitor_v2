# symbol_utils.py
"""Utilidades para manejo de símbolos en Bybit"""

def normalize_symbol(symbol: str, category: str = "linear") -> str:
    """
    Normaliza símbolos para Bybit - CORREGIDO
    """
    # Remover caracteres especiales y espacios, y eliminar el "/"
    symbol = symbol.upper().replace("#", "").replace("/", "").replace(" ", "")
    
    # Para LINEAR (futures), asegurar formato correcto
    if category == "linear":
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
    
    return symbol

def is_symbol_available(symbol: str, category: str = "linear") -> bool:
    """
    Verifica si un símbolo está disponible en Bybit LINEAR - MEJORADO
    """
    # Símbolos comunes disponibles en LINEAR
    available_linear_symbols = {
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "BNBUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT",
        "LINKUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "FILUSDT",
        "ICNTUSDT", "ZORAUSDT", "LABUSDT", "PIPPINUSDT"  # Agregar los nuevos tokens
    }
    
    normalized = normalize_symbol(symbol, category)
    return normalized in available_linear_symbols

def check_symbol_availability(symbol: str) -> dict:
    """
    Verifica disponibilidad en diferentes categorías - MEJORADO
    """
    normalized_linear = normalize_symbol(symbol, "linear")
    normalized_spot = normalize_symbol(symbol, "spot")
    
    # Para tokens nuevos, asumimos que están en LINEAR si tienen formato correcto
    available_in_linear = is_symbol_available(symbol, "linear")
    
    return {
        'original': symbol,
        'linear_symbol': normalized_linear,
        'spot_symbol': normalized_spot,
        'available_linear': available_in_linear,
        'available_spot': True,
        'recommended_category': 'linear'  # Siempre intentar LINEAR primero
    }