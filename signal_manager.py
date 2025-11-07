import logging
import asyncio
from datetime import datetime

from helpers import normalize_symbol
from indicators import get_technical_data
from trend_analysis import analyze_trend
from database import save_signal
from notifier import send_message

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧠 Procesamiento de señales recibidas
# ================================================================
async def process_signal(signal_data: dict):
    """
    Procesa una señal de trading recibida del lector de Telegram.

    Args:
        signal_data (dict): Ejemplo:
            {
                "pair": "BTC/USDT",
                "direction": "LONG",
                "entry": 27150.0,
                "leverage": 20,
                "timestamp": "2025-11-07 03:00:00"
            }
    """
    symbol = None
    try:
        symbol = normalize_symbol(signal_data["pair"])
        direction = signal_data.get("direction", "").lower()
        entry = float(signal_data.get("entry", 0))
        leverage = int(signal_data.get("leverage", 20))
        ts = signal_data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

        logger.info(f"📊 Analizando señal: {symbol.upper()} ({direction.upper()} x{leverage})")

        # ================================================================
        # 1️⃣ Obtener datos técnicos por temporalidad
        # ================================================================
        indicators_by_tf = await get_technical_data(symbol)

        if not indicators_by_tf:
            msg = f"⚠️ No se pudieron obtener indicadores para {symbol.upper()}"
            logger.warning(msg)
            send_message(msg)
            return

        # ================================================================
        # 2️⃣ Analizar tendencia general (EMA, RSI, MACD, divergencias)
        # ================================================================
        trend_result = analyze_trend(symbol, direction, entry, indicators_by_tf, leverage)
        match_ratio = trend_result.get("match_ratio", 0)
        recommendation = trend_result.get("recommendation", "SIN DATOS")

        msg = (
            f"📊 *Análisis de {symbol.upper()}*\n"
            f"🔹 *Dirección:* {direction.upper()} (x{leverage})\n"
            f"🔹 *Ratio de coincidencia:* {match_ratio:.2f}\n"
            f"📌 *Recomendación:* {recommendation}"
        )

        send_message(msg)

        # ================================================================
        # 3️⃣ Guardar señal procesada en base de datos
        # ================================================================
        await save_signal({
            "pair": symbol.upper(),
            "direction": direction.upper(),
            "entry": entry,
            "leverage": leverage,
            "match_ratio": match_ratio,
            "recommendation": recommendation,
            "timestamp": ts
        })

        logger.info(f"✅ Señal {symbol} procesada y guardada correctamente.")
        send_message(f"✅ Señal {symbol.upper()} procesada correctamente ({recommendation}).")

    except Exception as e:
        logger.error(f"❌ Error procesando señal {symbol or 'desconocida'}: {e}")
        send_message(f"❌ Error procesando señal {symbol or 'desconocida'}: {e}")


# ================================================================
# 🧪 Simulación manual de señales (para pruebas)
# ================================================================
async def simulate_signal_test():
    """Permite lanzar un test de señal sin depender de Telegram."""
    try:
        test_signal = {
            "pair": "SOON/USDT",
            "direction": "SHORT",
            "entry": 1.2994,
            "leverage": 20,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info("🚀 Iniciando test de análisis técnico con señal simulada...")
        await process_signal(test_signal)
        logger.info("✅ Test completado correctamente.")
        send_message("💬 [SIMULADO] ✅ Test de señal simulada completado correctamente.")

    except Exception as e:
        logger.error(f"❌ Error ejecutando el test: {e}")
        send_message(f"💬 [SIMULADO] ❌ Error ejecutando test de señal simulada: {e}")


# ================================================================
# 🏁 Ejecución directa (para debug)
# ================================================================
if __name__ == "__main__":
    asyncio.run(simulate_signal_test())
