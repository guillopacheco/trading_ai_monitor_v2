"""
core/signal_engine.py
---------------------
MOTOR TÉCNICO UNIFICADO
Este archivo reemplaza TODOS los motores anteriores (wrapper, smart, trend_system, technical_brain_unified)

Funciones principales:
    ✔ fetch_multi_tf_data()       → descarga datos multi-TF desde Bybit
    ✔ analyze_timeframe()         → indicadores de una TF
    ✔ combine_timeframes()        → consolidación multi-TF
    ✔ calculate_match_ratio()     → puntaje global 0–100%
    ✔ analyze_signal()            → análisis de entrada inicial
    ✔ analyze_reactivation()      → evaluación de reactivación
    ✔ analyze_reversal()          → análisis para posiciones abiertas
"""

import logging
from typing import Dict, Any, Optional

from core.indicators_core import (
    compute_indicators,
    detect_divergences,
    select_best_intervals,
)

from services.bybit_service import (
    get_ohlcv,
    get_symbol_price,
)

from services import db_service

from utils.helpers import now_ts
from utils.formatters import (
    format_match_ratio_text,
    format_recommendation_text,
)

from models.signal import Signal

from config import DEBUG_MODE


logger = logging.getLogger("signal_engine")


# ============================================================
# 🔵 1. DESCARGA MULTI-TEMPORALIDAD
# ============================================================

TF_MAP = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
}


def fetch_multi_tf_data(symbol: str, tfs: list) -> Dict[str, Any]:
    """
    Descarga OHLCV para varias temporalidades.
    Devuelve: { "1h": df, "4h": df, ... }
    """
    data = {}
    for tf in tfs:
        try:
            interval = TF_MAP.get(tf)
            if not interval:
                continue

            df = get_ohlcv(symbol, interval=interval, limit=200)
            if df is not None and not df.empty:
                data[tf] = df
            else:
                logger.warning(f"⚠️ Sin datos para {symbol} {tf}")

        except Exception as e:
            logger.error(f"❌ Error descargando {symbol} {tf}: {e}")

    return data


# ============================================================
# 🔵 2. ANALISIS POR TEMPORALIDAD
# ============================================================

def analyze_timeframe(df):
    """
    Aplica indicadores + divergencias a un DF.
    """
    ind = compute_indicators(df)
    if not ind:
        return None

    macd_div = detect_divergences(df, method="macd")
    rsi_div = detect_divergences(df, method="rsi")

    ind["macd_divergence"] = macd_div
    ind["rsi_divergence"] = rsi_div
    return ind


# ============================================================
# 🔵 3. COMBINACIÓN MULTI-TF
# ============================================================

def combine_timeframes(results: Dict[str, dict], direction: str) -> Dict[str, Any]:
    """
    Consolida todas las TF en un solo resultado.
    Se usa para match_ratio y recomendación.
    """
    total = 0
    trend_score = 0
    div_score = 0

    for tf, r in results.items():
        total += 1

        # Tendencia
        tf_trend = r.get("trend")
        if tf_trend == direction:
            trend_score += 1

        # Divergencias
        macd_div = r.get("macd_divergence")
        rsi_div = r.get("rsi_divergence")

        if direction == "long":
            if macd_div == "bullish":
                div_score += 1
            if rsi_div == "bullish":
                div_score += 1

        else:  # short
            if macd_div == "bearish":
                div_score += 1
            if rsi_div == "bearish":
                div_score += 1

    trend_pct = trend_score / total if total else 0
    div_pct = div_score / (total * 2) if total else 0

    match_ratio = round((trend_pct * 0.65 + div_pct * 0.35) * 100, 2)

    return {
        "match_ratio": match_ratio,
        "trend_pct": trend_pct,
        "divergence_pct": div_pct,
    }


# ============================================================
# 🔵 4. REGLAS DE RECOMENDACIÓN
# ============================================================

def recommendation_from_ratio(match_ratio: float, direction: str) -> Dict[str, str]:
    """
    Devuelve:
        {
          "allowed": True/False,
          "reason": "...",
          "quality": "A/B/C/D"
        }
    """

    if match_ratio >= 80:
        return {
            "allowed": True,
            "quality": "A",
            "reason": f"Condiciones fuertes para operación {direction.upper()}",
        }

    if 65 <= match_ratio < 80:
        return {
            "allowed": True,
            "quality": "B",
            "reason": f"Condiciones buenas para operación {direction.upper()}",
        }

    if 50 <= match_ratio < 65:
        return {
            "allowed": False,
            "quality": "C",
            "reason": "Condiciones medias, esperar mejor setup",
        }

    return {
        "allowed": False,
        "quality": "D",
        "reason": "Condiciones débiles, no entrar",
    }


# ============================================================
# 🔵 5. ANALISIS COMPLETO DE UNA SEÑAL (ENTRADA)
# ============================================================

def analyze_signal(signal: Signal) -> Dict[str, Any]:
    """
    Motor principal para evaluar si una señal nueva es viable.
    """

    try:
        logger.info(f"🧠 Analizando señal nueva: {signal.symbol}")

        # Multi-TF disponibles
        all_data = fetch_multi_tf_data(
            symbol=signal.symbol,
            tfs=["4h", "1h", "15m", "5m"]
        )

        best = select_best_intervals(all_data, n=3)
        if DEBUG_MODE:
            logger.info(f"🧠 TF seleccionadas: {best}")

        # Analizar cada TF
        tf_results = {}
        for tf in best:
            res = analyze_timeframe(all_data[tf])
            if res:
                tf_results[tf] = res

        if not tf_results:
            return {
                "allowed": False,
                "match_ratio": 0,
                "reason": "Sin datos suficientes"
            }

        # Consolidación multi-TF
        combined = combine_timeframes(tf_results, direction=signal.direction)
        match_ratio = combined["match_ratio"]

        # Reglas
        rec = recommendation_from_ratio(match_ratio, signal.direction)

        # Registrar log
        db_service.add_analysis_log(
            signal_id=signal.id,
            match_ratio=match_ratio,
            recommendation=rec["reason"],
            details=str(combined)
        )

        return {
            "allowed": rec["allowed"],
            "quality": rec["quality"],
            "match_ratio": match_ratio,
            "reason": rec["reason"],
            "tf_results": tf_results,
            "combined": combined,
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_signal: {e}")
        return {
            "allowed": False,
            "match_ratio": 0,
            "reason": "Error interno en motor técnico"
        }


# ============================================================
# 🔵 6. ANALISIS DE REACTIVACIÓN
# ============================================================

def analyze_reactivation(signal: Signal) -> Dict[str, Any]:
    """
    Igual que analyze_signal(), pero más estricto.
    """

    result = analyze_signal(signal)
    ratio = result.get("match_ratio", 0)

    return {
        **result,
        "reactivated": ratio >= 70   # regla
    }


# ============================================================
# 🔵 7. REVERSIÓN DE POSICIÓN (para operaciones abiertas)
# ============================================================

def analyze_reversal(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Útil para positions_controller.
    Indica si la tendencia general cambió en contra.
    """

    # Mirar 1h + 4h
    data = fetch_multi_tf_data(symbol, ["1h", "4h"])

    if "1h" not in data or "4h" not in data:
        return {"reversal": False, "reason": "Insuficiente data"}

    r1 = analyze_timeframe(data["1h"])
    r4 = analyze_timeframe(data["4h"])

    if not r1 or not r4:
        return {"reversal": False}

    if direction == "long":
        if r1["trend"] == "bearish" and r4["trend"] == "bearish":
            return {"reversal": True, "reason": "Tendencia general bajista"}

    if direction == "short":
        if r1["trend"] == "bullish" and r4["trend"] == "bullish":
            return {"reversal": True, "reason": "Tendencia general alcista"}

    return {"reversal": False}
