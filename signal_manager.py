import re
import logging
import asyncio
from bybit_client import get_ohlcv_data
from indicators import get_technical_data
from notifier import send_message

logger = logging.getLogger("signal_manager")

# ================================================================
# 🧠 Limpieza y normalización de señales
# ================================================================
def clean_signal_text(text: str) -> str:
    """Limpia y normaliza el texto de la señal recibido por Telegram."""
    text = re.sub(r"[^a-zA-Z0-9\s/._-]", "", text)
    text = text.replace(" ", "").replace("\n", "")
    return text.strip()

def extract_signal_details(message: str):
    """Extrae par, dirección y apalancamiento de la señal."""
    try:
        # Normaliza el texto
        msg = clean_signal_text(message.upper())
        # Ejemplo: "#SOON/USDT(LONGX20)" o "#PROMPT/USDT(SHORTX20)"
        pair_match = re.search(r"#?([A-Z0-9]+)[/\\-]?USDT", msg)
        direction_match = re.search(r"(LONG|SHORT)", msg)
        leverage_match = re.search(r"X(\d+)", msg)

        if not pair_match or not direction_match:
            logger.warning(f"⚠️ Señal no reconocida: {message}")
            return None

        pair = f"{pair_match.group(1)}USDT"
        direction = direction_match.group(1).lower()
        leverage = int(leverage_match.group(1)) if leverage_match else 20
        return pair, direction, leverage

    except Exception as e:
        logger.error(f"❌ Error extrayendo datos de señal: {e}")
        return None

# ================================================================
# 📊 Análisis técnico de señales
# ================================================================
async def process_signal(signal_message: str):
    """Procesa una señal recibida, analiza el par y envía recomendación."""
    try:
        details = extract_signal_details(signal_message)
        if not details:
            logger.warning("⚠️ No se pudo interpretar la señal.")
            return

        pair, direction, leverage = details
        logger.info(f"📊 Analizando señal: {pair} ({direction.upper()} x{leverage})")

        # --- Carga de velas ---
        timeframes = ["1", "5", "15"]
        dataframes = {}

        for tf in timeframes:
            df = get_ohlcv_data(pair, tf)
            if df is not None and not df.empty:
                dataframes[tf] = df
            else:
                logger.warning(f"⚠️ Insuficientes velas para {pair} ({tf}m)")

        if not dataframes:
            logger.warning(f"⚠️ No se pudieron obtener indicadores para {pair}")
            await send_message(f"⚠️ No se pudieron obtener datos para {pair}")
            return

        # --- Análisis técnico por temporalidad ---
        analysis = {}
        for tf, df in dataframes.items():
            analysis[tf] = get_technical_data(df)

        # --- Generar recomendación ---
        summary = []
        for tf, res in analysis.items():
            summary.append(f"🔹 **{tf}m:** {res.get('tendencia', 'Indefinida')}")

        recommendation = "✅ Coincide con la señal" if all(
            direction in res.get("tendencia", "").lower() for res in analysis.values()
        ) else "⚠️ Señal no confirmada por las tendencias."

        message = (
            f"📊 **Análisis de {pair}**\n"
            + "\n".join(summary)
            + f"\n📌 **Recomendación:** {recommendation}"
        )

        await send_message(message)

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        await send_message(f"⚠️ Error analizando la señal: {e}")
