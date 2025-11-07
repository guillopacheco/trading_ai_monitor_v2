"""
signal_manager.py

Gestor central de señales de trading:
- Recibe las señales parseadas desde telegram_reader.py
- Obtiene los datos de Bybit (OHLCV)
- Calcula indicadores técnicos en 1m, 5m, 15m
- Llama a trend_analysis.analyze_trend() para evaluar la calidad de la señal
- Envía resultados al notifier (Telegram)
"""

import logging
import time
from helpers import normalize_symbol
from indicators import get_technical_data
from trend_analysis import analyze_trend
from notifier import notify_signal_result
from database import store_signal

logger = logging.getLogger("signal_manager")

# ================================================================
# ⚙️ Configuración
# ================================================================
TIMEFRAMES = ["1m", "5m", "15m"]


# ================================================================
# 🚀 Procesamiento principal de señales
# ================================================================
def process_signal(signal_data: dict):
    """
    Recibe una señal parseada y ejecuta el análisis técnico completo.
    signal_data: {
        'pair': 'BTC',
        'direction': 'long',
        'leverage': 20,
        'entry': 67000.0,
        'take_profits': [68000.0, 69000.0, 70000.0],
        'message_text': '🔥 #BTC/USDT ...'
    }
    """
    try:
        symbol = normalize_symbol(signal_data["pair"])
        direction = signal_data["direction"]
        leverage = signal_data.get("leverage", 20)
        entry_price = float(signal_data["entry"])

        logger.info(f"🧠 Analizando señal {symbol} ({direction}, x{leverage})")

        # ================================================================
        # 📊 Obtener datos técnicos de múltiples temporalidades
        # ================================================================
        indicators_by_tf = {}
        for tf in TIMEFRAMES:
            tf_data = get_technical_data(symbol, tf)
            if tf_data:
                indicators_by_tf[tf] = tf_data
            else:
                logger.warning(f"⚠️ Sin datos suficientes para {symbol} en {tf}")

        if not indicators_by_tf:
            logger.error(f"❌ No se pudieron obtener datos técnicos para {symbol}")
            return

        # ================================================================
        # 🤖 Análisis técnico avanzado
        # ================================================================
        analysis = analyze_trend(
            symbol=symbol,
            signal_direction=direction,
            entry_price=entry_price,
            indicators_by_tf=indicators_by_tf,
            leverage=leverage
        )

        match_ratio = analysis["match_ratio"]
        recommendation = analysis["recommendation"]
        details = analysis["details"]

        logger.info(
            f"📈 Resultado {symbol}: match={match_ratio:.2f}, recomendación={recommendation}"
        )

        # ================================================================
        # 💾 Guardar en base de datos
        # ================================================================
        store_signal(
            symbol=symbol,
            direction=direction,
            leverage=leverage,
            entry=entry_price,
            match_ratio=match_ratio,
            recommendation=recommendation,
            timestamp=int(time.time()),
        )

        # ================================================================
        # 📬 Notificar resultado
        # ================================================================
        summary_msg = (
            f"📊 *Análisis de {symbol}*\n\n"
            f"🔹 *Dirección:* {direction.upper()}\n"
            f"🔹 *Apalancamiento:* x{leverage}\n"
            f"🔹 *Entrada:* {entry_price}\n"
            f"🔹 *Match ratio:* {match_ratio*100:.1f}%\n"
            f"📌 *Recomendación:* {recommendation}\n\n"
            f"🧠 *Notas técnicas:*\n"
        )

        # Agregar notas del análisis si existen
        for note in details.get("divergence_notes", []):
            summary_msg += f"• {note}\n"

        notify_signal_result(symbol, summary_msg)

    except Exception as e:
        logger.error(f"❌ Error procesando señal {signal_data.get('pair', '?')}: {e}", exc_info=True)
