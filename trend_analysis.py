"""
trend_analysis.py (versión mejorada)
-----------------------------------
Evalúa la tendencia técnica y genera una recomendación consolidada.
Compatible con indicators.py y divergence_detector.py.
"""

import numpy as np
import logging
from divergence_detector import detect_divergences

logger = logging.getLogger("trend_analysis")

# ================================================================
# ⚙️ Parámetros de ponderación
# ================================================================
WEIGHTS = {
    "ema": 0.35,
    "rsi": 0.20,
    "macd": 0.25,
    "divergence": 0.20,
    "volatility": 0.15
}

TF_WEIGHTS = {"1m": 0.25, "5m": 0.35, "15m": 0.25, "30m": 0.10, "1h": 0.05}
TF_ATR_FACTORS = {"1m": 0.5, "5m": 0.8, "15m": 1.0, "30m": 1.3, "1h": 1.6}


# ================================================================
# 🧭 Análisis técnico principal
# ================================================================
def analyze_trend(symbol, direction, entry, indicators_by_tf, leverage):
    """
    Evalúa la tendencia global combinando indicadores técnicos.
    Retorna un dict con match_ratio y recomendación textual.
    """

    try:
        direction = direction.lower()
        scores = []

        for tf, ind in indicators_by_tf.items():
            score = 0
            tf_factor = TF_ATR_FACTORS.get(tf, 1.0)

            # --- EMA ---
            if ind["ema_short"] and ind["ema_long"]:
                ema_score = 1 if (ind["ema_short"] > ind["ema_long"]) == (direction == "long") else -1
                score += WEIGHTS["ema"] * ema_score

            # --- RSI (sesgo y momentum) ---
            rsi = ind["rsi"]
            if rsi:
                if direction == "long":
                    score += WEIGHTS["rsi"] * ((rsi - 50) / 50)
                else:
                    score -= WEIGHTS["rsi"] * ((rsi - 50) / 50)

                # Momentum (pendiente RSI)
                if len(ind["rsi_series"]) >= 3:
                    rsi_slope = np.polyfit(range(len(ind["rsi_series"])), ind["rsi_series"], 1)[0]
                    if direction == "long" and rsi_slope < 0:
                        score -= 0.1
                    elif direction == "short" and rsi_slope > 0:
                        score -= 0.1

            # --- MACD (histograma y pendiente) ---
            macd_hist = ind["macd_hist"]
            if macd_hist:
                macd_score = np.sign(macd_hist) if direction == "long" else -np.sign(macd_hist)
                score += WEIGHTS["macd"] * macd_score

                if len(ind["macd_series"]) >= 3:
                    macd_slope = np.polyfit(range(len(ind["macd_series"])), ind["macd_series"], 1)[0]
                    if direction == "long" and macd_slope < 0:
                        score -= 0.1
                    elif direction == "short" and macd_slope > 0:
                        score -= 0.1

            # --- Divergencias RSI/MACD ---
            divergence_score = detect_divergences(symbol, ind, tf, direction)
            score += WEIGHTS["divergence"] * divergence_score

            # --- Volatilidad adaptativa (penaliza ATR alto) ---
            atr_penalty = (ind["atr_rel"] / tf_factor)
            score -= WEIGHTS["volatility"] * atr_penalty

            # --- Validación por BB Width ---
            if ind["bb_width"] < 0.01:
                score -= 0.05  # mercado lateral

            scores.append(score * TF_WEIGHTS.get(tf, 0.2))

        # ================================================================
        # 🧮 Consolidación multi-temporalidad
        # ================================================================
        avg_score = np.mean(scores) if scores else 0
        tf_alignment = sum(1 for s in scores if s > 0.5)

        # Si solo una temporalidad apoya la señal → degradar
        if avg_score < 0.45 and tf_alignment < 2:
            recommendation = "⏸️ ESPERAR"
        elif avg_score > 0.65 and tf_alignment >= 2:
            recommendation = "✅ ENTRADA"
        elif avg_score > 0.5:
            recommendation = "⚠️ ENTRADA CON PRECAUCIÓN"
        else:
            recommendation = "❌ DESCARTAR"

        logger.info(
            f"🧠 {symbol}: score={avg_score:.2f}, tf_align={tf_alignment}, rec={recommendation}"
        )

        return {
            "match_ratio": round(avg_score, 2),
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend() para {symbol}: {e}")
        return {"match_ratio": 0, "recommendation": "ERROR"}
