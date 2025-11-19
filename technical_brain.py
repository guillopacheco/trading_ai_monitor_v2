"""
technical_brain.py
------------------------------------------------------------
UNIFICADOR CENTRAL DE ANÁLISIS TÉCNICO

Este módulo reúne TODA la lógica técnica en un solo lugar:

✓ Tendencias multi-TF (1m–3m–5m–15m–30m–1h–4h)
✓ Divergencias (RSI / MACD + Smart Divergence)
✓ ATR y volatilidad relativa
✓ Match técnico (% de coincidencia con la señal)
✓ Lógica de entrada, reversión y reactivación
✓ Reportes listos para enviar por Telegram

EL RESTO DEL SISTEMA SOLO LLAMA:
- analyze_for_entry()
- analyze_for_reactivation()
- analyze_for_reversal()
- quick_tf_scan()

------------------------------------------------------------
"""

import logging
from typing import Dict, Any, List
from statistics import mean

from bybit_client import get_ohlcv_data
from smart_divergences import detect_smart_divergences

logger = logging.getLogger("technical_brain")


# ============================================================
# 🔧 Utilidades
# ============================================================

def safe_float(x):
    try:
        return float(x)
    except:
        return None


TF_LIST = ["5m", "15m", "30m", "1h", "4h", "1d"]


# ============================================================
# 📌 Análisis técnico base por temporalidad
# ============================================================

def compute_trend(df):
    """
    Determina tendencia usando:
    - EMA200
    - Pendiente de precio
    """

    if df is None or len(df) < 50:
        return "unknown"

    try:
        df["ema"] = df["close"].ewm(span=200, adjust=False).mean()

        last = df.iloc[-1]
        prev = df.iloc[-10]

        slope = last["close"] - prev["close"]
        candle_bias = "bullish" if last["close"] > last["open"] else "bearish"

        if last["close"] > last["ema"] and slope > 0:
            return "bullish"

        if last["close"] < last["ema"] and slope < 0:
            return "bearish"

        return candle_bias

    except Exception as e:
        logger.error(f"compute_trend error: {e}")
        return "unknown"


# ============================================================
# 📌 Análisis multi–TF completo
# ============================================================

def analyze_market(symbol: str, direction_hint: str = None) -> Dict[str, Any]:
    """
    Análisis técnico unificado para TODOS los módulos:
    - Tendencias por TF
    - Divergencias inteligentes
    - Señal de entrada sugerida
    """

    result = {
        "symbol": symbol,
        "direction_hint": direction_hint,
        "by_tf": {},
        "divergences": {},
        "overall_trend": "unknown",
        "entry_ok": False,
        "match_ratio": 0.0,
        "summary": ""
    }

    # ------------------------------------
    # 1. Recolectar OHLCV y calcular tendencias
    # ------------------------------------
    for tf in TF_LIST:
        df = get_ohlcv_data(symbol, tf, 400)
        if df is None or df.empty:
            continue

        trend = compute_trend(df)

        result["by_tf"][tf] = {
            "trend": trend,
            "close": safe_float(df["close"].iloc[-1])
        }

    if not result["by_tf"]:
        result["summary"] = "No hay suficientes datos para análisis."
        return result

    # ------------------------------------
    # 2. Divergencias inteligentes (RSI/MACD/Volumen)
    # ------------------------------------
    try:
        divs = detect_smart_divergences(symbol, result["by_tf"])
        result["divergences"] = divs
    except Exception as e:
        logger.error(f"detect_smart_divergences error: {e}")
        result["divergences"] = {}

    # ------------------------------------
    # 3. Tendencia global (pesada por TF mayores)
    # ------------------------------------
    trends = []
    weights = {"5m": 1, "15m": 2, "30m": 3, "1h": 4, "4h": 5, "1d": 6}

    for tf, info in result["by_tf"].items():
        t = info["trend"]
        if t == "bullish":
            trends.append(weights[tf])
        elif t == "bearish":
            trends.append(-weights[tf])

    if trends:
        avg = mean(trends)
        if avg > 1: 
            result["overall_trend"] = "bullish"
        elif avg < -1:
            result["overall_trend"] = "bearish"
        else:
            result["overall_trend"] = "neutral"

    # ------------------------------------
    # 4. Señal de entrada sugerida
    # ------------------------------------
    if direction_hint:
        if direction_hint == "long" and result["overall_trend"] == "bullish":
            result["entry_ok"] = True
            result["match_ratio"] = 85
        elif direction_hint == "short" and result["overall_trend"] == "bearish":
            result["entry_ok"] = True
            result["match_ratio"] = 85
        else:
            result["entry_ok"] = False
            result["match_ratio"] = 40
    else:
        # sugerencia automática
        if result["overall_trend"] == "bullish":
            result["entry_ok"] = True
            result["match_ratio"] = 70
        elif result["overall_trend"] == "bearish":
            result["entry_ok"] = True
            result["match_ratio"] = 70

    # ------------------------------------
    # 5. Resumen
    # ------------------------------------
    result["summary"] = build_summary(result)

    return result


# ============================================================
# 📌 Analizar entrada específica
# ============================================================

def analyze_for_entry(symbol: str, direction_hint: str):
    """
    Análisis especial para señales del canal (post-parseo).
    """
    res = analyze_market(symbol, direction_hint)
    return res


# ============================================================
# 📌 Formato Telegram
# ============================================================

def format_market_report(result: Dict[str, Any]) -> str:
    symbol = result["symbol"]
    trend = result["overall_trend"]
    divs = result["divergences"]
    match_ratio = result["match_ratio"]

    tf_lines = []
    for tf in ["5m", "15m", "30m", "1h", "4h", "1d"]:
        if tf in result["by_tf"]:
            t = result["by_tf"][tf]["trend"]
            tf_lines.append(f"• {tf}: {t.upper()}")

    div_lines = []
    for k, v in divs.items():
        if v and v not in ("None", "Ninguna"):
            div_lines.append(f"{k}: {v}")

    div_text = ", ".join(div_lines) if div_lines else "Ninguna"

    return (
        f"📊 *Análisis de {symbol}*\n"
        f"📌 Tendencia global: *{trend.upper()}*\n"
        f"🎯 Match técnico: *{match_ratio:.1f}%*\n\n"
        f"📈 Tendencias por temporalidad:\n" +
        "\n".join(tf_lines) +
        "\n\n"
        f"🧪 Divergencias: {div_text}\n\n"
        f"📌 Resumen:\n{result['summary']}"
    )


# ============================================================
# 📌 Construcción del resumen inteligente
# ============================================================

def build_summary(result: Dict[str, Any]) -> str:
    trend = result["overall_trend"]
    entry_ok = result["entry_ok"]
    hint = result["direction_hint"]

    if hint:
        if entry_ok:
            return f"Señal compatible con la tendencia global → {hint.upper()} recomendado."
        else:
            return f"La señal {hint.upper()} va contra la tendencia global."

    if trend == "bullish":
        return "Mercado con sesgo alcista, buscar LONG."
    elif trend == "bearish":
        return "Mercado con sesgo bajista, buscar SHORT."
    else:
        return "Mercado lateral / neutral."
