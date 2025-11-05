import logging
import numpy as np

logger = logging.getLogger("trend_analysis")


# ================================================================
# 📊 Análisis de tendencia por temporalidad
# ================================================================
def analyze_trend(symbol: str, tf_data: dict):
    """
    Evalúa la dirección de la tendencia en varias temporalidades (1m, 5m, 15m)
    combinando información de medias móviles, MACD y RSI.
    Retorna un resumen por temporalidad.
    """

    summary = {}
    try:
        for tf, df in tf_data.items():
            if len(df) < 30:
                summary[tf] = "neutral"
                continue

            # === 1️⃣ Medias móviles ===
            short_ma = df["close"].rolling(window=9).mean()
            long_ma = df["close"].rolling(window=21).mean()

            if short_ma.iloc[-1] > long_ma.iloc[-1]:
                ma_trend = "long"
            elif short_ma.iloc[-1] < long_ma.iloc[-1]:
                ma_trend = "short"
            else:
                ma_trend = "neutral"

            # === 2️⃣ MACD ===
            macd_line = df["macd"]
            signal_line = df["signal"]
            macd_trend = "long" if macd_line.iloc[-1] > signal_line.iloc[-1] else "short"

            # === 3️⃣ RSI ===
            rsi = df["rsi"].iloc[-1]
            if rsi > 60:
                rsi_trend = "long"
            elif rsi < 40:
                rsi_trend = "short"
            else:
                rsi_trend = "neutral"

            # === 4️⃣ Determinar tendencia final ===
            trend_votes = [ma_trend, macd_trend, rsi_trend]
            final_trend = max(set(trend_votes), key=trend_votes.count)
            summary[tf] = final_trend

            logger.debug(f"📈 {symbol} {tf}: MA={ma_trend}, MACD={macd_trend}, RSI={rsi_trend} → {final_trend}")

        logger.info(f"✅ Análisis de tendencia completado para {symbol}")
        return summary

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend({symbol}): {e}")
        return {tf: "neutral" for tf in tf_data.keys()}


# ================================================================
# ⚙️ Confirmación de tendencia y coincidencia técnica
# ================================================================
def confirm_trend_direction(symbol: str, trend_summary: dict, direction: str):
    """
    Evalúa la fuerza y consistencia de la tendencia global comparada con la dirección de la señal.
    Retorna una calificación de coincidencia y consistencia.
    """

    try:
        matches = sum(1 for t in trend_summary.values() if t == direction)
        total = len(trend_summary)
        ratio = matches / total if total > 0 else 0

        if ratio == 1.0:
            strength = "FUERTEMENTE CONFIRMADA"
        elif ratio >= 0.66:
            strength = "CONFIRMADA"
        elif ratio >= 0.33:
            strength = "DÉBILMENTE CONFIRMADA"
        else:
            strength = "NO CONFIRMADA"

        logger.info(f"📊 Confirmación {symbol}: {strength} ({matches}/{total})")
        return {"match_ratio": ratio, "strength": strength}

    except Exception as e:
        logger.error(f"❌ Error en confirm_trend_direction({symbol}): {e}")
        return {"match_ratio": 0, "strength": "ERROR"}


# ================================================================
# 🧠 Evaluación avanzada para reactivación
# ================================================================
def evaluate_reactivation_opportunity(symbol: str, tf_data: dict, direction: str, entry_price: float):
    """
    Evalúa si una señal previamente 'en espera' puede ser reactivada.
    Se activa cuando:
      - La tendencia coincide en ≥2 temporalidades.
      - MACD cruza en dirección favorable.
      - RSI deja la zona neutra.
      - El precio se acerca ±0.5% al valor de entrada original.
    """

    try:
        trend_summary = analyze_trend(symbol, tf_data)
        confirm = confirm_trend_direction(symbol, trend_summary, direction)

        if confirm["match_ratio"] >= 0.66:
            df_1m = tf_data.get("1m")
            if df_1m is not None and len(df_1m) > 5:
                last_macd = df_1m["macd"].iloc[-1]
                last_signal = df_1m["signal"].iloc[-1]
                last_rsi = df_1m["rsi"].iloc[-1]
                last_price = df_1m["close"].iloc[-1]

                macd_cross = (last_macd > last_signal) if direction == "long" else (last_macd < last_signal)
                rsi_valid = (last_rsi > 55 if direction == "long" else last_rsi < 45)
                price_near_entry = abs(last_price - entry_price) / entry_price <= 0.005

                if macd_cross and rsi_valid and price_near_entry:
                    logger.info(f"♻️ Señal {symbol} reactivada automáticamente")
                    return {"status": "reactivada", "confidence": confirm["match_ratio"]}

        logger.info(f"⏳ {symbol}: No cumple condiciones de reactivación")
        return {"status": "sin_cambio", "confidence": confirm["match_ratio"]}

    except Exception as e:
        logger.error(f"❌ Error evaluando reactivación para {symbol}: {e}")
        return {"status": "error", "confidence": 0}
