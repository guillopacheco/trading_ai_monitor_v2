import re
import logging
import asyncio

logger = logging.getLogger("telegram_reader")

class TelegramSignalReader:
    """
    Lector y parser para señales del canal Andy Insider.
    """

    def __init__(self, callback=None):
        self._processed_signals = set()
        self.callback = callback  # nuevo: permite manejar señales procesadas externamente

    def parse_message(self, text: str):
        """Determina si el mensaje contiene una señal válida y la parsea."""
        if self._is_profit_update(text):
            logger.info("💰 Mensaje de profit detectado — ignorado")
            return None

        if not self._is_trading_signal(text):
            logger.debug("📭 Mensaje ignorado — no corresponde a una señal válida")
            return None

        return self._parse_signal_message(text)

    def _is_trading_signal(self, text: str) -> bool:
        """Verifica si el texto corresponde a una señal completa."""
        if re.search(r'✅\s*Price\s*-\s*\d', text) or 'Profit' in text:
            return False
        pattern = re.compile(
            r"🔥\s*#([A-Z0-9]+)/USDT\s*\((Long|Short)[^)]*\)\s*🔥.*Entry\s*-\s*([\d.]+).*Take-Profit:",
            re.S
        )
        return bool(pattern.search(text))

    def _is_profit_update(self, text: str) -> bool:
        """Detecta mensajes de profit o TP alcanzado"""
        return bool(re.search(r'✅\s*Price\s*-\s*\d', text)) or 'Profit' in text

    def _parse_signal_message(self, text: str):
        """Extrae los datos de la señal Andy Insider."""
        try:
            match = re.search(
                r"#([A-Z0-9]+)/USDT\s*\((Long|Short)[^x]*x(\d+)\).*?Entry\s*-\s*([\d.]+).*?Take-Profit:\s*(?:🥉\s*([\d.]+).*🥈\s*([\d.]+).*🥇\s*([\d.]+).*🚀\s*([\d.]+))?",
                text, re.S
            )
            if not match:
                return None

            pair, direction, leverage, entry, tp1, tp2, tp3, tp4 = match.groups()
            take_profits = [float(tp) for tp in [tp1, tp2, tp3, tp4] if tp]

            data = {
                'pair': pair.strip(),
                'direction': direction.lower(),
                'leverage': int(leverage),
                'entry': float(entry),
                'take_profits': take_profits,
                'message_text': text
            }

            logger.info(f"✅ Señal parseada correctamente: {pair} ({direction}) x{leverage}")
            return data

        except Exception as e:
            logger.error(f"❌ Error parseando señal: {e}")
            return None

    async def start(self):
        """
        Este método simula la escucha asincrónica del canal de Telegram.
        (Luego se conectará al cliente real de Telethon o python-telegram-bot)
        """
        logger.info("📡 TelegramSignalReader iniciado en modo escucha...")
        while True:
            await asyncio.sleep(10)  # simula espera de nuevos mensajes
            # Aquí iría la lectura real de mensajes del canal
            # Por ahora, solo dejamos un placeholder
            pass
