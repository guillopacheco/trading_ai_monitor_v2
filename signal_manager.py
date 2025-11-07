"""
signal_manager.py
---------------------------------------------------------
Administra el flujo completo de una señal detectada:
1️⃣ Recibe la señal parseada desde telegram_reader.
2️⃣ Obtiene datos técnicos (OHLCV + indicadores).
3️⃣ Analiza la tendencia con trend_analysis + divergence_detector.
4️⃣ Guarda el resultado en la base de datos.
5️⃣ Envía notificación con la recomendación final.
---------------------------------------------------------
"""

import logging
import time
from datetime import datetime

from indicators import get_technical_data
from trend_analysis import analyze_trend
from database import save_signal
from notifier import notify_signal_result
from helpers import normalize_symbol

logger = logging.getLogger("signal_manager")

# ================================================================
# ⚙️ Parámetros generales
# ================================================================
ANALYSIS_TIMEFRAMES = ["1m", "5m", "15m"]
MAX_ANALYSIS_RETRIES = 3
RETRY_DELAY = 15  # segundos


# ================================================================
# 🔍 Procesar una señal de trading
# ================================================================
def process_signal(signal_data: dict):
    """
    Ejecuta el flujo completo de análisis técnico para una señal recibida.
    - signal_data: dict con {pair, direction, leverage, entry, take_profits, message_text}
    """
    try:
        pair = signal_data["pair"].upper().replace("#", "")
        symbol = normalize_symbol(pair)
        direction = signal_data["direction"]
        leverage = int(signal_data.get("leverage", 20))
        entry_price = float(signal_data["entry"])

        logger.info(f"⚙️ Procesando señal: {symbol} ({direction.upper()} x{leverage})")

        # =========================================================
        # 1️⃣ Obtener datos técnicos de Bybit
        # =========================================================
        indicators_by_tf = None
        for attempt in range(MAX_ANALYSIS_RETRIES):
            try:
                indicators_by_tf = get_technical_data(symbol, ANALYSIS_TIMEFRAMES)
                if indicators_by_tf:
                    break
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos técnicos (intento {attempt+1}): {e}")
            time.sleep(RETRY_DELAY)

        if not indicators_by_tf:
            logger.error(f"❌ No se pudieron obtener datos técnicos para {symbol}")
            return

        logger.info(f"📈 Datos técnicos obtenidos correctamente para {symbol}")

        # =========================================================
        # 2️⃣ Analizar tendencia y divergencias
        # =========================================================
        analysis = analyze_trend(
            symbol=symbol,
            signal_direction=direction,
            entry_price=entry_price,
            indicators_by_tf=indicators_by_tf,
            leverage=leverage,
        )

        match_ratio = analysis["match_ratio"]
        recommendation = analysis["recommendation"]

        logger.info(
            f"📊 Resultado {symbol} — match_ratio={match_ratio:.2f}, recomendación={recommendation}"
        )

        # =========================================================
        # 3️⃣ Guardar señal en base de datos
        # =========================================================
        record = {
            "symbol": symbol,
            "direction": direction,
            "leverage": leverage,
            "entry": entry_price,
            "match_ratio": match_ratio,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "details": str(analysis["details"]),
        }

        save_signal(record)
        logger.info(f"💾 Señal guardada en base de datos: {symbol}")

        # =========================================================
        # 4️⃣ Notificar resultado al usuario
        # =========================================================
        msg = (
            f"📊 *Análisis de {symbol}*\n"
            f"🔹 Dirección: *{direction.upper()}*\n"
            f"🔹 Apalancamiento: *x{leverage}*\n"
            f"🔹 Entrada: `{entry_price}`\n\n"
            f"📈 *Match Ratio:* `{match_ratio:.2%}`\n"
            f"📌 *Recomendación:* {format_recommendation(recommendation)}"
        )
        notify_signal_result(symbol, msg)

        logger.info(f"📨 Notificación enviada correctamente para {symbol}")

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")


# ================================================================
# 🧠 Formatear recomendación
# ================================================================
def format_recommendation(recommendation: str) -> str:
    """
    Devuelve un texto enriquecido con ícono según la recomendación.
    """
    icons = {
        "ENTRADA": "✅ *Entrada Confirmada*",
        "ENTRADA_CON_PRECAUCION": "🟡 *Entrada con Precaución*",
        "ESPERAR": "⏳ *Esperar Confirmación*",
        "DESCARTAR": "❌ *Descartar Señal*",
    }
    return icons.get(recommendation, recommendation)


# ================================================================
# 🔁 Función auxiliar para análisis manual (opcional)
# ================================================================
def analyze_manual(symbol: str, direction: str, entry_price: float, leverage: int = 20):
    """
    Permite ejecutar un análisis técnico manual desde consola.
    """
    indicators_by_tf = get_technical_data(symbol, ANALYSIS_TIMEFRAMES)
    if not indicators_by_tf:
        print(f"⚠️ No se pudieron obtener datos técnicos para {symbol}")
        return

    analysis = analyze_trend(
        symbol=symbol,
        signal_direction=direction,
        entry_price=entry_price,
        indicators_by_tf=indicators_by_tf,
        leverage=leverage,
    )

    print("=== RESULTADO MANUAL ===")
    print(f"Símbolo: {symbol}")
    print(f"Dirección: {direction}")
    print(f"Match ratio: {analysis['match_ratio']:.2%}")
    print(f"Recomendación: {analysis['recommendation']}")
    print("Notas de divergencia:")
    for n in analysis["details"]["divergence_notes"]:
        print("  -", n)
    print("=========================")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyze_manual("BTCUSDT", "long", 69000)
