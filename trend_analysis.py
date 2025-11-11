"""
trend_analysis.py (versión final-validada)
------------------------------------------
Consolida análisis técnico multi-temporalidad:
- Evalúa tendencias por EMA10 / EMA30, RSI y MACD.
- Integra divergencias (RSI / MACD / volumen) desde divergence_detector.py.
- Calcula coherencia entre temporalidades.
- Genera recomendación final para signal_manager / operation_tracker.

Modo validación (configurable vía ANALYSIS_DEBUG_MODE en config.py)
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

        trends = {}
        for tf, tech in tech_multi.items():
            trend = determine_trend(tech)
            trends[tf] = trend
            if ANALYSIS_DEBUG_MODE:
                logger.debug(f"{symbol} [{tf}] → EMA10={tech.get('ema_short'):.4f}, EMA30={tech.get('ema_long'):.4f}, "
                             f"MACD_HIST={tech.get('macd_hist'):.4f}, RSI={tech.get('rsi'):.2f} → {trend}")

        # ================================================================
        # 📈 Evaluar divergencias RSI / MACD / Volumen
        # ================================================================
        divergences = detect_divergences(symbol, tech_multi)
        div_summary = ", ".join([f"{k}: {v}" for k, v in divergences.items() if v != "Ninguna"]) or "Ninguna detectada"

        # ================================================================
        # 📊 Calcular coherencia entre temporalidades
        # ================================================================
        trend_values = list(trends.values())
        major_trend = max(set(trend_values), key=trend_values.count)
        match_ratio = trend_values.count(major_trend) / len(trend_values) * 100

        # ================================================================
        # 📌 Generar recomendación final
        # ================================================================
        recommendation = "⚠️ Señal no confirmada."
        if major_trend.lower() == direction.lower() and match_ratio >= 66:
            recommendation = "✅ Coincide con la dirección de la señal."
        elif "Lateral" in major_trend:
            recommendation = "⚠️ Mercado lateral — esperar confirmación."
        elif match_ratio < 50:
            recommendation = "❌ Tendencias contradictorias — evitar entrada."

        if any(v in ["Bajista", "Alcista"] for v in divergences.values()):
            recommendation += " (⚠️ Divergencia detectada)"

        # ================================================================
        # 🧾 Resultado estructurado
        # ================================================================
        result = {
            "symbol": symbol,
            "trends": trends,
            "major_trend": major_trend,
            "match_ratio": round(match_ratio, 2),
            "divergences": divergences,
            "recommendation": recommendation
        }

        # ================================================================
        # 🪶 Logging del resultado
        # ================================================================
        summary_lines = [f"🔹 {tf}: {tr}" for tf, tr in trends.items()]
        logger.info(
            f"📊 Análisis {symbol} → {major_trend} ({match_ratio:.1f}%)\n"
            + "\n".join(summary_lines)
            + f"\n📈 Divergencias: {div_summary}\n📌 Recomendación: {recommendation}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error analizando tendencia de {symbol}: {e}")
        return {"symbol": symbol, "recommendation": "Error", "match_ratio": 0.0}


# ================================================================
# 🧪 Prueba local
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("🚀 Test local de trend_analysis (final-validada)")
    test = analyze_trend("BTCUSDT", direction="long")
    print(test)