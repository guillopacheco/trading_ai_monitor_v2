import re
import logging
import asyncio
from telethon import TelegramClient, events

from services.signals_service.signal_service import SignalService
from application_layer import process_incoming_signal

logger = logging.getLogger("telegram_reader")


# ===============================================================
# 📌 Cargar configuración desde config.py
# ===============================================================
from config import API_ID, API_HASH, TELEGRAM_SESSION, VIP_CHANNEL_ID


# ===============================================================
# 🟦 PARSER DE SEÑALES VIP
# ===============================================================
def parse_signal_text(message_text: str):
    """
    Extrae symbol + direction de una señal VIP usando expresiones regulares.
    Ejemplo:
    🔥 #GIGGLE/USDT (Long📈, x20) 🔥
    """
    try:
        # Buscar algo como #XYZ/USDT
        symbol_match = re.search(r"#([A-Za-z0-9]+\/USDT)", message_text)
        if not symbol_match:
            return None

        symbol = symbol_match.group(1).replace("/", "").upper()  # GIGGLEUSDT

        # Buscar dirección
        direction = None
        if re.search(r"\b(long|compra|buy)\b", message_text, re.IGNORECASE):
            direction = "long"
        elif re.search(r"\b(short|venta|sell)\b", message_text, re.IGNORECASE):
            direction = "short"

        if not direction:
            return None

        return symbol, direction

    except Exception as e:
        logger.exception(f"❌ Error intentando parsear señal: {e}")
        return None


# ===============================================================
# 📡 Iniciar el lector de señales VIP (Telethon)
# ===============================================================
async def start_telegram_reader():
    """
    Lector del canal VIP: recibe señales → las guarda → dispara análisis automáticamente.
    """
    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    @client.on(events.NewMessage(chats=VIP_CHANNEL_ID))
    async def handler(event):
        try:
            raw_text = event.message.message or ""
            logger.info(f"📥 Señal recibida desde canal VIP:\n{raw_text}")

            parsed = parse_signal_text(raw_text)
            if not parsed:
                logger.info("⚪ Mensaje ignorado (no es señal).")
                return

            symbol, direction = parsed
            logger.info(f"🔍 Señal detectada: {symbol} ({direction})")

            # 1) Guardar la señal en la DB mediante SignalService
            inserted_id = SignalService.save_signal(symbol, direction, raw_text)
            logger.info(f"💾 Señal guardada con ID {inserted_id}")

            # 2) Despachar análisis automático (sin bloquear el lector)
            asyncio.create_task(
                async_auto_analyze(symbol, direction, inserted_id)
            )

        except Exception as e:
            logger.exception(f"❌ Error procesando mensaje desde el VIP: {e}")

    logger.info("📡 Lector de señales activo y escuchando canal VIP.")

    await client.start()
    await client.run_until_disconnected()


# ===============================================================
# 🤖 Análisis automático en segundo plano
# ===============================================================
async def async_auto_analyze(symbol: str, direction: str, signal_id: int):
    """
    Procesa la señal automáticamente sin bloquear Telethon.
    """
    try:
        logger.info(f"⚙️ Análisis automático iniciado para {symbol} ({direction})")

        result_text = await process_incoming_signal(symbol, direction)

        # La notificación al usuario final se hace desde notifier.py
        logger.info(f"📤 Resultado análisis automático:\n{result_text}")

        # Actualizar estado final de la señal en DB:
        SignalService.update_signal_status(signal_id, "analyzed")

    except Exception as e:
        logger.exception(
            f"❌ Error en análisis automático de {symbol} ({direction}): {e}"
        )
        SignalService.update_signal_status(signal_id, "error")

