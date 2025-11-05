import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("divergence_detector")


# ================================================================
# ⚙️ Detección avanzada de divergencias RSI y MACD
# ================================================================
def detect_divergences(symbol: str, tf_data: dict, direction: str = None):
    """
    Detecta divergencias RSI y MACD en distintas temporalidades.
    Clasifica su fuerza y coherencia con la dirección esperada.
    Retorna lista de divergencias encontradas.
    """
    divergences = []

    try:
        for tf, df in tf_data.items():
            if len(df) < 30:
                continue

            close = df["close"].values
            rsi = df["rsi"].values
            macd = df["macd"].values
            price_peaks = detect_peaks(close)
            rsi_peaks = detect_peaks(rsi)
            macd_peaks = detect_peaks(macd)

            # === 1️⃣ Comparar dirección de picos ===
            if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
                price_diff = close[price_peaks[-1]] - close[price_peaks[-2]]
                rsi_diff = rsi[rsi_peaks[-1]] - rsi[rsi_peaks[-2]]

                if (price_diff > 0 and rsi_diff < 0):  # Divergencia bajista
                    strength = classify_divergence_strength(rsi_diff, tf)
                    if direction == "short":
                        coherence = "coherente"
                    else:
                        coherence = "contraria"
                    divergences.append({
                        "type": "rsi",
                        "tf": tf,
                        "strength": strength,
                        "coherence": coherence,
                        "direction": "bearish"
                    })

                elif (price_diff < 0 and rsi_diff > 0):  # Divergencia alcista
                    strength = classify_divergence_strength(rsi_diff, tf)
                    if direction == "long":
                        coherence = "coherente"
                    else:
                        coherence = "contraria"
                    divergences.append({
                        "type": "rsi",
                        "tf": tf,
                        "strength": strength,
                        "coherence": coherence,
                        "direction": "bullish"
                    })

            # === 2️⃣ Verificar también divergencias en MACD ===
            if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
                price_diff = close[price_peaks[-1]] - close[price_peaks[-2]]
                macd_diff = macd[macd_peaks[-1]] - macd[macd_peaks[-2]]

                if (price_diff > 0 and macd_diff < 0):  # Divergencia bajista
                    strength = classify_divergence_strength(macd_diff, tf)
                    coherence = "coherente" if direction == "short" else "contraria"
                    divergences.append({
                        "type": "macd",
                        "tf": tf,
                        "strength": strength,
                        "coherence": coherence,
                        "direction": "bearish"
                    })

                elif (price_diff < 0 and macd_diff > 0):  # Divergencia alcista
                    strength = classify_divergence_strength(macd_diff, tf)
                    coherence = "coherente" if direction == "long" else "contraria"
                    divergences.append({
                        "type": "macd",
                        "tf": tf,
                        "strength": strength,
                        "coherence": coherence,
                        "direction": "bullish"
                    })

        # === 3️⃣ Resumen final ===
        total = len(divergences)
        strong = sum(1 for d in divergences if d["strength"] == "fuerte")
        coherent = sum(1 for d in divergences if d["coherence"] == "coherente")

        logger.info(
            f"🔺 {symbol}: {total} divergencias detectadas ({strong} fuertes, {coherent} coherentes)"
        )
        return divergences

    except Exception as e:
        logger.error(f"❌ Error en detect_divergences({symbol}): {e}")
        return []


# ================================================================
# 🔍 Utilidades internas
# ================================================================
def detect_peaks(series, window: int = 5):
    """
    Identifica picos locales simples para evaluar divergencias.
    """
    peaks = []
    try:
        for i in range(window, len(series) - window):
            if series[i] > max(series[i - window:i]) and series[i] > max(series[i + 1:i + window]):
                peaks.append(i)
        return peaks
    except Exception:
        return []


def classify_divergence_strength(diff_value: float, tf: str):
    """
    Clasifica la divergencia como fuerte, moderada o débil
    según la magnitud relativa y el timeframe.
    """
    abs_diff = abs(diff_value)
    multiplier = {"1m": 1.0, "5m": 0.8, "15m": 0.6, "1h": 0.5}.get(tf, 0.5)

    score = abs_diff * multiplier

    if score > 0.8:
        return "fuerte"
    elif score > 0.4:
        return "moderada"
    else:
        return "débil"
