import logging
import asyncio
from datetime import datetime
from indicators import get_technical_data
from trend_analysis import analyze_trend
from divergence_detector import evaluate_divergences
from database import save_signal
from notifier import notify_signal_result
from helpers import normalize_symbol

logger = logging.getLogger("signal_manager")


# ================================================================
# 🧩 Proceso principal de análisis de señales
# ================================================================
async def process_signal(signal_data: dict):
    """
    Procesa una señal proveniente del lector de Telegram:
    - Normaliza el símbolo
    - Obtiene datos técnicos
    - Analiza tendencia, divergencias y volatilidad
    - Guarda resultados en BD
    - Envía notificación a Telegram
    """
    try:
        symbol = normalize_symbol(signal_data["pair"])
        direction = signal_data["direction"]
        entry = float(signal_data["entry"])
        leverage = int(signal_data.get("leverage", 20))

        logger.info(f"📊 Analizando señal: {symbol} ({direction.upper()} x{leverage})")

        # === 1️⃣ Obtener datos técnicos por timeframe ===
        indicators = await get_technical_data(symbol)
        if not indicators:
            logger.warning(f"⚠️ No se obtuvieron datos técnicos para {symbol}")
            return

        # === 2️⃣ Ejecutar análisis de tendencia ===
        analysis = analyze_trend(
            symbol=symbol,
            signal_direction=direction,
            entry_price=entry,
            indicators_by_tf=indicators,
            leverage=leverage
        )

        match_ratio = analysis.get("match_ratio", 0.0)
        recommendation = analysis.get("recommendation", "DESCARTAR")

        # === 3️⃣ Guardar en la base de datos ===
        signal_record = {
            "pair": symbol,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": signal_data.get("take_profits"),
            "match_ratio": match_ratio,
            "recommendation": recommendation,
        }
        await save_signal(signal_record)

        # === 4️⃣ Enviar notificación ===
        msg = (
            f"📊 *Análisis de {symbol}*\n"
            f"🔹 Dirección: *{direction.upper()}*\n"
            f"💰 Entrada: {entry}\n"
            f"⚙️ Apalancamiento: x{leverage}\n"
            f"📈 Coincidencia técnica: {match_ratio*100:.1f}%\n"
            f"📌 *Recomendación:* {recommendation}\n"
        )
        notify_signal_result(symbol, msg)

        # ======================================================
        # Guardar en base de datos
        # ======================================================
        await save_signal({
            "pair": symbol,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "match_ratio": result["match_ratio"],
            "recommendation": result["recommendation"],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

        logger.info(f"✅ Señal {symbol} procesada correctamente ({direction.upper()} x{leverage})")

        # ======================================================
        # Notificar resultado
        # ======================================================
        message = (
            f"📊 *Análisis de {symbol}*\n"
            f"🔹 Dirección: {direction.upper()}\n"
            f"📈 Entry: {entry}\n"
            f"🎯 Coincidencia: {result['match_ratio']*100:.1f}%\n"
            f"📌 Recomendación: *{result['recommendation']}*"
        )

        from notifier import send_message
        await send_message(message)

    except Exception as e:
        logger.error(f"❌ Error procesando señal {symbol}: {e}")
