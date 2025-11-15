"""
trend_analysis.py (versión final con confirmación de señales)
-------------------------------------------------------------
- Evalúa tendencias por EMA10 / EMA30, RSI y MACD.
- Integra divergencias (RSI / MACD / volumen) desde divergence_detector.py.
- Calcula coherencia entre temporalidades.
- Confirma si la dirección de la señal coincide con las tendencias dominantes.
- Genera recomendación final para signal_manager / operation_tracker.
"""

import logging
from indicators import get_technical_data
from divergence_detector import detect_divergences
from config import ANALYSIS_DEBUG_MODE, DEFAULT_TIMEFRAMES

logger = logging.getLogger("trend_analysis")


# ================================================================
# 🔍 Determinar tendencia general
# ================================================================
def determine_trend(tech: dict) -> str:
    """Determina tendencia básica a partir de EMA y MACD."""
    ema_short = tech.get("ema_short", 0)
    ema_long = tech.get("ema_long", 0)
    macd_hist = tech.get("macd_hist", 0)
    rsi = tech.get("rsi", 50)

    if ema_short > ema_long and macd_hist > 0 and rsi > 55:
        return "Alcista"
    elif ema_short < ema_long and macd_hist < 0 and rsi < 45:
        return "Bajista"
    else:
        return "Lateral / Mixta"


# ================================================================
# ✅ Confirmar señal vs. tendencia técnica
# ================================================================
def confirm_signal_direction(direction: str, tech_data: dict) -> tuple[bool, float]:
    """
    Compara la dirección de la señal (long/short) con las tendencias detectadas.
    Devuelve (confirmada, coincidencia_en_porcentaje)
    """
    direction = direction.lower()
    matches = 0
    total = 0

    for tf, data in tech_data.items():
        trend = data.get("trend", "").lower()
        total += 1
        if (direction == "long" and "alcista" in trend) or (direction == "short" and "bajista" in trend):
            matches += 1

    if total == 0:
        return False, 0.0

    ratio = (matches / total) * 100
    confirmada = ratio >= 60  # 60% o más de coincidencia
    return confirmada, ratio


# ================================================================
# 🧠 Análisis de coherencia multi-temporalidad
# ================================================================
def analyze_trend(symbol: str, direction: str, entry_price: float = None, tech_multi: dict = None, leverage: int = 20):
    """
    Analiza tendencias multi-temporalidad y genera una recomendación final.
    Compatible con indicadores de indicators.py y divergencias.
    """
    try:
        if tech_multi is None:
            tech_multi = get_technical_data(symbol, intervals=DEFAULT_TIMEFRAMES)
        if not tech_multi:
            logger.warning(f"⚠️ No se encontraron datos técnicos para {symbol}")
            return {"symbol": symbol, "recommendation": "Sin datos", "match_ratio": 0.0}

        # ================================================================
        # 📊 Determinar tendencia por temporalidad
        # ================================================================
        trends = {}
        for tf, tech in tech_multi.items():
            trend = determine_trend(tech)
            tech["trend"] = trend  # guardamos dentro del diccionario técnico
            trends[tf] = trend
            if ANALYSIS_DEBUG_MODE:
                logger.debug(
                    f"{symbol} [{tf}] → EMA10={tech.get('ema_short'):.4f}, EMA30={tech.get('ema_long'):.4f}, "
                    f"MACD_HIST={tech.get('macd_hist'):.4f}, RSI={tech.get('rsi'):.2f} → {trend}"
                )

        # ================================================================
        # 📈 Evaluar divergencias RSI / MACD / Volumen
        # ================================================================
        divergences = detect_divergences(symbol, tech_multi)
        div_summary = ", ".join([f"{k}: {v}" for k, v in divergences.items() if v != "Ninguna"]) or "Ninguna detectada"

                # 🆕 Agregar sesgo global de divergencias smart
        smart_biases = []
        smart_confidences = []
        for tf, tech in tech_multi.items():
            bias = tech.get("smart_bias")
            conf = tech.get("smart_confidence", 0.0)
            if bias and bias != "neutral":
                smart_biases.append((bias, conf))
                smart_confidences.append(conf)

        dominant_bias = None
        avg_conf = 0.0
        if smart_biases:
            # Tomamos el bias con mayor confianza media
            smart_biases.sort(key=lambda x: x[1], reverse=True)
            dominant_bias = smart_biases[0][0]
            avg_conf = sum(smart_confidences) / len(smart_confidences)

        # Si hay bias de reversión fuerte en contra de la dirección de la señal,
        # degradamos la confirmación.
        if dominant_bias and avg_conf >= 0.6:
            if direction.lower() == "long" and "bearish" in dominant_bias:
                recommendation = "⚠️ Señal en contra de divergencia bajista fuerte (posible reversión)."
            elif direction.lower() == "short" and "bullish" in dominant_bias:
                recommendation = "⚠️ Señal en contra de divergencia alcista fuerte (posible rebote)."

        # ================================================================
        # 📌 Confirmar dirección de señal
        # ================================================================
        confirmada, match_ratio = confirm_signal_direction(direction, tech_multi)

        # ================================================================
        # 📌 Generar recomendación final
        # ================================================================
        if confirmada:
            recommendation = f"✅ Señal confirmada ({match_ratio:.1f}% de coincidencia con tendencia)"
        else:
            recommendation = f"⚠️ Señal no confirmada ({match_ratio:.1f}% de coincidencia con tendencia)"

        # Ajuste si el mercado está lateral
        if all("Lateral" in t for t in trends.values()):
            recommendation = "⚠️ Mercado lateral — esperar confirmación adicional."

        # Añadir nota si hay divergencias
        if any(v in ["Bajista", "Alcista"] for v in divergences.values()):
            recommendation += " (⚠️ Divergencia detectada)"

        # ================================================================
        # 🧾 Resultado estructurado
        # ================================================================
        result = {
            "symbol": symbol,
            "trends": trends,
            "match_ratio": round(match_ratio, 2),
            "divergences": divergences,
            "recommendation": recommendation,
        }

        # ================================================================
        # 🧮 Etiqueta de confianza visual
        # ================================================================
        if match_ratio >= 80:
            confidence_label = "🟢 Alta"
        elif 60 <= match_ratio < 80:
            confidence_label = "🟡 Media"
        else:
            confidence_label = "🔴 Baja"

        # ================================================================
        # 📤 Mensaje completo para Telegram
        # ================================================================
        message = (
            f"📊 *Análisis de {symbol}*\n"
            + "\n".join([f"🔹 *{tf}*: {tr}" for tf, tr in trends.items()])
            + f"\n📈 *Tendencia dominante:* {major_trend}\n"
            + f"📊 *Coincidencia:* {match_ratio:.1f}%\n"
            + f"📈 *Divergencias:* {div_summary}\n"
            + f"📌 *Recomendación:* {recommendation}\n"
            + f"🧭 *Confianza:* {confidence_label}"
        )

        # Enviar al log y a Telegram
        logger.info(message)

        try:
            from notifier import send_message
            import asyncio
            asyncio.create_task(send_message(message))
        except Exception as e:
            logger.debug(f"📨 No se pudo enviar análisis de {symbol} a Telegram: {e}")

        return result

    except Exception as e:
        logger.error(f"❌ Error analizando tendencia de {symbol}: {e}")
        return {"symbol": symbol, "recommendation": "Error", "match_ratio": 0.0}

# ================================================================
# 🧪 Prueba local
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("🚀 Test local de trend_analysis (confirmación integrada)")
    test = analyze_trend("BTCUSDT", direction="long")
    print(test)
