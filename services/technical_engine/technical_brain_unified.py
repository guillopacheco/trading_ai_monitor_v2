"""
technical_brain_unified.py
--------------------------
Capa de ORQUESTACIÓN del motor técnico.

⚠️ IMPORTANTE
Este módulo **no** calcula indicadores directamente. Toda la lógica
pesada vive en `technical_engine.py` (motor único real).

Aquí solo:
    - Normalizamos parámetros.
    - Llamamos a `technical_engine.analyze(...)`.
    - Adaptamos el resultado al formato esperado por:
        * smart_reactivation_validator.py
        * position_reversal_monitor.py
        * telegram_reader.py
        * command_bot.py  (/analizar)

De esta forma:
    - Hay UN SOLO motor técnico real.
    - Cambios futuros se hacen en `technical_engine.py` sin romper el resto.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import logging

from services.technical_engine.technical_engine import analyze as core_analyze

logger = logging.getLogger("technical_brain_unified")


def _norm_direction(direction_hint: Optional[str]) -> Optional[str]:
    """Normaliza el lado a 'long' / 'short' o None."""
    if not direction_hint:
        return None
    d = direction_hint.strip().lower()
    if d.startswith("long") or d.startswith("buy"):
        return "long"
    if d.startswith("short") or d.startswith("sell"):
        return "short"
    return None


def run_unified_analysis(
    *,
    symbol: str,
    direction_hint: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Punto ÚNICO de entrada para todo análisis técnico de la app.

    Parámetros
    ----------
    symbol:
        Par en Bybit, ej. 'BTCUSDT', 'PIPPINUSDT'.
    direction_hint:
        'long' / 'short' si se conoce el lado de la señal/operación.
    context:
        'entry' | 'reactivation' | 'reversal' | 'operation' | 'manual'
    roi:
        ROI actual de la operación (si aplica, en % incluyendo apalancamiento).
    loss_pct:
        Pérdida flotante estimada (si aplica, en %).

    Retorna
    -------
    dict con las claves que esperan los módulos de alto nivel:

        {
            "symbol": "...",
            "direction_hint": "long"/"short"/None,

            "snapshot": {
                "symbol": "...",
                "direction_hint": "...",
                "timeframes": [...],
                "major_trend_code": "bull/bear/sideways",
                "major_trend_label": "Alcista / Bajista / Lateral",
                "trend_score": float 0–1,
                "match_ratio": float 0–100,
                "divergences": { "RSI": "...", "MACD": "..." },
                "smart_bias_code": "...",
                "smart_bias": "...",
                "confidence": float 0–1,
                "technical_score": float 0–100,
                "grade": "A" / "B" / "C" / "D",
            },

            "decision": {
                "allowed": bool,
                "decision": "enter" / "reactivate" / "close" / "wait" / "hedge" / "error",
                "decision_reasons": [...],
                "technical_score": float,
                "match_ratio": float,
                "grade": "A"–"D",
                "confidence": float,
                "context": "...",
                "roi": float|None,
                "loss_pct": float|None,
            },

            "smart_entry": {
                "entry_allowed": bool,
                "entry_grade": "A"–"D",
                "entry_mode": "ok" / "warn" / "block" / "error",
                "entry_score": float,
                "entry_reasons": [...],
            },

            "divergences": {...},
            "raw": { ... resultado original de technical_engine.analyze ... },
        }
    """

    norm_dir = _norm_direction(direction_hint)

    try:
        core_result = core_analyze(
            symbol=symbol,
            direction_hint=norm_dir,
            context=context,
            roi=roi,
            loss_pct=loss_pct,
        )
    except Exception as e:  # Falla dura del motor
        logger.error(f"❌ Error en run_unified_analysis({symbol}): {e}", exc_info=True)
        # Devolvemos estructura estándar en modo error, para no romper callers.
        return {
            "symbol": symbol,
            "direction_hint": norm_dir,
            "snapshot": {},
            "decision": {
                "allowed": False,
                "decision": "error",
                "decision_reasons": [str(e)],
                "technical_score": 0.0,
                "match_ratio": 0.0,
                "grade": "D",
                "confidence": 0.0,
                "context": context,
                "roi": roi,
                "loss_pct": loss_pct,
            },
            "smart_entry": {
                "entry_allowed": False,
                "entry_grade": "D",
                "entry_mode": "error",
                "entry_score": 0.0,
                "entry_reasons": [str(e)],
            },
            "divergences": {},
            "raw": {"error": str(e)},
        }

    if not isinstance(core_result, dict):
        logger.error(
            f"⚠️ technical_engine.analyze devolvió tipo inesperado: {type(core_result)}"
        )
        return {
            "symbol": symbol,
            "direction_hint": norm_dir,
            "snapshot": {},
            "decision": {
                "allowed": False,
                "decision": "error",
                "decision_reasons": [f"tipo inesperado: {type(core_result)}"],
                "technical_score": 0.0,
                "match_ratio": 0.0,
                "grade": "D",
                "confidence": 0.0,
                "context": context,
                "roi": roi,
                "loss_pct": loss_pct,
            },
            "smart_entry": {
                "entry_allowed": False,
                "entry_grade": "D",
                "entry_mode": "error",
                "entry_score": 0.0,
                "entry_reasons": [],
            },
            "divergences": {},
            "raw": {"raw": core_result},
        }

    # ------------------------------------------------------------------
    # 1) Extraer snapshot bruto multi-TF del bloque debug (si existe)
    # ------------------------------------------------------------------
    debug_block = core_result.get("debug") or {}
    raw_snapshot = debug_block.get("raw_snapshot") or {}

    # Fallbacks por si en el futuro se cambia el nombre del campo
    if not raw_snapshot and "snapshot" in core_result:
        raw_snapshot = core_result["snapshot"]

    # ------------------------------------------------------------------
    # 2) Construir snapshot normalizado para el resto de la app
    # ------------------------------------------------------------------
    snapshot: Dict[str, Any] = {
        "symbol": raw_snapshot.get("symbol", core_result.get("symbol", symbol)),
        "direction_hint": raw_snapshot.get("direction_hint", norm_dir),
        "timeframes": raw_snapshot.get("timeframes")
        or core_result.get("timeframes")
        or [],

        "major_trend_code": raw_snapshot.get("major_trend_code"),
        # Si el snapshot no tiene label textual, usamos lo que expone technical_engine
        "major_trend_label": raw_snapshot.get("major_trend_label")
        or core_result.get("major_trend")
        or "",

        "trend_score": raw_snapshot.get("trend_score"),
        "match_ratio": raw_snapshot.get("match_ratio", core_result.get("match_ratio", 0.0)),
        "divergences": raw_snapshot.get("divergences")
        or core_result.get("divergences")
        or {},

        "smart_bias_code": raw_snapshot.get("smart_bias_code")
        or core_result.get("smart_bias"),
        # Alias para compatibilidad con códigos antiguos
        "smart_bias": raw_snapshot.get("smart_bias_code")
        or core_result.get("smart_bias"),

        "confidence": raw_snapshot.get("confidence", core_result.get("confidence", 0.0)),
        "technical_score": raw_snapshot.get(
            "technical_score", core_result.get("technical_score", 0.0)
        ),
        "grade": raw_snapshot.get("grade", core_result.get("grade", "D")),
    }

    # ------------------------------------------------------------------
    # 3) Bloque de decisión global
    # ------------------------------------------------------------------
    decision: Dict[str, Any] = {
        "allowed": bool(core_result.get("allowed", False)),
        "decision": core_result.get("decision", "wait") or "wait",
        "decision_reasons": core_result.get("decision_reasons") or [],
        "technical_score": core_result.get("technical_score", 0.0),
        "match_ratio": core_result.get("match_ratio", 0.0),
        "grade": core_result.get("grade", snapshot.get("grade", "D")),
        "confidence": core_result.get("confidence", 0.0),
        "context": context,
        "roi": roi,
        "loss_pct": loss_pct,
    }

    # ------------------------------------------------------------------
    # 4) Bloque Smart Entry (ya integrado en technical_engine)
    # ------------------------------------------------------------------
    smart_entry: Dict[str, Any] = {
        "entry_allowed": core_result.get("entry_allowed", False),
        "entry_grade": core_result.get("entry_grade", snapshot.get("grade", "D")),
        "entry_mode": core_result.get("entry_mode", "ok"),
        "entry_score": core_result.get("entry_score", core_result.get("technical_score", 0.0)),
        "entry_reasons": core_result.get("entry_reasons") or [],
    }

    # ------------------------------------------------------------------
    # 5) Ensamblar respuesta final unificada
    # ------------------------------------------------------------------
    unified: Dict[str, Any] = {
        "symbol": symbol,
        "direction_hint": norm_dir,
        "snapshot": snapshot,
        "decision": decision,
        "smart_entry": smart_entry,
        "divergences": snapshot.get("divergences") or core_result.get("divergences") or {},
        "raw": core_result,
    }

    try:
        logger.debug(
            "✅ run_unified_analysis %s (%s) → %s [match=%.1f, score=%.1f, grade=%s]",
            symbol,
            norm_dir,
            decision["decision"],
            float(decision.get("match_ratio", 0.0)),
            float(decision.get("technical_score", 0.0)),
            decision.get("grade", "D"),
        )
    except Exception:
        # Nunca romper por culpa de un log
        pass

    return unified
