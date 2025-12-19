# services/telegram_service/signal_parser.py
import re


def parse_signal(text: str) -> dict | None:
    """
    Parser básico de señales VIP tipo:
    🔥 #SIREN/USDT (Short📉, x20) 🔥
    """

    if not text:
        return None

    # símbolo
    m_symbol = re.search(r"#([A-Z0-9]+)/USDT", text)
    if not m_symbol:
        return None

    symbol = m_symbol.group(1) + "USDT"

    # dirección
    if "short" in text.lower():
        direction = "short"
    elif "long" in text.lower():
        direction = "long"
    else:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
    }
