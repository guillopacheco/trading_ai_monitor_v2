import logging
from datetime import datetime

from helpers import normalize_symbol
from indicators import get_technical_data
from trend_analysis import analyze_trend
from database import save_signal
from notifier import send_message

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧠 Procesamiento principal de señales recibidas
# ================================================================
def process_signal(signal_data: dict):
    """
    Procesa una señal de trading recibida desde Telegram.

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
        # ------------------------------------------------------------
        # 🔹 Normalización y validación de datos
        # ------------------------------------------------------------
        symbol = normalize_symbol(signal_data["pair"])
        direction = signal_data.get("direction", "").lower()
        entry = float(signal_data.get("entry", 0))
        leverage = int(signal_data.get("leverage", 20))
        ts = signal_data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

        logger.info(f"📊 Analizando señal: {symbol.upper()} ({direction.upper()} x{leverage})")

        # ------------------------------------------------------------
        # 1️⃣ Obtener indicadores técnicos multi-temporalidad
        # ------------------------------------------------------------
        indicators_by_tf = get_technical_data(symbol)

        if not indicators_by_tf:
            msg = f"⚠️ No se pudieron obtener indicadores para {symbol.upper()}"
            logger.warning(msg)
            send_message(msg)
            return

        # ------------------------------------------------------------
        # 2️⃣ Analizar tendencia global
        # ------------------------------------------------------------
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

        # ------------------------------------------------------------
        # 3️⃣ Guardar señal analizada en base de datos
        # ------------------------------------------------------------
        save_signal({
            "pair": symbol.upper(),
            "direction": direction.upper(),
            "entry": entry,
            "leverage": leverage,
            "match_ratio": match_ratio,
            "recommendation": recommendation,
            "timestamp": ts
        })

        logger.info(f"✅ Señal {symbol.upper()} procesada y guardada correctamente.")
        send_message(f"✅ Señal {symbol.upper()} procesada correctamente ({recommendation}).")

    except Exception as e:
        logger.error(f"❌ Error procesando señal {symbol or 'desconocida'}: {e}")
        send_message(f"❌ Error procesando señal {symbol or 'desconocida'}: {e}")


# ================================================================
# 🧪 Modo de prueba local
# ================================================================
def simulate_signal_test():
    """Permite lanzar un test de señal sin depender del lector de Telegram."""
    try:
        test_signal = {
            "pair": "SOON/USDT",
            "direction": "SHORT",
            "entry": 1.2994,
            "leverage": 20,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info("🚀 Iniciando test de análisis técnico con señal simulada...")
        process_signal(test_signal)
        logger.info("✅ Test completado correctamente.")
        send_message("💬 [SIMULADO] ✅ Test de señal simulada completado correctamente.")

    except Exception as e:
        logger.error(f"❌ Error ejecutando el test: {e}")
        send_message(f"💬 [SIMULADO] ❌ Error ejecutando test de señal simulada: {e}")


# ================================================================
# 🏁 Ejecución directa (para debug manual)
# ================================================================
if __name__ == "__main__":
    simulate_signal_test()
