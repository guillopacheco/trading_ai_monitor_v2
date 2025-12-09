import logging
from telethon import TelegramClient, events

from config import API_ID, API_HASH, TELEGRAM_SESSION, TELEGRAM_CHANNEL_ID

telegram_reader_logger = logging.getLogger("telegram_reader")


# ===================================================================
#   TELEGRAM READER — Lector oficial de señales del canal VIP
# ===================================================================
async def start_telegram_reader(app_layer):
    """
    Lector de señales usando Telethon.
    • Corre en el loop principal (sin threads)
    • Cada mensaje recibido se envía al SignalCoordinator
    """

    if not hasattr(app_layer, "signal"):
        telegram_reader_logger.error("❌ ApplicationLayer no tiene signal coordinator.")
        return

    signal_coord = app_layer.signal  # SignalCoordinator

    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    await client.start()
    telegram_reader_logger.info("📡 Cliente Telethon conectado y listo para escuchar señales...")

    # ------------------------------------------------------------------
    #  Handler de señales nuevas
    # ------------------------------------------------------------------
    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
    async def handler(event):
        text = event.raw_text.strip()
        telegram_reader_logger.info(f"📨 Señal recibida del canal VIP: {text[:100]}...")

        # Intentar extraer símbolo MEJORADO
        try:
            # Buscar patrón #SÍMBOLO/USDT
            import re
            pattern = r'#([A-Za-z0-9]+)/USDT'
            match = re.search(pattern, text)
            
            if match:
                raw_symbol = match.group(1)  # Ej: SYN, PIPPIN, ARIA
            else:
                # Fallback: tomar primera palabra sin #
                parts = text.split()
                for part in parts:
                    if part.startswith("#"):
                        raw_symbol = part.replace("#", "").split("/")[0]
                        break
                else:
                    raw_symbol = parts[0].replace("#", "").split("/")[0]
            
            # Normalizar símbolo
            from helpers import normalize_symbol, normalize_direction
            symbol = normalize_symbol(raw_symbol)
            
            # Detectar dirección MEJORADO
            text_lower = text.lower()
            if "long" in text_lower or "📈" in text:
                direction = "long"
            elif "short" in text_lower or "📉" in text:
                direction = "short"
            else:
                telegram_reader_logger.warning("⚠️ No se encontró dirección en la señal.")
                return
            
            telegram_reader_logger.info(f"📊 Señal parseada: {symbol} ({direction})")
            
        except Exception as e:
            telegram_reader_logger.error(f"❌ Error parseando señal: {e}", exc_info=True)
            return
    
    # ------------------------------------------------------------------
    #  Enviar señal al COORDINADOR
    # ------------------------------------------------------------------
    try:
        await signal_coord.process_telegram_signal(
            symbol=symbol,
            direction=direction,
            raw_text=text
        )

        telegram_reader_logger.info(
            f"💾 Señal enviada al SignalCoordinator → {symbol} ({direction})"
        )

    except Exception as e:
        telegram_reader_logger.error(f"❌ Error procesando señal: {e}", exc_info=True)

    # Mantener sesión activa
    await client.run_until_disconnected()
