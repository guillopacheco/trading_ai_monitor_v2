# services/telegram_service/signal_parser.py
import re
import logging

logger = logging.getLogger("signal_parser")


def parse_signal(text: str) -> dict | None:
    if not text:
        return None

    # 🔎 símbolo tolerante a emojis
    m_symbol = re.search(r"#\s*([A-Z0-9]+)[^\w]{0,5}USDT", text.upper())
    if not m_symbol:
        logger.warning("❌ parse_signal: no se detectó símbolo")
        return None

    symbol = m_symbol.group(1) + "USDT"

    # 🔎 dirección
    text_l = text.lower()
    if "short" in text_l:
        direction = "short"
    elif "long" in text_l:
        direction = "long"
    else:
        logger.warning("❌ parse_signal: no se detectó dirección")
        return None

    logger.info(f"✅ parse_signal OK → {symbol} {direction}")

    return {
        "symbol": symbol,
        "direction": direction,
    }
