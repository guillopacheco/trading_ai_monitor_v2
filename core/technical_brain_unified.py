"""
core/technical_brain_unified.py
--------------------------------
Motor Técnico Unificado A+ (versión estable)

Este módulo centraliza el análisis técnico para:

- Señales nuevas
- Reactivación de señales pendientes
- Monitoreo de posiciones abiertas

Depende únicamente de:
- core.indicators_core.fetch_indicators
- utils.normalizers (normalización 0–1)
- services.bybit_service (a través de indicators_core)

Las funciones públicas son:

    async run_full_analysis(symbol, direction)
    async evaluate_reactivation(symbol, direction)
    async analyze_open_position(symbol, direction)

Estas funciones son las que usa core.signal_engine.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional

from core.indicators_core import fetch_indicators
from utils.normalizers import (
    normalize_trend,
    normalize_rsi,
    normalize_macd_hist,
    normalize_volatility,
    normalize_divergence,
    merge_block_scores,
    merge_multi_tf,
)

logger = logging.getLogger("technical_brain_unified")


# ================================================================
# 🔧 Utilidades internas
# ================================================================

def _normalize_direction(direction: str) -> str:
    """
    Normaliza la dirección a 'long' o 'short'.
    """
    if not direction:
        return "long"
    d = direction.strip().lower()
    if d in ("long", "buy", "l"):
        return "long"
    if d in ("short", "sell", "s"):
        return "short"
    return "long"


def _trend_label_from_bool(trend_raw: bool) -> str:
    """
    Traduce el booleano de tendencia básica a etiqueta textual.
    """
    if trend_raw is True:
        return "bullish"
    if trend_raw is False:
        return "bearish"
    return "neutral"


def _grade_from_score(score: float) -> str:
    """
    Convierte el score global (0–1) a A/B/C/D.
    """
    if score >= 0.80:
        return "A"
    if score >= 0.65:
        return "B"
    if score >= 0.50:
        return "C"
    return "D"


def _bias_from_score(score: float) -> str:
    """
    Sesgo general de mercado según el score global.
    """
    if score >= 0.60:
        return "bullish"
    if score <= 0.40:
        return "bearish"
    return "neutral"


# ================================================================
# 🔹 Análisis de UNA temporalidad (TF)
# ================================================================

async def _analyze_timeframe(symbol: str, tf_name: str, tf_code: str) -> Dict[str, Any]:
    """
    Obtiene indicadores de una TF y genera un bloque normalizado.
    tf_name: etiqueta amigable (ej. '1H', '4H', '1D')
    tf_code: código de timeframe para la API (ej. '60', '240', 'D' o '1440')
    """
    try:
        data = await fetch_indicators(symbol, tf_code)
    except Exception as e:
        logger.error(f"❌ Error obteniendo indicadores para {symbol} ({tf_name}): {e}")
        data = None

    if not data:
        return {
            "ok": False,
            "tf": tf_name,
            "trend_label": "neutral",
            "score": 0.5,
            "norm": {},
            "raw": {},
        }

    # Datos crudos
    rsi = data.get("rsi")
    macd_hist = data.get("macd_hist")
    atr_pct = data.get("atr_pct")
    trend_raw = data.get("trend_raw")
    divergence = data.get("divergence")

    # Normalización por componente
    trend_text = "up" if trend_raw else "down"
    n_trend = normalize_trend(trend_text)
    n_rsi = normalize_rsi(rsi)
    n_macd = normalize_macd_hist(macd_hist)
    n_vol = normalize_volatility(atr_pct)
    n_div = normalize_divergence(divergence)

    block_norm = {
        "trend": n_trend,
        "rsi": n_rsi,
        "macd": n_macd,
        "volatility": n_vol,
        "divergence": n_div,
    }

    # Score del bloque
    block_score = merge_block_scores(block_norm)

    return {
        "ok": True,
        "tf": tf_name,
        "trend_label": _trend_label_from_bool(trend_raw),
        "score": block_score,
        "norm": block_norm,
        "raw": data,
    }


# ================================================================
# 🔹 Motor principal para señales nuevas
# ================================================================

async def run_full_analysis(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Motor principal del análisis técnico A+ para señales nuevas.
    Retorna un dict que usa directamente core.signal_engine.
    """

    logger.info(f"🧠 Ejecutando run_full_analysis para {symbol} ({direction})")

    direction_norm = _normalize_direction(direction)

    # Definimos los timeframes que vamos a usar
    # Puedes ajustar los códigos según tu implementación de Bybit:
    # - '60'  → 1H
    # - '240' → 4H
    # - 'D' o '1440' → 1D
    tf_map = {
        "1H": "60",
        "4H": "240",
        "1D": "1440",
    }

    # Ejecutar análisis de TF en paralelo
    tasks = [
        _analyze_timeframe(symbol, tf_name, tf_code)
        for tf_name, tf_code in tf_map.items()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)

    blocks: Dict[str, Dict[str, Any]] = {}
    for res in results:
        tf_name = res["tf"]
        blocks[tf_name] = res

    # Score global (0–1) a partir de los bloques
    global_score = merge_multi_tf(blocks)

    # Calificación y sesgo
    grade = _grade_from_score(global_score)
    bias = _bias_from_score(global_score)

    ok = any(b.get("ok") for b in blocks.values())

    return {
        "ok": ok,
        "symbol": symbol,
        "direction": direction_norm,
        "blocks": blocks,
        "global_score": global_score,
        "entry_grade": grade,
        "bias": bias,
    }


# ================================================================
# 🔹 Motor para reactivación de señales
# ================================================================

async def evaluate_reactivation(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Evalúa si una señal pendiente merece ser reactivada.
    Usa los mismos bloques que run_full_analysis, pero con umbrales distintos.
    """

    logger.info(f"♻️ Evaluando reactivación para {symbol} ({direction})")

    analysis = await run_full_analysis(symbol, direction)

    if not analysis["ok"]:
        return {
            "reactivate": False,
            "grade": "D",
            "global_score": 0.0,
            "analysis": analysis,
        }

    grade = analysis["entry_grade"]
    score = analysis["global_score"]

    # Regla simple de reactivación:
    # - A o B con score >= 0.60
    # - C solo si score >= 0.70 (caso muy específico)
    if grade in ("A", "B") and score >= 0.60:
        reactivate = True
    elif grade == "C" and score >= 0.70:
        reactivate = True
    else:
        reactivate = False

    return {
        "reactivate": reactivate,
        "grade": grade,
        "global_score": score,
        "analysis": analysis,
    }


# ================================================================
# 🔹 Motor para posiciones abiertas (detección de reversión)
# ================================================================

async def analyze_open_position(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Analiza una posición abierta y detecta posible reversión.
    Usado por controllers/positions_controller.py.
    """

    logger.info(f"🔍 Analizando posición abierta en {symbol} ({direction})")

    analysis = await run_full_analysis(symbol, direction)

    if not analysis["ok"]:
        return {
            "ok": False,
            "symbol": symbol,
            "direction": _normalize_direction(direction),
            "analysis": analysis,
            "reversal": False,
        }

    direction_norm = _normalize_direction(direction)
    score = analysis["global_score"]

    # Regla simple de reversión:
    # - Si es LONG y el score cae < 0.40 → posible reversión
    # - Si es SHORT y el score sube > 0.60 → posible reversión
    if direction_norm == "long":
        reversal = score < 0.40
    else:
        reversal = score > 0.60

    return {
        "ok": True,
        "symbol": symbol,
        "direction": direction_norm,
        "analysis": analysis,
        "reversal": reversal,
    }
