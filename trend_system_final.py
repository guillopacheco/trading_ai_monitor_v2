"""
trend_system_final.py
------------------------------------------------------------
Motor de análisis técnico avanzado para:

- /analizar (análisis manual desde Telegram)
- Reactivación de señales (signal_reactivation_sync.py)
- Monitor de reversiones (position_reversal_monitor.py)
- Cualquier módulo que quiera un reporte ya formateado.

Características clave:
- Usa indicators.get_technical_data() (multi-TF + divergencias smart)
- Selección AUTOMÁTICA de TF dentro de indicators.py
- Cálculo de tendencia por TF (Alcista / Bajista / Lateral)
- Cálculo de tendencia mayor + coherencia
- Uso de divergencias clásicas + smart (RSI/MACD)
- Match técnico vs dirección de la señal (long/short)
- Recomendación textual coherente con el resto de módulos
- Devuelve SIEMPRE:
    - Un dict estructurado con el resultado
    - Un string formateado para enviar directo a Telegram
------------------------------------------------------------
"""

import logging
from typing import Dict, Any, Optional, Tuple
from collections import Counter

from indicators import get_technical_data
from config import ANALYSIS_MODE

logger = logging.getLogger("trend_system_final")


# ================================================================
# 🔧 Umbrales dinámicos (agresivo / conservador)
# ================================================================
def _get_thresholds() -> Dict[str, float]:
    """
    Devuelve los umbrales dinámicos para:
    - confirmación de señal
    - reactivación de señal
    - uso interno (monitores)

    Basado en config.ANALYSIS_MODE:
        - "conservative"
        - "aggressive"
    """
    mode = (ANALYSIS_MODE or "conservative").lower()

    if mode == "aggressive":
        return {
            "confirm": 70.0,
            "reactivation": 70.0,
            "internal": 60.0,
        }

    # Modo conservador (por defecto)
    return {
        "confirm": 80.0,
        "reactivation": 80.0,
        "internal": 70.0,
    }


# ================================================================
# 🔧 Utilidades internas
# ================================================================
def _tf_to_minutes(tf: str) -> int:
    """
    Convierte '1m', '3m', '5m', '15m', '30m', '60m', '1h', '4h' → minutos.
    Si falla, devuelve un valor grande para dejarlo al final.
    """
    try:
        tf = tf.strip().lower()
        if tf.endswith("m"):
            return int(tf[:-1])
        if tf.endswith("h"):
            return int(tf[:-1]) * 60
        return int(tf)
    except Exception:
        return 9999


def _trend_label_from_raw(raw: str) -> str:
    raw = (raw or "").lower()
    if "bull" in raw or "alc" in raw:
        return "Alcista"
    if "bear" in raw or "baj" in raw:
        return "Bajista"
    return "Lateral / Mixta"


def _bucket_from_label(label: str) -> str:
    l = (label or "").lower()
    if "alc" in l or "bull" in l:
        return "bull"
    if "baj" in l or "bear" in l:
        return "bear"
    return "side"


def _bucket_to_label(bucket: str) -> str:
    if bucket == "bull":
        return "Alcista"
    if bucket == "bear":
        return "Bajista"
    return "Lateral / Mixta"


def _safe_conf_to_float(value: Any) -> float:
    """
    Convierte confidencias tipo 'weak' / 'medium' / 'strong' o números a [0..1].
    Evita errores como float('weak').
    """
    if value is None:
        return 0.0

    # Si ya es número
    if isinstance(value, (int, float)):
        try:
            v = float(value)
            # Normalizar si parece estar en porcentaje > 1
            if v > 1.5:
                return max(0.0, min(1.0, v / 100.0))
            return max(0.0, min(1.0, v))
        except Exception:
            return 0.0

    # Si es string, intentar parsear o mapear
    if isinstance(value, str):
        txt = value.strip().lower()
        # Intento directo
        try:
            v = float(txt)
            if v > 1.5:
                return max(0.0, min(1.0, v / 100.0))
            return max(0.0, min(1.0, v))
        except Exception:
            pass

        # Mapear categorías habituales
        mapping = {
            "veryweak": 0.1,
            "weak": 0.25,
            "moderate": 0.5,
            "medium": 0.5,
            "strong": 0.8,
            "verystrong": 0.95,
        }
        for key, val in mapping.items():
            if key in txt:
                return val

    return 0.0


def _classify_confidence(match_ratio: float, smart_conf_avg: float) -> str:
    """
    Clasifica la confianza combinando:
    - match_ratio (coincidencia de tendencias con la dirección)
    - smart_conf_avg (confianza media de divergencias inteligentes)
    """
    base = max(0.0, min(1.0, match_ratio / 100.0))
    smart = max(0.0, min(1.0, smart_conf_avg))
    combined = (0.7 * base) + (0.3 * smart)

    if combined >= 0.8:
        return "🟢 Alta"
    if combined >= 0.5:
        return "🟡 Media"
    return "🔴 Baja"


def _compute_major_trend(trends: Dict[str, str]) -> Tuple[str, float]:
    """
    A partir de un dict {tf: tendencia}, calcula:
    - tendencia mayor (Alcista/Bajista/Lateral)
    - porcentaje de coherencia entre temporalidades
    """
    if not trends:
        return "Sin datos", 0.0

    buckets = {"bull": 0, "bear": 0, "side": 0}
    for label in trends.values():
        b = _bucket_from_label(label)
        buckets[b] += 1

    total = sum(buckets.values()) or 1
    dominant = max(buckets, key=buckets.get)
    coherence = (buckets[dominant] / total) * 100.0
    return _bucket_to_label(dominant), coherence


def _evaluate_direction_match(
    direction_hint: Optional[str],
    trends: Dict[str, str],
) -> Tuple[float, int, int]:
    """
    Calcula qué porcentaje de temporalidades coincide con la dirección sugerida
    (long/short). Si no hay direction_hint, devuelve 0.
    """
    if not direction_hint or not trends:
        return 0.0, 0, 0

    direction = direction_hint.lower()
    matches = 0
    total = 0

    for _, label in trends.items():
        label = (label or "").lower()
        total += 1
        if direction == "long" and "alcista" in label:
            matches += 1
        elif direction == "short" and "bajista" in label:
            matches += 1

    if total == 0:
        return 0.0, 0, 0

    ratio = (matches / total) * 100.0
    return ratio, matches, total


def _summarize_divergences(tech_multi: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    A partir del dict de indicadores por TF, genera un resumen amigable:

    { "RSI": "Alcista (15m)" / "Bajista (1h)" / "Ninguna",
      "MACD": "...",
      "Volumen": "Ninguna" (placeholder)
    }
    """
    rsi_candidates = []
    macd_candidates = []

    for tf, tech in tech_multi.items():
        # Smart primero, luego legacy
        rsi_raw = tech.get("smart_rsi_div") or tech.get("rsi_div")
        macd_raw = tech.get("smart_macd_div") or tech.get("macd_div")

        if rsi_raw and str(rsi_raw).lower() not in ["none", "ninguna", "neutral"]:
            rsi_candidates.append((tf, str(rsi_raw).lower()))

        if macd_raw and str(macd_raw).lower() not in ["none", "ninguna", "neutral"]:
            macd_candidates.append((tf, str(macd_raw).lower()))

    def _pick_main(cands):
        if not cands:
            return "Ninguna"

        # Ordenar por TF más lenta primero (1h > 15m > 5m…)
        cands_sorted = sorted(cands, key=lambda x: _tf_to_minutes(x[0]), reverse=True)
        tf, kind = cands_sorted[0]
        # Texto bonito
        if "bear" in kind or "baj" in kind:
            return f"Bajista ({tf})"
        if "bull" in kind or "alc" in kind:
            return f"Alcista ({tf})"
        return f"{kind} ({tf})"

    return {
        "RSI": _pick_main(rsi_candidates),
        "MACD": _pick_main(macd_candidates),
        "Volumen": "Ninguna",  # placeholder, por ahora
    }


def _direction_vs_bias_comment(direction: Optional[str], bias: str) -> Optional[str]:
    """
    Nota si la dirección sugerida va en contra del bias smart.
    bias típico: 'bullish-reversal', 'bearish-reversal', 'continuation', 'neutral'
    """
    if not direction or not bias:
        return None

    d = direction.lower()
    b = bias.lower()

    if d == "long" and "bear" in b:
        return "⚠️ La dirección LONG va en contra de un posible giro bajista (smart bias)."
    if d == "short" and "bull" in b:
        return "⚠️ La dirección SHORT va en contra de un posible giro alcista (smart bias)."
    return None


# ================================================================
# 🧠 Núcleo de análisis
# ================================================================
def analyze_trend_core(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analiza un símbolo usando:

    - indicators.get_technical_data() sobre múltiples TF
    - divergencias smart (ya calculadas en indicators.py)
    - bias y confianza smart
    - coincidencia con la dirección sugerida (long/short)

    Devuelve un dict estructurado:

    {
      "symbol": ...,
      "trends": { "5m": "Alcista", ... },
      "major_trend": "Alcista/Bajista/Lateral/...",
      "major_coherence": 0-100,
      "direction_hint": "long"/"short"/None,
      "match_ratio": 0-100,
      "match_count": int,
      "match_total": int,
      "divergences": { "RSI": "...", "MACD": "...", "Volumen": "..." },
      "smart_bias": "...",
      "smart_confidence_avg": 0-1,
      "confidence_label": "🟢/🟡/🔴 ...",
      "allowed": bool (si la señal es viable),
      "overall_trend": "bullish"/"bearish"/"sideways",
      "recommendation": str,
    }
    """
    try:
        tech_multi = get_technical_data(symbol)

        if not tech_multi:
            logger.warning(f"⚠️ No se encontraron datos técnicos para {symbol}")
            return {
                "symbol": symbol,
                "trends": {},
                "major_trend": "Sin datos",
                "major_coherence": 0.0,
                "direction_hint": direction_hint,
                "match_ratio": 0.0,
                "match_count": 0,
                "match_total": 0,
                "divergences": {"RSI": "Ninguna", "MACD": "Ninguna", "Volumen": "Ninguna"},
                "smart_bias": "neutral",
                "smart_confidence_avg": 0.0,
                "confidence_label": "🔴 Baja",
                "allowed": False,
                "overall_trend": "sideways",
                "recommendation": "Sin datos técnicos suficientes.",
            }

        # ------------------------------------------------------------
        # 📊 Tendencias por TF + smart bias/confidence
        # ------------------------------------------------------------
        trends: Dict[str, str] = {}
        smart_biases = []
        smart_conf_values = []

        for tf, tech in tech_multi.items():
            raw_trend = tech.get("trend")  # bullish/bearish calculado en indicators
            label = _trend_label_from_raw(raw_trend)
            trends[tf] = label

            sb = tech.get("smart_bias", "neutral")
            sc = _safe_conf_to_float(tech.get("smart_confidence", 0.0))

            if sb and sb != "neutral":
                smart_biases.append(sb)
            if sc > 0:
                smart_conf_values.append(sc)

        major_trend, major_coherence = _compute_major_trend(trends)

        dominant_bias = "neutral"
        if smart_biases:
            dominant_bias = Counter(smart_biases).most_common(1)[0][0]

        smart_conf_avg = sum(smart_conf_values) / len(smart_conf_values) if smart_conf_values else 0.0

        # ------------------------------------------------------------
        # 📈 Divergencias (resumen)
        # ------------------------------------------------------------
        divergences = _summarize_divergences(tech_multi)

        # ------------------------------------------------------------
        # 🎯 Coincidencia con dirección sugerida
        # ------------------------------------------------------------
        match_ratio, match_count, match_total = _evaluate_direction_match(direction_hint, trends)

        # ------------------------------------------------------------
        # ✅ Lógica de "allowed" para uso interno (reversión/reactivación)
        # ------------------------------------------------------------
        thresholds = _get_thresholds()
        internal_thr = thresholds.get("internal", 70.0)

        allowed = True
        reasons_internal = []

        # 1) Coincidencia muy baja
        if direction_hint:
            if match_ratio < (internal_thr * 0.6):
                allowed = False
                reasons_internal.append(f"Match muy bajo ({match_ratio:.1f}%).")

        # 2) Divergencias fuertes en contra
        rsi_div = (divergences.get("RSI") or "").lower()
        macd_div = (divergences.get("MACD") or "").lower()

        if direction_hint == "long":
            if "bajista" in rsi_div or "bear" in rsi_div or "bajista" in macd_div or "bear" in macd_div:
                allowed = False
                reasons_internal.append("Divergencias bajistas contra LONG.")
        elif direction_hint == "short":
            if "alcista" in rsi_div or "bull" in rsi_div or "alcista" in macd_div or "bull" in macd_div:
                allowed = False
                reasons_internal.append("Divergencias alcistas contra SHORT.")

        # 3) Smart bias muy contrario
        db = dominant_bias.lower()
        if direction_hint == "long" and "bear" in db:
            allowed = False
            reasons_internal.append("Smart bias bajista contra LONG.")
        if direction_hint == "short" and "bull" in db:
            allowed = False
            reasons_internal.append("Smart bias alcista contra SHORT.")

        # ------------------------------------------------------------
        # 🧮 Confianza global
        # ------------------------------------------------------------
        confidence_label = _classify_confidence(match_ratio, smart_conf_avg)

        # ------------------------------------------------------------
        # 🧭 Overall trend (compacto)
        # ------------------------------------------------------------
        if "alcista" in major_trend.lower():
            overall_trend = "bullish"
        elif "bajista" in major_trend.lower():
            overall_trend = "bearish"
        else:
            overall_trend = "sideways"

        # ------------------------------------------------------------
        # 📌 Recomendación textual
        # ------------------------------------------------------------
        if direction_hint:
            confirm_thr = thresholds.get("confirm", 80.0)

            if not allowed:
                recommendation = f"❌ Condiciones técnicas poco favorables para {direction_hint.upper()}: " \
                                 + "; ".join(reasons_internal) if reasons_internal else \
                                 "❌ Condiciones técnicas poco favorables para la señal."
            else:
                if match_ratio >= confirm_thr:
                    recommendation = f"✅ Señal confirmada ({match_ratio:.1f}% de coincidencia con la tendencia)."
                elif match_ratio >= (confirm_thr - 20):
                    recommendation = f"🟡 Señal parcialmente confirmada ({match_ratio:.1f}% de coincidencia)."
                else:
                    recommendation = f"⚠️ Señal débil ({match_ratio:.1f}% de coincidencia). Esperar mejor entrada."

        else:
            # Sin dirección propuesta, lectura descriptiva
            if "alcista" in major_trend.lower():
                recommendation = "📈 Tendencia mayor alcista. Buscar oportunidades LONG en retrocesos."
            elif "bajista" in major_trend.lower():
                recommendation = "📉 Tendencia mayor bajista. Buscar oportunidades SHORT en rebotes."
            elif "lateral" in major_trend.lower():
                recommendation = "⚖️ Mercado lateral/mixto. Evitar entradas agresivas; esperar ruptura clara."
            else:
                recommendation = "ℹ️ Sin suficiente información para una recomendación clara."

        # Nota extra si bias smart contradice
        bias_note = _direction_vs_bias_comment(direction_hint, dominant_bias)
        if bias_note:
            recommendation += f" {bias_note}"

        # Nota si hay divergencias detectadas
        if any(v and v != "Ninguna" for v in divergences.values()):
            recommendation += " (⚠️ Divergencia técnica detectada.)"

        return {
            "symbol": symbol,
            "trends": trends,
            "major_trend": major_trend,
            "major_coherence": round(major_coherence, 2),
            "direction_hint": direction_hint,
            "match_ratio": round(match_ratio, 2),
            "match_count": match_count,
            "match_total": match_total,
            "divergences": divergences,
            "smart_bias": dominant_bias,
            "smart_confidence_avg": round(smart_conf_avg, 3),
            "confidence_label": confidence_label,
            "allowed": allowed,
            "overall_trend": overall_trend,
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core para {symbol}: {e}")
        return {
            "symbol": symbol,
            "trends": {},
            "major_trend": "Error",
            "major_coherence": 0.0,
            "direction_hint": direction_hint,
            "match_ratio": 0.0,
            "match_count": 0,
            "match_total": 0,
            "divergences": {"RSI": "Error", "MACD": "Error", "Volumen": "Error"},
            "smart_bias": "neutral",
            "smart_confidence_avg": 0.0,
            "confidence_label": "🔴 Baja",
            "allowed": False,
            "overall_trend": "sideways",
            "recommendation": "Error en el análisis técnico.",
        }


# ================================================================
# 📨 Formateo final para Telegram
# ================================================================
def analyze_and_format(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Función principal que usarán:
    - /analizar
    - signal_reactivation_sync
    - position_reversal_monitor
    - Otros módulos que quieran un reporte listo para Telegram

    Retorna:
      (resultado_dict, mensaje_formateado_markdown)
    """
    result = analyze_trend_core(symbol, direction_hint=direction_hint)

    symbol = result.get("symbol", symbol)
    trends = result.get("trends", {})
    major_trend = result.get("major_trend", "Sin datos")
    major_coherence = result.get("major_coherence", 0.0)
    direction = result.get("direction_hint")
    match_ratio = result.get("match_ratio", 0.0)
    divergences = result.get("divergences", {})
    smart_bias = result.get("smart_bias", "neutral")
    smart_conf = result.get("smart_confidence_avg", 0.0)
    confidence_label = result.get("confidence_label", "🔴 Baja")
    recommendation = result.get("recommendation", "Sin recomendación.")

    # Tendencias por TF ordenadas
    tf_lines = []
    for tf in sorted(trends.keys(), key=_tf_to_minutes):
        tf_lines.append(f"🔹 *{tf}*: {trends[tf]}")
    tf_block = "\n".join(tf_lines) if tf_lines else "🔹 Sin datos por temporalidad."

    # Divergencias en texto
    if divergences:
        parts = []
        rsi_txt = divergences.get("RSI")
        macd_txt = divergences.get("MACD")
        if rsi_txt and rsi_txt != "Ninguna":
            parts.append(f"RSI: {rsi_txt}")
        if macd_txt and macd_txt != "Ninguna":
            parts.append(f"MACD: {macd_txt}")
        div_text = ", ".join(parts) if parts else "Ninguna"
    else:
        div_text = "Ninguna"

    # Sesgo smart legible
    bias_human_map = {
        "bullish-reversal": "Reversión alcista",
        "bearish-reversal": "Reversión bajista",
        "continuation": "Continuación de tendencia",
        "neutral": "Neutral / sin sesgo claro",
    }
    bias_human = bias_human_map.get(smart_bias, smart_bias)

    if direction:
        dir_text = direction.upper()
        dir_line = f"🎯 *Dirección sugerida:* {dir_text}\n"
        match_line = f"📊 *Coincidencia con la tendencia:* {match_ratio:.1f}%\n"
    else:
        dir_line = ""
        match_line = ""

    message = (
        f"📊 *Análisis de {symbol}*\n"
        f"{tf_block}\n\n"
        f"🧭 *Tendencia mayor:* {major_trend} ({major_coherence:.2f}%)\n"
        f"{dir_line}"
        f"{match_line}"
        f"🧪 *Divergencias:* {div_text}\n"
        f"🧬 *Sesgo técnico (smart):* {bias_human} (confianza {smart_conf:.2f})\n"
        f"🧮 *Confianza global:* {confidence_label}\n\n"
        f"📌 *Recomendación:* {recommendation}"
    )

    return result, message


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    r, m = analyze_and_format("BTCUSDT", direction_hint="long")
    print(m)
