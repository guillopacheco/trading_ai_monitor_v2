"""
core/technical_brain_unified.py
--------------------------------
Motor Técnico Unificado A+ (modelo total)

Este módulo centraliza TODO el análisis técnico:

- Multi–timeframe (4H, 1H, 30M, 15M + micro 5M/1M)
- Tendencia, momentum, volatilidad, estructura
- Divergencias clásicas + smart_divergences
- Smart bias (continuación / reversión)
- Smart Entry (evaluate_entry)
- Hook para reactivación inteligente
- Hook para reversión de posiciones

Entrada principal:
    run_unified_analysis(symbol, direction_hint, context="entry", **kwargs)

Salida:
    dict con campos:
        - symbol, direction, context
        - allowed (bool)
        - decision (str)
        - grade (A/B/C/D)
        - match_ratio (0–100)
        - technical_score (0–100)
        - global_confidence (🟢/🟡/🔴)
        - risk_class (low/medium/high/extreme)
        - trend, momentum, volatility, structure, divergences, micro
        - smart_entry, smart_reactivation, smart_reversal
        - reason (texto humano)
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta  # type: ignore

from services.bybit_service import get_ohlcv

# Integraciones opcionales (no rompemos si no existen)
try:
    from smart_divergences import detect_smart_divergences
except Exception:  # pragma: no cover
    detect_smart_divergences = None  # type: ignore

try:
    from smart_entry_validator import evaluate_entry
except Exception:  # pragma: no cover
    evaluate_entry = None  # type: ignore

try:
    from smart_reactivation_validator import validate_reactivation_intelligently
except Exception:  # pragma: no cover
    validate_reactivation_intelligently = None  # type: ignore

try:
    # En tu config actual existe ANALYSIS_DEBUG_MODE
    from config import ANALYSIS_DEBUG_MODE as DEBUG_MODE  # type: ignore
except Exception:  # pragma: no cover
    DEBUG_MODE = False  # fallback seguro

logger = logging.getLogger("technical_brain_unified")


# ============================================================
# 🔧 Utilidades básicas
# ============================================================

_TIMEFRAME_MAP = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "1d": "D",
}

_MAIN_TFS = ["4h", "1h", "30m", "15m"]
_MICRO_TFS = ["5m", "1m"]


def _safe_pct(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return float(n) / float(d) * 100.0


def _load_ohlcv_tf(symbol: str, tf: str, limit: int = 300) -> Optional[pd.DataFrame]:
    """Carga OHLCV desde bybit_service para un timeframe dado."""
    interval = _TIMEFRAME_MAP.get(tf)
    if interval is None:
        logger.warning(f"⚠️ Timeframe no soportado: {tf}")
        return None

    df = get_ohlcv(symbol, interval=interval, limit=limit)
    if df is None or df.empty:
        logger.warning(f"⚠️ Sin datos OHLCV para {symbol} ({tf})")
        return None

    # Asegurar orden por tiempo ascendente
    df = df.sort_index()
    return df


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega indicadores necesarios."""
    out = df.copy()

    # EMAs básicas
    out["ema_fast"] = ta.ema(out["close"], length=10)
    out["ema_slow"] = ta.ema(out["close"], length=30)

    # RSI
    out["rsi"] = ta.rsi(out["close"], length=14)

    # MACD estándar
    macd = ta.macd(out["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        out["macd"] = macd["MACD_12_26_9"]
        out["macd_signal"] = macd["MACDs_12_26_9"]
        out["macd_hist"] = macd["MACDh_12_26_9"]

    # Estocástico
    stoch = ta.stoch(out["high"], out["low"], out["close"], k=14, d=3, smooth_k=3)
    if stoch is not None:
        out["stoch_k"] = stoch["STOCHk_14_3_3"]
        out["stoch_d"] = stoch["STOCHd_14_3_3"]

    # ATR para volatilidad
    atr = ta.atr(out["high"], out["low"], out["close"], length=14)
    if atr is not None:
        out["atr"] = atr

    # MFI para divergencias smart
    mfi = ta.mfi(out["high"], out["low"], out["close"], out["volume"], length=14)
    if mfi is not None:
        out["mfi"] = mfi

    return out


def _trend_code_from_series(
    close: pd.Series, ema_fast: pd.Series, ema_slow: pd.Series
) -> Tuple[str, float]:
    """Devuelve ('bull'/'bear'/'sideways', score 0-100)."""
    if close.empty or ema_fast.empty or ema_slow.empty:
        return "sideways", 0.0

    c = close.iloc[-1]
    ef = ema_fast.iloc[-1]
    es = ema_slow.iloc[-1]

    # slope de ema rápida
    slope = float(ema_fast.diff().iloc[-5:].mean())

    if c > ef > es and slope > 0:
        return "bull", 80.0 + min(20.0, abs(slope) * 500)
    if c < ef < es and slope < 0:
        return "bear", 80.0 + min(20.0, abs(slope) * 500)

    # cerca de las EMAs → rango
    if abs(c - ef) / max(1e-8, abs(ef)) < 0.002:
        return "sideways", 40.0

    return "sideways", 30.0


def _momentum_score(rsi: float, macd_hist: float, adx: Optional[float] = None) -> float:
    """Score simple de momentum."""
    score = 0.0

    if not np.isnan(rsi):
        # 50 es neutro, 30-70 rango saludable
        if 40 <= rsi <= 60:
            score += 35
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            score += 25
        else:
            score += 10

    if not np.isnan(macd_hist):
        score += max(0.0, 30.0 - abs(macd_hist) * 200)

    if adx is not None and not np.isnan(adx):
        if adx > 25:
            score += 20
        elif adx > 15:
            score += 10

    return max(0.0, min(100.0, score))


def _volatility_score(atr: float, price: float) -> Tuple[float, str]:
    """
    Calcula score de volatilidad y clase:
      - Muy alta → riesgo extremo
      - Media → ideal
      - Muy baja → lateral peligroso
    """
    if price <= 0 or np.isnan(price) or np.isnan(atr):
        return 50.0, "unknown"

    ratio = atr / price  # % rango diario aproximado

    if ratio > 0.08:
        return 25.0, "extreme"
    if ratio > 0.04:
        return 60.0, "high"
    if ratio > 0.02:
        return 90.0, "medium"
    return 50.0, "low"


def _structure_score(close: float, ema_fast: float, ema_slow: float) -> Tuple[float, bool]:
    """
    Estructura básica:
      - si precio muy extendido vs EMA rápida → peligro
      - si precio demasiado pegado a ema lenta → lateral
    """
    if any(np.isnan(x) for x in [close, ema_fast, ema_slow]):
        return 50.0, False

    dist_fast = abs(close - ema_fast) / max(1e-8, abs(ema_fast))
    dist_slow = abs(close - ema_slow) / max(1e-8, abs(ema_slow))

    overextended = dist_fast > 0.03  # >3%

    if overextended:
        return 30.0, True
    if dist_slow < 0.005:
        return 40.0, False
    return 80.0, False


def _risk_class_from_score(score: float) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "high"
    return "extreme"


def _confidence_label_from_score(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 55:
        return "🟡"
    return "🔴"


def _major_trend_from_tfs(tf_info: Dict[str, Dict[str, Any]]) -> Tuple[str, float]:
    """
    Calcula tendencia mayor ("bull"/"bear"/"sideways") y confianza.
    Usa principalmente 4H y 1H.
    """
    weights = {
        "4h": 0.6,
        "1h": 0.3,
        "30m": 0.1,
    }
    bull = 0.0
    bear = 0.0
    side = 0.0

    for tf, info in tf_info.items():
        code = info.get("trend_code", "sideways")
        s = info.get("trend_score", 0.0)
        w = weights.get(tf, 0.0)
        if code == "bull":
            bull += s * w
        elif code == "bear":
            bear += s * w
        else:
            side += s * w

    total = bull + bear + side
    if total == 0:
        return "sideways", 0.0

    if bull >= bear and bull >= side:
        return "bull", bull / total
    if bear >= bull and bear >= side:
        return "bear", bear / total
    return "sideways", side / total


def _smart_bias_code(major_trend_code: str, direction: Optional[str]) -> str:
    """
    Clasificación de sesgo:
        continuation / bullish-reversal / bearish-reversal / neutral
    """
    if direction is None:
        return "neutral"

    direction = direction.lower()
    if major_trend_code == "bull":
        if direction == "long":
            return "continuation"
        if direction == "short":
            return "bearish-reversal"
    if major_trend_code == "bear":
        if direction == "short":
            return "continuation"
        if direction == "long":
            return "bullish-reversal"
    return "neutral"


# ============================================================
# 🔍 Análisis multi–TF principal
# ============================================================

def _analyze_timeframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Analiza un único timeframe con los indicadores ya calculados."""
    last = df.iloc[-1]

    trend_code, trend_score = _trend_code_from_series(
        df["close"], df["ema_fast"], df["ema_slow"]
    )

    rsi = float(last.get("rsi", np.nan))
    macd_hist = float(last.get("macd_hist", np.nan))
    atr = float(last.get("atr", np.nan)) if "atr" in df.columns else np.nan
    price = float(last["close"])

    mom_score = _momentum_score(rsi, macd_hist)
    vol_score, vol_class = _volatility_score(atr, price)
    struct_score, overextended = _structure_score(
        price, float(last["ema_fast"]), float(last["ema_slow"])
    )

    return {
        "trend_code": trend_code,
        "trend_score": trend_score,
        "rsi": rsi,
        "macd_hist": macd_hist,
        "atr": atr,
        "price": price,
        "momentum_score": mom_score,
        "volatility_score": vol_score,
        "volatility_class": vol_class,
        "structure_score": struct_score,
        "overextended": overextended,
    }


# ============================================================
# 🧠 Motor principal
# ============================================================

def run_unified_analysis(
    symbol: str,
    direction_hint: Optional[str] = None,
    context: str = "entry",
    timeframes: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Motor técnico A+.

    symbol: par, ej. "GIGGLEUSDT"
    direction_hint: "long"/"short"/None
    context:
        - "entry"        → señal nueva
        - "reactivation" → señal pendiente
        - "position"     → posición abierta
    kwargs:
        - entry_price (float, opcional, para reactivación/posición)
        - loss_pct      (float, opcional, para posición)
    """
    direction_hint = (direction_hint or "").lower() or None
    tfs = timeframes or _MAIN_TFS

    tf_data: Dict[str, pd.DataFrame] = {}
    tf_info: Dict[str, Dict[str, Any]] = {}

    # 1) Cargar datos multi-TF
    for tf in tfs:
        try:
            raw = _load_ohlcv_tf(symbol, tf)
            if raw is None:
                continue
            df = _add_indicators(raw)
            if len(df) < 50:
                logger.warning(f"⚠️ Muy pocos datos para {symbol} ({tf})")
                continue
            tf_data[tf] = df
            tf_info[tf] = _analyze_timeframe(df)
        except Exception as e:
            logger.error(f"❌ Error procesando TF {tf} para {symbol}: {e}")

    if not tf_info:
        logger.error(f"❌ No se pudo obtener ningún timeframe válido para {symbol}")
        return {
            "symbol": symbol,
            "direction": direction_hint,
            "context": context,
            "allowed": False,
            "decision": "error",
            "grade": "D",
            "match_ratio": 0.0,
            "technical_score": 0.0,
            "global_confidence": "🔴",
            "risk_class": "extreme",
            "trend": {},
            "momentum": {},
            "volatility": {},
            "structure": {},
            "divergences": {},
            "micro": {},
            "smart_entry": {},
            "smart_reactivation": {},
            "smart_reversal": {},
            "reason": "No se pudieron obtener datos suficientes para el análisis.",
        }

    # 2) Tendencia mayor
    major_trend_code, trend_confidence = _major_trend_from_tfs(tf_info)

    # 3) Divergencias smart (solo en TF principal 1H o 30M)
    main_tf = "1h" if "1h" in tf_data else ("30m" if "30m" in tf_data else list(tf_data.keys())[0])
    main_df = tf_data[main_tf]
    smart_divs: Dict[str, Any] = {}
    divergence_score = 50.0

    if detect_smart_divergences is not None:
        try:
            smart_divs = detect_smart_divergences(main_df)
            # Heurística simple: penalizar si hay divergencias fuertes en contra
            flags = smart_divs.get("summary", {}) if isinstance(smart_divs, dict) else {}
            num_bearish = int(flags.get("bearish_count", 0))
            num_bullish = int(flags.get("bullish_count", 0))
            if direction_hint == "long":
                divergence_score = max(0.0, 70.0 + (num_bullish * 5) - (num_bearish * 15))
            elif direction_hint == "short":
                divergence_score = max(0.0, 70.0 + (num_bearish * 5) - (num_bullish * 15))
            else:
                divergence_score = 60.0
        except Exception as e:
            logger.warning(f"⚠️ Error en detect_smart_divergences: {e}")
            smart_divs = {}
            divergence_score = 50.0

    # 4) Agregar micro–TF (5m/1m)
    micro_info: Dict[str, Any] = {}
    for micro_tf in _MICRO_TFS:
        try:
            raw_m = _load_ohlcv_tf(symbol, micro_tf, limit=200)
            if raw_m is None:
                continue
            df_m = _add_indicators(raw_m)
            if len(df_m) < 50:
                continue
            micro_info[micro_tf] = _analyze_timeframe(df_m)
        except Exception as e:
            logger.warning(f"⚠️ Error en micro-TF {micro_tf} para {symbol}: {e}")

    # 5) Consolidar scores globales
    trend_scores = [info["trend_score"] for info in tf_info.values()]
    mom_scores = [info["momentum_score"] for info in tf_info.values()]
    vol_scores = [info["volatility_score"] for info in tf_info.values()]
    struct_scores = [info["structure_score"] for info in tf_info.values()]

    trend_score = float(np.mean(trend_scores)) if trend_scores else 0.0
    momentum_score = float(np.mean(mom_scores)) if mom_scores else 0.0
    volatility_score = float(np.mean(vol_scores)) if vol_scores else 0.0
    structure_score = float(np.mean(struct_scores)) if struct_scores else 0.0
    micro_score = float(np.mean([m["momentum_score"] for m in micro_info.values()])) if micro_info else 50.0

    # technical_score global (ponderado)
    technical_score = (
        trend_score * 0.30
        + momentum_score * 0.20
        + divergence_score * 0.20
        + structure_score * 0.10
        + volatility_score * 0.05
        + micro_score * 0.15
    )
    technical_score = max(0.0, min(100.0, technical_score))

    # match_ratio: cuánto se alinea con la dirección de la señal
    if direction_hint is None:
        match_ratio = technical_score
    else:
        aligned = 0.0
        for tf, info in tf_info.items():
            code = info.get("trend_code", "sideways")
            if direction_hint == "long" and code == "bull":
                aligned += 1.0
            elif direction_hint == "short" and code == "bear":
                aligned += 1.0
        match_ratio = _safe_pct(aligned, len(tf_info))

    # Grado técnico básico (antes de Smart Entry)
    if technical_score >= 80 and match_ratio >= 75:
        technical_grade = "A"
    elif technical_score >= 65 and match_ratio >= 60:
        technical_grade = "B"
    elif technical_score >= 50 and match_ratio >= 45:
        technical_grade = "C"
    else:
        technical_grade = "D"

    confidence = technical_score / 100.0
    risk_class = _risk_class_from_score(technical_score)
    global_conf = _confidence_label_from_score(technical_score)

    smart_bias_code = _smart_bias_code(major_trend_code, direction_hint)

    # Snapshot para Smart Entry
    snapshot = {
        "grade": technical_grade,
        "technical_grade": technical_grade,
        "technical_score": technical_score,
        "match_ratio": match_ratio,
        "confidence": confidence,
        "major_trend_code": major_trend_code,
        "smart_bias_code": smart_bias_code,
        "smart_bias": smart_bias_code,
        "divergences": smart_divs,
    }

    smart_entry_block: Dict[str, Any] = {}
    if context == "entry" and evaluate_entry is not None:
        try:
            smart_entry_block = evaluate_entry(symbol, direction_hint, snapshot)
        except Exception as e:
            logger.warning(f"⚠️ Error en evaluate_entry: {e}")
            smart_entry_block = {}

    # Decisión base según contexto
    decision = "wait"
    allowed = False
    grade = technical_grade
    decision_reasons: List[str] = []

    if context == "entry":
        if smart_entry_block:
            allowed = bool(smart_entry_block.get("entry_allowed", False))
            grade = smart_entry_block.get("entry_grade", technical_grade)
            entry_mode = smart_entry_block.get("entry_mode", "warn")
            if allowed and entry_mode == "ok":
                decision = "enter"
            elif allowed and entry_mode == "warn":
                decision = "wait"
            else:
                decision = "reject"
            decision_reasons.append(
                smart_entry_block.get("entry_summary", "Entrada evaluada por motor inteligente.")
            )
        else:
            # fallback simple
            if technical_grade in ("A", "B") and match_ratio >= 65:
                allowed = True
                decision = "enter"
                decision_reasons.append("Setup técnico sólido (grade A/B, match_ratio alto).")
            elif technical_grade == "C":
                allowed = False
                decision = "wait"
                decision_reasons.append("Condiciones medias, mejor esperar un setup más claro.")
            else:
                allowed = False
                decision = "reject"
                decision_reasons.append("Condiciones débiles, alta probabilidad de fallo.")

    elif context == "reactivation":
        # Hook al validador inteligente de reactivación si está disponible
        entry_price = kwargs.get("entry_price")
        smart_reactivation_block: Dict[str, Any] = {}
        if validate_reactivation_intelligently is not None and entry_price:
            try:
                side = "LONG" if direction_hint == "long" else "SHORT"
                smart_reactivation_block = validate_reactivation_intelligently(
                    symbol=symbol,
                    side=side,
                    entry_price=float(entry_price),
                    divergences_hint=smart_divs.get("labels") if isinstance(smart_divs, dict) else None,
                )
            except Exception as e:
                logger.warning(f"⚠️ Error en validate_reactivation_intelligently: {e}")
                smart_reactivation_block = {}

        # lógica simplificada + smart si existe
        if smart_reactivation_block:
            decision = smart_reactivation_block.get("decision", "esperar")
            score = smart_reactivation_block.get("score", 0.0)
            allowed = decision == "reactivar"
            if allowed:
                decision_reasons.append(f"Reactivación aprobada (score={score:.1f}).")
            else:
                decision_reasons.append(f"Reactivación no aprobada (decision={decision}).")
        else:
            # fallback: usar technical_grade + match_ratio
            if technical_grade in ("A", "B") and match_ratio >= 70:
                allowed = True
                decision = "reactivate"
                decision_reasons.append("Condiciones técnicas fuertes para reactivar la señal.")
            elif technical_grade == "C":
                allowed = False
                decision = "wait"
                decision_reasons.append("Condiciones medias, esperar mejor contexto para reactivar.")
            else:
                allowed = False
                decision = "cancel"
                decision_reasons.append("Condiciones débiles, reactivación desaconsejada.")

    elif context == "position":
        # Evaluación básica de posición abierta
        loss_pct = float(kwargs.get("loss_pct", 0.0))
        reversal_risk = 0.0

        # Penalizar si divergencias fuertes en contra
        if direction_hint == "long":
            if divergence_score < 50:
                reversal_risk += 20.0
        elif direction_hint == "short":
            if divergence_score < 50:
                reversal_risk += 20.0

        if technical_score < 50:
            reversal_risk += 30.0
        if match_ratio < 40:
            reversal_risk += 20.0
        if loss_pct <= -30:
            reversal_risk += 30.0

        if reversal_risk >= 60:
            decision = "close_or_reverse"
            allowed = False
            decision_reasons.append("Riesgo de reversión elevado según análisis técnico global.")
        elif reversal_risk >= 30:
            decision = "watch"
            allowed = False
            decision_reasons.append("Señales mixtas, vigilar la posición de cerca.")
        else:
            decision = "hold"
            allowed = True
            decision_reasons.append("Contexto técnico todavía favorable para mantener la posición.")

    # Texto humano principal
    if decision == "enter":
        reason = "Setup técnico de alta calidad. Entrada permitida."
    elif decision in ("reactivate", "reactivar"):
        reason = "Condiciones favorables para reactivar la señal."
    elif decision in ("close_or_reverse",):
        reason = "Riesgo técnico elevado. Se recomienda cerrar o revertir la operación."
    elif decision == "hold":
        reason = "Contexto técnico razonable para mantener la operación."
    elif decision in ("cancel",):
        reason = "Reactivación desaconsejada por condiciones técnicas débiles."
    elif decision in ("reject",):
        reason = "Entrada desaconsejada. Setup con baja probabilidad de éxito."
    else:
        reason = "Condiciones mixtas. Se recomienda esperar confirmaciones adicionales."

    # Bloques para la salida
    trend_block = {
        "per_tf": tf_info,
        "major_trend_code": major_trend_code,
        "trend_confidence": trend_confidence,
        "trend_score": trend_score,
    }

    momentum_block = {
        "momentum_score": momentum_score,
    }

    volatility_block = {
        "volatility_score": volatility_score,
    }

    structure_block = {
        "structure_score": structure_score,
    }

    micro_block = {
        "per_tf": micro_info,
        "micro_score": micro_score,
    }

    smart_reactivation_block_out: Dict[str, Any] = {}
    smart_reversal_block_out: Dict[str, Any] = {}

    if context == "reactivation" and "smart_reactivation_block" in locals():
        smart_reactivation_block_out = smart_reactivation_block

    if context == "position":
        smart_reversal_block_out = {
            "reversal_risk": reversal_risk,
            "loss_pct": loss_pct,
        }

    result: Dict[str, Any] = {
        "symbol": symbol,
        "direction": direction_hint,
        "context": context,
        "allowed": allowed,
        "decision": decision,
        "decision_reasons": decision_reasons,
        "grade": grade,
        "technical_grade": technical_grade,
        "technical_score": technical_score,
        "match_ratio": match_ratio,
        "global_confidence": global_conf,
        "risk_class": risk_class,
        "trend": trend_block,
        "momentum": momentum_block,
        "volatility": volatility_block,
        "structure": structure_block,
        "divergences": smart_divs,
        "divergence_score": divergence_score,
        "micro": micro_block,
        "smart_entry": smart_entry_block,
        "smart_reactivation": smart_reactivation_block_out,
        "smart_reversal": smart_reversal_block_out,
        "reason": reason,
    }

    if DEBUG_MODE:
        logger.debug(f"[DEBUG] Unified analysis for {symbol} ({context}): {result}")

    return result
