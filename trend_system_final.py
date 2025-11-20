"""
trend_system_final.py
------------------------------------------------------------
Motor de análisis técnico avanzado para:

- /analizar (análisis manual desde Telegram)
- Reactivación de señales (signal_reactivation_sync.py)
- Monitor de operaciones abiertas (operation_tracker.py)
- Otros módulos que quieran un reporte ya formateado.

Características clave:
- Usa indicators.get_technical_data() para obtener datos multi-TF
- Selección AUTOMÁTICA de las 3 mejores temporalidades para apalancamiento x20
- Cálculo de tendencia por TF (Alcista / Bajista / Lateral)
- Cálculo de tendencia mayor + coherencia
- Uso de divergence_detector.detect_divergences()
- Uso de smart_bias / smart_confidence provenientes de indicators.py
- Match técnico vs dirección de la señal (long/short)
- Recomendación textual coherente con el resto de módulos
- Devuelve SIEMPRE:
    - Un dict estructurado con el resultado
    - Un string formateado para enviar directo a Telegram
------------------------------------------------------------
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
from collections import Counter

from indicators import get_technical_data
from divergence_detector import detect_divergences
from config import DEFAULT_TIMEFRAMES, ANALYSIS_DEBUG_MODE

logger = logging.getLogger("trend_system_final")


# ================================================================
# 🔧 Umbrales dinámicos (agresivo / conservador)
# ================================================================
def _get_thresholds() -> dict:
    """
    Devuelve los umbrales dinámicos para:
    - confirmación de señal
    - reactivación de señal
    - uso interno

    Se basa en config.ANALYSIS_MODE:
        - "conservative"
        - "aggressive"
        - "balanced" (intermedio)
    """
    from config import ANALYSIS_MODE

    mode = (ANALYSIS_MODE or "conservative").lower()

    if mode == "aggressive":
        return {
            "confirm": 70.0,
            "reactivation": 70.0,
            "internal": 60.0,
        }
    elif mode == "balanced":
        return {
            "confirm": 75.0,
            "reactivation": 75.0,
            "internal": 65.0,
        }

    # Modo conservador (por defecto)
    return {
        "confirm": 80.0,
        "reactivation": 80.0,
        "internal": 70.0,
    }


# ================================================================
# 🔧 Utilidades de temporalidades
# ================================================================
def _tf_to_minutes(tf: str) -> int:
    """
    Convierte:
      '1m','3m','5m','15m','30m','60m','1h','4h'
    a minutos (int).

    Si no se puede, devuelve 9999 para dejarlo al final.
    """
    try:
        tf = tf.strip().lower()
        if tf.endswith("m"):
            return int(tf.replace("m", ""))
        if tf.endswith("h"):
            hours = int(tf.replace("h", ""))
            return hours * 60
        # fallback: asumir minutos
        return int(tf)
    except Exception:
        return 9999


def _normalize_config_timeframes() -> List[str]:
    """
    Convierte DEFAULT_TIMEFRAMES de config.py (["1","5","15"])
    al formato usado por indicators.get_technical_data()
    (["1m","5m","15m"]).
    """
    tfs: List[str] = []
    try:
        for tf in DEFAULT_TIMEFRAMES:
            tf_str = str(tf).strip()
            if tf_str.endswith("m") or tf_str.endswith("h"):
                tfs.append(tf_str)
            else:
                tfs.append(f"{tf_str}m")
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron normalizar DEFAULT_TIMEFRAMES: {e}")
    return tfs


def _candidate_timeframes() -> List[str]:
    """
    Genera la lista de temporalidades candidatas:

    - Usa DEFAULT_TIMEFRAMES de config.py (si existen)
    - Añade set recomendado para x20:
      ["1m","3m","5m","15m","30m","60m"]

    Luego deduplica y ordena por minutos crecientes.
    """
    base = set(_normalize_config_timeframes())
    for tf in ["1m", "3m", "5m", "15m", "30m", "60m"]:
        base.add(tf)

    return sorted(base, key=_tf_to_minutes)


def _score_timeframe(tf: str, tech: Dict[str, Any]) -> float:
    """
    Asigna un "score de calidad" a una TF basándose en:

    - Horizonte temporal (en minutos)
    - Volatilidad relativa (atr_rel)
    """
    minutes = _tf_to_minutes(tf)

    # Peso base por horizonte (ajustado a futuros x20)
    if minutes <= 1:
        base = 0.4
    elif minutes <= 3:
        base = 0.6
    elif minutes <= 5:
        base = 0.9
    elif minutes <= 15:
        base = 1.2
    elif minutes <= 30:
        base = 1.1
    elif minutes <= 60:
        base = 1.0
    else:
        base = 0.6

    atr_rel = float(tech.get("atr_rel", 0.0) or 0.0)

    # Zona “saludable” de volatilidad
    if 0.005 <= atr_rel <= 0.03:
        base += 0.2
    elif atr_rel < 0.002 or atr_rel > 0.05:
        base -= 0.3

    return base


def _select_best_timeframes(
    tech_all: Dict[str, Dict[str, Any]],
    max_tfs: int = 3
) -> Dict[str, Dict[str, Any]]:
    """
    Recibe el dict completo de indicadores por TF y devuelve solo las
    `max_tfs` temporalidades con mejor score.
    """
    if not tech_all:
        return {}

    if len(tech_all) <= max_tfs:
        return dict(sorted(tech_all.items(), key=lambda kv: _tf_to_minutes(kv[0])))

    scored = []
    for tf, tech in tech_all.items():
        score = _score_timeframe(tf, tech)
        scored.append((tf, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    chosen_tfs = [tf for tf, _ in scored[:max_tfs]]
    chosen_tfs = sorted(chosen_tfs, key=_tf_to_minutes)

    if ANALYSIS_DEBUG_MODE:
        logger.debug("🎯 Ranking TF: " + " | ".join([f"{tf}:{s:.2f}" for tf, s in scored]))
        logger.debug(f"✅ TF seleccionadas: {chosen_tfs}")

    return {tf: tech_all[tf] for tf in chosen_tfs if tf in tech_all}


# ================================================================
# 🔍 Utilidades de tendencia
# ================================================================
def _determine_trend_for_tf(tech: dict) -> str:
    """
    Determina tendencia textual usando:
    - EMA corta vs EMA larga
    - MACD hist
    - RSI
    """
    ema_short = tech.get("ema_short", 0.0)
    ema_long = tech.get("ema_long", 0.0)
    macd_hist = tech.get("macd_hist", 0.0)
    rsi = tech.get("rsi", 50.0)

    if ema_short > ema_long and macd_hist > 0 and rsi > 55:
        return "Alcista"
    elif ema_short < ema_long and macd_hist < 0 and rsi < 45:
        return "Bajista"
    else:
        return "Lateral / Mixta"


def _trend_to_bucket(trend: str) -> str:
    t = (trend or "").lower()
    if "alcista" in t or "bull" in t:
        return "bull"
    if "bajista" in t or "bear" in t:
        return "bear"
    return "side"


def _bucket_to_label(bucket: str) -> str:
    if bucket == "bull":
        return "Alcista"
    if bucket == "bear":
        return "Bajista"
    return "Lateral / Mixta"


def _compute_major_trend(trends: Dict[str, str]) -> Tuple[str, float]:
    """
    A partir de {tf: tendencia}, calcula:
    - tendencia mayor
    - porcentaje de coherencia
    """
    if not trends:
        return "Sin datos", 0.0

    buckets = {"bull": 0, "bear": 0, "side": 0}
    for t in trends.values():
        b = _trend_to_bucket(t)
        buckets[b] += 1

    total = sum(buckets.values()) or 1
    dominant = max(buckets, key=buckets.get)
    coherence = (buckets[dominant] / total) * 100.0
    label = _bucket_to_label(dominant)
    return label, coherence


def _evaluate_direction_match(
    direction_hint: Optional[str],
    trends: Dict[str, str]
) -> Tuple[float, int, int]:
    """
    Calcula el % de TF que coincide con la dirección propuesta.
    """
    if not direction_hint or not trends:
        return 0.0, 0, 0

    direction_hint = direction_hint.lower()
    matches = 0
    total = 0

    for _, t in trends.items():
        t_low = (t or "").lower()
        total += 1
        if direction_hint == "long" and "alcista" in t_low:
            matches += 1
        elif direction_hint == "short" and "bajista" in t_low:
            matches += 1

    if total == 0:
        return 0.0, 0, 0

    ratio = (matches / total) * 100.0
    return ratio, matches, total


def _classify_confidence(match_ratio: float, smart_conf_avg: float) -> str:
    """
    Confianza combinando match_ratio (0–100) y smart_conf_avg (0–1).
    """
    base = match_ratio / 100.0
    combined = (0.7 * base) + (0.3 * smart_conf_avg)

    if combined >= 0.8:
        return "🟢 Alta"
    elif combined >= 0.5:
        return "🟡 Media"
    else:
        return "🔴 Baja"


def _direction_vs_bias_comment(direction: Optional[str], bias: str) -> Optional[str]:
    """
    Comenta si la dirección LONG/SHORT va en contra del bias smart.
    """
    if not direction or not bias or bias == "neutral":
        return None

    d = direction.lower()
    b = bias.lower()

    if d == "long" and "bearish" in b:
        return "⚠️ La dirección LONG va en contra de una posible reversión bajista."
    if d == "short" and "bullish" in b:
        return "⚠️ La dirección SHORT va en contra de una posible reversión alcista."
    return None


# ================================================================
# 🧪 Evaluación de riesgo por divergencias (nivel alto/medio/bajo)
# ================================================================
def _assess_divergence_risk(
    direction_hint: Optional[str],
    tech_multi: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evalúa el riesgo que aportan las divergencias "smart" por TF.

    Reglas:
    - SOLO se usan las TF que realmente existen en tech_multi.
    - NO se penaliza si no hay 1h/4h (monedas nuevas).
    - Se considera "en contra" cuando:
        LONG  ← divergencia bajista (bearish)
        SHORT ← divergencia alcista (bullish)
    - Se ponderan más las TF de 15m–1h+.

    Devuelve:
      {
        "level": "none" | "medium" | "high",
        "reason": str
      }
    """
    if not direction_hint or not tech_multi:
        return {"level": "none", "reason": ""}

    d = direction_hint.lower()

    high_hits = 0  # divergencias fuertes en >=60m
    mid_hits = 0   # divergencias significativas en 15m–30m

    for tf, tech in tech_multi.items():
        minutes = _tf_to_minutes(tf)

        rsi_type = str(tech.get("smart_rsi_div") or "").lower()
        macd_type = str(tech.get("smart_macd_div") or "").lower()
        strength = float(tech.get("smart_div_strength", 0.0) or 0.0)

        # ¿Esta divergencia va en contra de la dirección?
        against = False
        if d == "long":
            if "bear" in rsi_type or "bear" in macd_type:
                against = True
        elif d == "short":
            if "bull" in rsi_type or "bull" in macd_type:
                against = True

        if not against:
            continue

        # Clasificación por TF y fuerza
        if minutes >= 60 and strength >= 0.6:
            high_hits += 1
        elif 15 <= minutes < 60 and strength >= 0.4:
            mid_hits += 1

    if high_hits > 0:
        return {
            "level": "high",
            "reason": "Divergencias fuertes en temporalidades mayores (≥1h) en contra de la señal.",
        }
    if mid_hits > 0:
        return {
            "level": "medium",
            "reason": "Divergencias relevantes en 15m–30m en contra de la señal.",
        }

    return {"level": "none", "reason": ""}


# ================================================================
# 🧠 Núcleo de análisis
# ================================================================
def analyze_trend_core(
    symbol: str,
    direction_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analiza un símbolo con:
    - datos técnicos multi-TF (indicators.get_technical_data)
    - selección automática de las mejores TF
    - divergencias (divergence_detector)
    - smart_bias / smart_confidence

    Mantiene una API estable para el resto de módulos.
    """
    try:
        candidates = _candidate_timeframes()
        tech_all = get_technical_data(symbol, intervals=candidates)

        if not tech_all:
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
                "recommendation": "Sin datos técnicos disponibles.",
                "divergence_risk": {"level": "none", "reason": ""},
            }

        # 🎯 Selección automática de TF
        tech_multi = _select_best_timeframes(tech_all, max_tfs=3)

        if not tech_multi:
            logger.warning(f"⚠️ No se pudieron seleccionar TF válidas para {symbol}")
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
                "recommendation": "Sin datos técnicos disponibles.",
                "divergence_risk": {"level": "none", "reason": ""},
            }

        # 📊 Tendencia por TF + smart info
        trends: Dict[str, str] = {}
        smart_biases = []
        smart_confidences = []

        for tf, tech in tech_multi.items():
            trend = _determine_trend_for_tf(tech)
            trends[tf] = trend
            tech["trend"] = trend

            sb = tech.get("smart_bias", "neutral")
            sc = float(tech.get("smart_confidence", 0.0))

            if sb and sb != "neutral":
                smart_biases.append(sb)
            if sc > 0:
                smart_confidences.append(sc)

            if ANALYSIS_DEBUG_MODE:
                try:
                    logger.debug(
                        f"{symbol} [{tf}] → EMAshort={tech.get('ema_short'):.4f}, "
                        f"EMAlong={tech.get('ema_long'):.4f}, MACD_HIST={tech.get('macd_hist'):.4f}, "
                        f"RSI={tech.get('rsi'):.2f} → {trend}"
                    )
                except Exception:
                    logger.debug(f"{symbol} [{tf}] → trend={trend}")

        major_trend, major_coherence = _compute_major_trend(trends)

        # 🧪 Divergencias globales (tradicionales)
        divergences = detect_divergences(symbol, tech_multi)

        # 🧬 Smart bias
        dominant_bias = "neutral"
        if smart_biases:
            dominant_bias = Counter(smart_biases).most_common(1)[0][0]

        smart_conf_avg = sum(smart_confidences) / len(smart_confidences) if smart_confidences else 0.0

        # 📌 Match vs dirección sugerida (sin penalización aún)
        match_ratio, match_count, match_total = _evaluate_direction_match(direction_hint, trends)

        # ============================================================
        # 🧮 Recomendación base (antes de aplicar riesgo por divergencias)
        # ============================================================
        if direction_hint:
            th = _get_thresholds()
            needed = th.get("confirm", 80.0)

            if match_ratio >= needed:
                recommendation = f"✅ Señal confirmada ({match_ratio:.1f}% de coincidencia con la tendencia)."
            elif match_ratio >= needed - 20:
                recommendation = f"🟡 Señal parcialmente confirmada ({match_ratio:.1f}% de coincidencia)."
            else:
                recommendation = f"⚠️ Esperar mejor entrada ({match_ratio:.1f}% de coincidencia)."
        else:
            if major_trend == "Alcista":
                recommendation = "📈 Tendencia mayor alcista. Buscar oportunidades LONG en retrocesos."
            elif major_trend == "Bajista":
                recommendation = "📉 Tendencia mayor bajista. Buscar oportunidades SHORT en rebotes."
            elif major_trend == "Lateral / Mixta":
                recommendation = "⚖️ Mercado lateral/mixto. Evitar entradas agresivas; esperar ruptura clara."
            else:
                recommendation = "ℹ️ Sin suficiente información para una recomendación clara."

        # ============================================================
        # 🧪 Ajuste por divergencias smart en contra (riesgo alto/medio)
        # ============================================================
        divergence_risk = _assess_divergence_risk(direction_hint, tech_multi)
        risk_level = divergence_risk["level"]
        risk_reason = divergence_risk["reason"]

        if direction_hint and risk_level != "none":
            # No modificamos la estructura de salida, solo afinamos texto
            # y, en caso extremo, bajamos efectividad de la señal.
            if risk_level == "high":
                # Capar match_ratio para que no parezca "perfecta"
                match_ratio = min(match_ratio, 65.0)
                if "✅ Señal confirmada" in recommendation:
                    recommendation = (
                        "⚠️ Señal técnicamente alineada con la tendencia, "
                        "pero con divergencias FUERTES en temporalidades mayores. "
                        "Recomiendo NO entrar agresivo; mejor esperar confirmación o retroceso."
                    )
                else:
                    recommendation += f" ⚠️ {risk_reason}"
            elif risk_level == "medium":
                recommendation += f" ⚠️ {risk_reason}"

        # Aviso por divergencias clásicas (legacy)
        div_values = [v for v in divergences.values() if v and v not in ["Ninguna", "None"]]
        if div_values:
            recommendation += " (⚠️ Divergencia técnica detectada.)"

        # Nota por bias contrario
        bias_note = _direction_vs_bias_comment(direction_hint, dominant_bias)
        if bias_note:
            recommendation += f" {bias_note}"

        # Confianza final (después de posibles ajustes de match_ratio)
        confidence_label = _classify_confidence(match_ratio, smart_conf_avg)

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
            "recommendation": recommendation,
            # Campo nuevo, solo informativo (no rompe nada):
            "divergence_risk": divergence_risk,
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
            "recommendation": "Error en el análisis técnico.",
            "divergence_risk": {"level": "none", "reason": ""},
        }


# ================================================================
# 📨 Formateo final para Telegram
# ================================================================
def analyze_and_format(
    symbol: str,
    direction_hint: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Función principal que usarán:
    - /analizar
    - signal_reactivation_sync
    - operation_tracker
    - Cualquier módulo que quiera texto listo para Telegram
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
    divergence_risk = result.get("divergence_risk", {"level": "none", "reason": ""})

    # Bloque de tendencias
    tf_lines = []
    for tf in sorted(trends.keys(), key=_tf_to_minutes):
        tf_lines.append(f"🔹 *{tf}*: {trends[tf]}")
    tf_block = "\n".join(tf_lines) if tf_lines else "🔹 Sin datos por temporalidad."

    # Divergencias en texto (legacy)
    if divergences:
        div_parts = []
        for k, v in divergences.items():
            if not v or v in ["Ninguna", "None"]:
                continue
            div_parts.append(f"{k}: {v}")
        div_text = ", ".join(div_parts) if div_parts else "Ninguna"
    else:
        div_text = "Ninguna"

    # Sesgo smart
    bias_human = {
        "bullish-reversal": "Reversión alcista",
        "bearish-reversal": "Reversión bajista",
        "continuation": "Continuación de tendencia",
        "neutral": "Neutral / sin sesgo claro",
    }.get(smart_bias, smart_bias)

    if direction:
        dir_text = direction.upper()
        dir_line = f"🎯 *Dirección sugerida:* {dir_text}\n"
        match_line = f"📊 *Coincidencia con la tendencia:* {match_ratio:.1f}%\n"
    else:
        dir_line = ""
        match_line = ""

    risk_line = ""
    if divergence_risk.get("level") in ("medium", "high"):
        risk_line = f"⚠️ *Riesgo por divergencias:* {divergence_risk.get('reason','')}\n"

    message = (
        f"📊 *Análisis de {symbol}*\n"
        f"{tf_block}\n\n"
        f"🧭 *Tendencia mayor:* {major_trend} ({major_coherence:.2f}%)\n"
        f"{dir_line}"
        f"{match_line}"
        f"🧪 *Divergencias:* {div_text}\n"
        f"{risk_line}"
        f"🧬 *Sesgo técnico (smart):* {bias_human} (confianza {smart_conf:.2f})\n"
        f"🧮 *Confianza global:* {confidence_label}\n"
        f"\n📌 *Recomendación:* {recommendation}"
    )

    return result, message


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    r, m = analyze_and_format("BTCUSDT", direction_hint="long")
    print(m)
