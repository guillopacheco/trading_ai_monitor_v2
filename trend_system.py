"""
trend_system_final.py
------------------------------------------------------------
Motor unificado y estable para análisis técnico avanzado.

Usado por:
- /analizar
- signal_manager (señales entrantes)
- signal_reactivation_sync (reactivaciones)
- operation_tracker (monitoreo)
------------------------------------------------------------
"""

import logging
from typing import Optional, Tuple, Dict, Any

from indicators import get_technical_data
from divergence_detector import detect_divergences
from config import DEFAULT_TIMEFRAMES, ANALYSIS_DEBUG_MODE

logger = logging.getLogger("trend_system_final")


# ================================================================
# 🔧 Helpers internos
# ================================================================
def _normalize_timeframes() -> list[str]:
    tfs = []
    for tf in DEFAULT_TIMEFRAMES:
        tf_str = str(tf).strip()
        if not tf_str.endswith("m"):
            tf_str += "m"
        tfs.append(tf_str)
    return tfs


def _determine_trend(tech: dict) -> str:
    ema_short = tech.get("ema_short", 0)
    ema_long = tech.get("ema_long", 0)
    macd_hist = tech.get("macd_hist", 0)
    rsi = tech.get("rsi", 50)

    if ema_short > ema_long and macd_hist > 0 and rsi > 55:
        return "Alcista"
    elif ema_short < ema_long and macd_hist < 0 and rsi < 45:
        return "Bajista"
    return "Lateral / Mixta"


def _trend_to_bucket(trend: str) -> str:
    t = (trend or "").lower()
    if "alcista" in t:
        return "bull"
    if "bajista" in t:
        return "bear"
    return "side"


def _bucket_to_label(b: str) -> str:
    return {"bull": "Alcista", "bear": "Bajista"}.get(b, "Lateral / Mixta")


def _compute_major_trend(trends: Dict[str, str]) -> Tuple[str, float]:
    if not trends:
        return "Sin datos", 0.0

    buckets = {"bull": 0, "bear": 0, "side": 0}
    for tr in trends.values():
        buckets[_trend_to_bucket(tr)] += 1

    total = max(sum(buckets.values()), 1)
    dominant = max(buckets, key=buckets.get)
    coherence = (buckets[dominant] / total) * 100
    return _bucket_to_label(dominant), coherence


def _evaluate_direction_match(direction: Optional[str], trends: Dict[str, str]):
    if not direction:
        return 0.0, 0, 0

    matches = 0
    total = 0
    d = direction.lower()

    for tf, trend in trends.items():
        t_low = trend.lower()
        total += 1
        if d == "long" and "alcista" in t_low:
            matches += 1
        elif d == "short" and "bajista" in t_low:
            matches += 1

    if total == 0:
        return 0.0, 0, 0

    ratio = (matches / total) * 100
    return ratio, matches, total


def _classify_confidence(match_ratio: float, smart_conf: float):
    combined = (0.7 * (match_ratio / 100.0)) + (0.3 * smart_conf)
    if combined >= 0.8:
        return "🟢 Alta"
    elif combined >= 0.5:
        return "🟡 Media"
    return "🔴 Baja"


def _direction_bias_warning(direction: Optional[str], bias: str):
    if not direction or bias == "neutral":
        return None

    d = direction.lower()
    b = bias.lower()

    if d == "long" and "bearish" in b:
        return "⚠️ LONG va en contra de una posible reversión bajista."
    if d == "short" and "bullish" in b:
        return "⚠️ SHORT va en contra de una posible reversión alcista."
    return None


# ================================================================
# 🧠 Núcleo del análisis (para uso interno)
# ================================================================
def analyze_trend_core(symbol: str, direction_hint: Optional[str] = None):
    try:
        intervals = _normalize_timeframes()
        tech_multi = get_technical_data(symbol, intervals=intervals)

        if not tech_multi:
            return {
                "symbol": symbol,
                "trends": {},
                "major_trend": "Sin datos",
                "major_coherence": 0.0,
                "direction_hint": direction_hint,
                "match_ratio": 0.0,
                "divergences": {},
                "smart_bias": "neutral",
                "smart_confidence_avg": 0.0,
                "confidence_label": "🔴 Baja",
                "recommendation": "Sin datos técnicos disponibles."
            }

        # ------------------------------------------------------------
        # Tendencias por TF
        # ------------------------------------------------------------
        trends = {}
        smart_biases = []
        smart_confs = []

        for tf, tech in tech_multi.items():
            trend = _determine_trend(tech)
            tech["trend"] = trend
            trends[tf] = trend

            if tech.get("smart_bias") and tech["smart_bias"] != "neutral":
                smart_biases.append(tech["smart_bias"])
            if tech.get("smart_confidence", 0) > 0:
                smart_confs.append(tech["smart_confidence"])

        major_trend, major_coherence = _compute_major_trend(trends)

        # ------------------------------------------------------------
        # Divergencias
        # ------------------------------------------------------------
        divergences = detect_divergences(symbol, tech_multi)

        # Smart bias final
        if smart_biases:
            from collections import Counter
            smart_bias = Counter(smart_biases).most_common(1)[0][0]
        else:
            smart_bias = "neutral"

        smart_conf_avg = sum(smart_confs) / len(smart_confs) if smart_confs else 0.0

        # ------------------------------------------------------------
        # Coincidencia con dirección sugerida
        # ------------------------------------------------------------
        match_ratio, match_count, match_total = _evaluate_direction_match(direction_hint, trends)

        # ============================================================
        # Reglas de recomendación (FIX 2 completo)
        # ============================================================
        if direction_hint:

            # ❌ Regla 1: DESCARTAR si TODO va en contra
            if (
                direction_hint.lower() == "long"
                and all("bajista" in t.lower() for t in trends.values())
            ):
                recommendation = "DESCARTAR"

            elif (
                direction_hint.lower() == "short"
                and all("alcista" in t.lower() for t in trends.values())
            ):
                recommendation = "DESCARTAR"

            else:
                # ✔ Regla 2: Escala de confirmación
                if match_ratio >= 80:
                    recommendation = f"CONFIRMADA ({match_ratio:.1f}%)."
                elif 60 <= match_ratio < 80:
                    recommendation = f"ESPERAR MEJOR ENTRADA ({match_ratio:.1f}%)."
                else:
                    recommendation = f"ESPERAR MEJOR ENTRADA ({match_ratio:.1f}%)."

        else:
            # Sin dirección: lectura neutral
            if major_trend == "Alcista":
                recommendation = "📈 Tendencia mayor alcista. Buscar LONG."
            elif major_trend == "Bajista":
                recommendation = "📉 Tendencia mayor bajista. Buscar SHORT."
            else:
                recommendation = "⚖️ Mercado lateral. Esperar ruptura clara."

        # Aviso por divergencias
        if any(v not in ["Ninguna", "None"] for v in divergences.values()):
            recommendation += " (⚠️ Divergencia técnica detectada.)"

        # Aviso por sesgo smart contradictorio
        bias_note = _direction_bias_warning(direction_hint, smart_bias)
        if bias_note:
            recommendation += f" {bias_note}"

        confidence_label = _classify_confidence(match_ratio, smart_conf_avg)

        return {
            "symbol": symbol,
            "trends": trends,
            "major_trend": major_trend,
            "major_coherence": round(major_coherence, 2),
            "direction_hint": direction_hint,
            "match_ratio": round(match_ratio, 2),
            "divergences": divergences,
            "smart_bias": smart_bias,
            "smart_confidence_avg": round(smart_conf_avg, 3),
            "confidence_label": confidence_label,
            "recommendation": recommendation
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core({symbol}): {e}")
        return {
            "symbol": symbol,
            "trends": {},
            "major_trend": "Error",
            "major_coherence": 0.0,
            "direction_hint": direction_hint,
            "match_ratio": 0.0,
            "divergences": {},
            "smart_bias": "neutral",
            "smart_confidence_avg": 0.0,
            "confidence_label": "🔴 Baja",
            "recommendation": "Error en análisis técnico."
        }


# ================================================================
# 📤 Reporte final para Telegram
# ================================================================
def analyze_and_format(symbol: str, direction_hint: Optional[str] = None):
    result = analyze_trend_core(symbol, direction_hint)

    trends = result["trends"]
    major_trend = result["major_trend"]
    major_coherence = result["major_coherence"]
    match_ratio = result["match_ratio"]
    divergences = result["divergences"]
    smart_bias = result["smart_bias"]
    smart_conf = result["smart_confidence_avg"]
    confidence_label = result["confidence_label"]
    recommendation = result["recommendation"]

    # Bloque de TF ordenado
    def _key(tf: str):
        try:
            return int(tf.replace("m", ""))
        except:
            return 9999

    tf_block = "\n".join([f"🔹 *{tf}*: {trends[tf]}" for tf in sorted(trends.keys(), key=_key)]) \
        if trends else "🔹 Sin datos técnicos."

    # Divergencias texto limpio
    div_text = ", ".join([f"{k}: {v}" for k, v in divergences.items() if v not in ["Ninguna", None]]) \
        if divergences else "Ninguna"

    bias_label = {
        "bullish-reversal": "Reversión alcista",
        "bearish-reversal": "Reversión bajista",
        "continuation": "Continuación de tendencia",
        "neutral": "Neutral / sin sesgo claro"
    }.get(smart_bias, smart_bias)

    # Dirección sugerida
    direction_line = f"🎯 *Dirección sugerida:* {direction_hint.upper()}\n" if direction_hint else ""

    match_line = f"📊 *Coincidencia:* {match_ratio:.1f}%\n" if direction_hint else ""

    message = (
        f"📊 *Análisis de {symbol}*\n"
        f"{tf_block}\n\n"
        f"🧭 *Tendencia mayor:* {major_trend} ({major_coherence:.2f}%)\n"
        f"{direction_line}"
        f"{match_line}"
        f"🧪 *Divergencias:* {div_text}\n"
        f"🧬 *Sesgo smart:* {bias_label} (confianza {smart_conf:.2f})\n"
        f"🧮 *Confianza global:* {confidence_label}\n\n"
        f"📌 *Recomendación:* {recommendation}"
    )

    return result, message
