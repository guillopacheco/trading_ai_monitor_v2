import logging
import threading
from datetime import datetime
from indicators import get_indicators
from trend_analysis import analyze_trend
from divergence_detector import detect_divergences
from notifier import notify_signal_result, notify_reactivation
from helpers import calculate_match_ratio, normalize_symbol
from database import save_signal, update_operation_status
from signal_reactivation import check_reactivation

logger = logging.getLogger("signal_manager")

# ================================================================
# ⚙️ Procesamiento principal de señales
# ================================================================
def process_signal(signal_data: dict):
    """
    Analiza y gestiona una nueva señal recibida desde Telegram.
    Evalúa su coherencia técnica y decide si abrir, esperar o descartar.
    """
    try:
        raw_symbol = signal_data.get("pair", "")
        direction = signal_data.get("direction", "").lower()
        leverage = signal_data.get("leverage", 20)
        entry = signal_data.get("entry")
        take_profits = signal_data.get("take_profits", [])

        symbol = normalize_symbol(raw_symbol)
        logger.info(f"🔍 Procesando señal: {symbol} ({direction}, {leverage}x)")

        # === 1️⃣ Obtener datos de 3 temporalidades ===
        timeframes = ["1m", "5m", "15m"]
        data = get_indicators(symbol, timeframes)
        if not data or len(data) < 3:
            logger.warning(f"⚠️ No se pudieron obtener datos suficientes para {symbol}")
            return None

        # === 2️⃣ Detectar divergencias ===
        divergences = detect_divergences(symbol, data)
        strong_divs = [d for d in divergences if d["strength"] == "strong"]

        # === 3️⃣ Analizar tendencia global ===
        trend_summary = analyze_trend(symbol, data)
        match_ratio = calculate_match_ratio(trend_summary, direction)

        # === 4️⃣ Clasificar consistencia ===
        consistent_tfs = sum([1 for tf, trend in trend_summary.items() if trend == direction])
        consistency = f"{consistent_tfs}/3"

        # === 5️⃣ Generar recomendación ===
        recommendation = decide_action(match_ratio, strong_divs, consistency, direction, leverage)

        # === 6️⃣ Guardar resultados ===
        signal_record = {
            "pair": symbol,
            "direction": direction,
            "leverage": leverage,
            "entry": entry,
            "take_profits": take_profits,
            "match_ratio": match_ratio,
            "recommendation": recommendation,
            "consistency": consistency,
            "divergences": divergences,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_signal(signal_record)
        update_operation_status(symbol, recommendation, match_ratio * 100)

        # === 7️⃣ Notificar resultado inicial ===
        msg = (
            f"📊 *Análisis técnico completado*\n\n"
            f"🪙 *Par:* {symbol}\n"
            f"📈 *Dirección:* {direction.upper()} ({leverage}x)\n"
            f"📊 *Match técnico:* {match_ratio*100:.1f}%\n"
            f"📉 *Consistencia:* {consistency}\n"
            f"⚠️ *Divergencias:* {len(divergences)}\n\n"
            f"📌 *Recomendación:* {recommendation}"
        )
        notify_signal_result(symbol, msg)

        # === 8️⃣ Si la señal fue “ESPERAR”, activar reactivación programada ===
        if recommendation == "ESPERAR MEJOR ENTRADA":
            logger.info(f"🕒 Activando reanálisis periódico para {symbol}")
            thread = threading.Thread(
                target=lambda: delayed_reactivation(symbol, direction, leverage, entry),
                daemon=True,
            )
            thread.start()

        return signal_record

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}")
        return None


# ================================================================
# 🤖 Decisión de acción
# ================================================================
def decide_action(match_ratio: float, divergences: list, consistency: str, direction: str, leverage: int):
    """
    Determina la acción recomendada según el análisis técnico.
    """
    div_count = len(divergences)
    consistent_tfs = int(consistency.split("/")[0])

    if match_ratio >= 0.75 and consistent_tfs >= 2 and div_count <= 1:
        return "ENTRADA RECOMENDADA"
    elif 0.55 <= match_ratio < 0.75 or div_count >= 2:
        return "ESPERAR MEJOR ENTRADA"
    else:
        return "DESCARTAR"


# ================================================================
# ♻️ Reactivación diferida
# ================================================================
def delayed_reactivation(symbol: str, direction: str, leverage: int, entry: float):
    """
    Espera un periodo y vuelve a analizar señales que estaban en espera.
    """
    try:
        logger.info(f"🔄 Monitoreando reactivación para {symbol} durante 6h...")
        for i in range(12):  # 12 ciclos de 30 min = 6 horas
            result = check_reactivation(symbol, direction, leverage, entry)
            if result and result.get("status") == "reactivada":
                logger.info(f"✅ Reactivación confirmada: {symbol}")
                break
            else:
                logger.info(f"⏳ {symbol}: sin cambio, reanalizando en 30 min.")
            time.sleep(1800)
        logger.info(f"⏹️ Fin del monitoreo de reactivación para {symbol}.")
    except Exception as e:
        logger.error(f"❌ Error en delayed_reactivation({symbol}): {e}")
