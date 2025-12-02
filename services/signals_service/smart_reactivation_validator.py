"""
smart_reactivation_validator.py
--------------------------------
Módulo de VALIDACIÓN DE REACTIVACIÓN INTELIGENTE.

Objetivo:
- Evitar reactivaciones tipo QUSDT (TP2 alcanzado y luego se muere el movimiento).
- Distinguir entre:
    - Reactivar (la tendencia sigue fuerte a favor).
    - Esperar (hay dudas / rebote técnico).
    - Cancelar reactivación (alto riesgo de reversión).

Se apoya en:
- Tendencia por EMAs (rápida / lenta).
- Momentum (MACD, RSI, estocástico).
- Contexto de volatilidad (ATR / elasticidad de Bollinger).
- Posición del precio respecto a bandas / EMAs.
- “Hint” opcional de divergencias (texto ya calculado por el motor principal).

API principal:
    validate_reactivation_intelligently(...)
Devuelve un dict listo para ser interpretado por signal_reactivation_sync.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any, List, Tuple

import logging
import numpy as np
import pandas as pd
import pandas_ta as ta  # ya se usa en otros módulos del proyecto

from services.bybit_service.bybit_client import get_ohlcv_data

logger = logging.getLogger("smart_reactivation")

Side = Literal["LONG", "SHORT"]
Decision = Literal["reactivar", "esperar", "cancelar"]


# ============================================================================
# 🔹 Dataclasses de resultado
# ============================================================================

@dataclass
class ReactivationScores:
    trend_score: float
    momentum_score: float
    volatility_score: float
    exhaustion_penalty: float
    divergence_penalty: float
    total_score: float


@dataclass
class ReactivationDecision:
    symbol: str
    side: Side
    decision: Decision
    score: float
    reasons: List[str]
    scores: ReactivationScores
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # scores como dict simple
        d["scores"] = asdict(self.scores)
        return d


# ============================================================================
# 🔹 Utilidades técnicas internas
# ============================================================================

def _load_ohlcv(symbol: str, tf: str, limit: int = 200) -> Optional[pd.DataFrame]:
    """
    Envuelve get_ohlcv_data para obtener datos limpios.
    Se asume que get_ohlcv_data ya devuelve columnas:
    ['open','high','low','close','volume', ...] y un índice datetime.
    """
    try:
        df = get_ohlcv_data(symbol, tf, limit=limit)
    except Exception as e:
        logger.error(f"❌ Error al obtener OHLCV {symbol} ({tf}): {e}")
        return None

    if df is None or df.empty:
        logger.warning(f"⚠️ Sin datos OHLCV para {symbol} ({tf})")
        return None

    # Aseguramos orden por tiempo
    df = df.sort_index()
    return df


def _add_indicators(df: pd.DataFrame,
                    ema_fast: int = 10,
                    ema_slow: int = 30) -> pd.DataFrame:
    """Añade EMAs, RSI, MACD, Estocástico, ATR, Bandas de Bollinger."""
    out = df.copy()

    # EMAs
    out["ema_fast"] = ta.ema(out["close"], length=ema_fast)
    out["ema_slow"] = ta.ema(out["close"], length=ema_slow)

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

    # ATR
    out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)

    # Bandas de Bollinger (20, 2)
    bb = ta.bbands(out["close"], length=20, std=2)
    if bb is not None:
        out["bb_lower"] = bb[f"BBL_20_2.0"]
        out["bb_mid"] = bb[f"BBM_20_2.0"]
        out["bb_upper"] = bb[f"BBU_20_2.0"]
        out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]

    return out


def _trend_direction(row: pd.Series, side: Side) -> float:
    """
    Devuelve un valor de -1 a +1 indicando qué tan alineada está la
    micro-tendencia con el side pedido.
    """
    ema_fast = row.get("ema_fast")
    ema_slow = row.get("ema_slow")
    if pd.isna(ema_fast) or pd.isna(ema_slow):
        return 0.0

    # si estamos en LONG, queremos ema_fast > ema_slow
    # si estamos en SHORT, queremos ema_fast < ema_slow
    diff = (ema_fast - ema_slow) / ema_slow if ema_slow != 0 else 0
    if side == "LONG":
        base = np.clip(diff * 10, -1, 1)
    else:
        base = np.clip(-diff * 10, -1, 1)
    return float(base)


def _trend_slope(df: pd.DataFrame, side: Side, lookback: int = 5) -> float:
    """
    Evalúa la pendiente de la EMA rápida en las últimas N velas.
    Valor aproximado entre -1 y +1.
    """
    if len(df) < lookback + 1:
        return 0.0
    ema = df["ema_fast"].tail(lookback + 1).values
    if np.any(np.isnan(ema)):
        return 0.0
    # cambio relativo
    delta = ema[-1] - ema[0]
    rel = delta / ema[0] if ema[0] != 0 else 0.0
    # si el side es LONG, queremos pendiente positiva; SHORT, negativa
    if side == "LONG":
        val = np.clip(rel * 10, -1, 1)
    else:
        val = np.clip(-rel * 10, -1, 1)
    return float(val)


def _momentum_score(row: pd.Series, side: Side) -> float:
    """
    Momentum combinado:
    - MACD hist
    - RSI vs 50
    - Estocástico (K y D) direccional
    Devuelve valor aprox entre -1 y +1.
    """
    score = 0.0
    # Peso MACD
    macd_hist = row.get("macd_hist")
    if not pd.isna(macd_hist):
        if side == "LONG":
            score += np.tanh(macd_hist * 8) * 0.5
        else:
            score += np.tanh(-macd_hist * 8) * 0.5

    # Peso RSI
    rsi = row.get("rsi")
    if not pd.isna(rsi):
        if side == "LONG":
            score += ((rsi - 50) / 50.0) * 0.3  # >0 si RSI >50
        else:
            score += ((50 - rsi) / 50.0) * 0.3  # >0 si RSI <50

    # Peso Estocástico (queremos que vaya a favor)
    k = row.get("stoch_k")
    d = row.get("stoch_d")
    if not pd.isna(k) and not pd.isna(d):
        # dirección actual (K vs D)
        if side == "LONG":
            score += 0.2 if k > d else -0.1
        else:
            score += 0.2 if k < d else -0.1

    # normalizamos a [-1,1]
    score = float(np.clip(score, -1, 1))
    return score


def _volatility_info(row: pd.Series) -> Tuple[float, float]:
    """
    Devuelve:
    - ratio_atr = ATR / close (proxy de volatilidad).
    - bb_width   (amplitud de Bollinger).
    """
    close = row.get("close")
    atr = row.get("atr")
    bb_width = row.get("bb_width")

    ratio_atr = 0.0
    if not pd.isna(atr) and not pd.isna(close) and close != 0:
        ratio_atr = float(atr / close)

    if pd.isna(bb_width):
        bb_width = 0.0

    return ratio_atr, float(bb_width)


def _exhaustion_penalty(row: pd.Series, side: Side) -> float:
    """
    Penalización por agotamiento extremo.
    - Si RSI > 75 en LONG → cuidado (probable corrección).
    - Si RSI < 25 en SHORT → cuidado.
    - Si precio tocando banda externa → también penaliza algo.
    Devuelve un valor negativo (0 si no hay agotamiento).
    """
    rsi = row.get("rsi")
    close = row.get("close")
    bb_upper = row.get("bb_upper")
    bb_lower = row.get("bb_lower")

    penalty = 0.0

    if not pd.isna(rsi):
        if side == "LONG" and rsi > 75:
            penalty -= 0.5
        if side == "SHORT" and rsi < 25:
            penalty -= 0.5

    if not any(pd.isna([close, bb_upper, bb_lower])):
        # Si estamos en LONG y pegados a banda superior → agotamiento alcista
        if side == "LONG" and close >= bb_upper:
            penalty -= 0.3
        # Si estamos en SHORT y pegados a banda inferior → agotamiento bajista
        if side == "SHORT" and close <= bb_lower:
            penalty -= 0.3

    return penalty


def _divergence_penalty(divergences_hint: Optional[Dict[str, str]],
                        side: Side) -> float:
    """
    Interpretación simple del texto de divergencias que ya
    construye el motor técnico principal.

    Ejemplos:
      - "RSI: Alcista (1h)" en un SHORT  => penaliza.
      - "MACD: Bajista (4h)" en un LONG  => penaliza.
    """
    if not divergences_hint:
        return 0.0

    text = " ".join(v for v in divergences_hint.values() if v)
    text = text.lower()

    penalty = 0.0
    if side == "LONG":
        # divergencias bajistas van en contra
        if "bajista" in text:
            penalty -= 0.6
    else:  # SHORT
        if "alcista" in text:
            penalty -= 0.6

    return penalty


# ============================================================================
# 🔹 Función principal de validación
# ============================================================================

def validate_reactivation_intelligently(
    symbol: str,
    side: Side,
    entry_price: float,
    tf_entry: str = "15m",
    tf_confirm: str = "1h",
    divergences_hint: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Mega-módulo de VALIDACIÓN DE REACTIVACIÓN.

    Parámetros
    ----------
    symbol : par en formato BYBIT, ej. "QUSDT".
    side   : "LONG" o "SHORT" (dirección original de la señal).
    entry_price : precio de entrada original de la señal.
    tf_entry    : timeframe operativo principal (normalmente 15m).
    tf_confirm  : timeframe superior de confirmación (normalmente 1h).
    divergences_hint : dict opcional con texto de divergencias ya
        calculadas por el motor principal. Ej:
        {"RSI": "Alcista (1h)", "MACD": "Ninguna"}.

    Retorna
    -------
    dict con campos:
        - allowed (bool)
        - decision ("reactivar" | "esperar" | "cancelar")
        - score (0–100)
        - reasons (lista de frases)
        - scores (sub-scores internos)
        - metrics (info técnica para logs / debug)
    """

    # ------------------------------
    # 1) Cargar datos
    # ------------------------------
    df_entry = _load_ohlcv(symbol, tf_entry, limit=200)
    df_confirm = _load_ohlcv(symbol, tf_confirm, limit=200)

    if df_entry is None or df_confirm is None:
        msg = "Sin datos suficientes en uno de los timeframes."
        logger.warning(f"⚠️ {symbol}: {msg}")
        result = ReactivationDecision(
            symbol=symbol,
            side=side,
            decision="esperar",
            score=0.0,
            reasons=[msg],
            scores=ReactivationScores(
                trend_score=0,
                momentum_score=0,
                volatility_score=0,
                exhaustion_penalty=0,
                divergence_penalty=0,
                total_score=0,
            ),
            metrics={},
        )
        return result.to_dict()

    # ------------------------------
    # 2) Calcular indicadores
    # ------------------------------
    df_entry = _add_indicators(df_entry)
    df_confirm = _add_indicators(df_confirm)

    last_e = df_entry.iloc[-1]
    last_c = df_confirm.iloc[-1]

    reasons: List[str] = []

    # ------------------------------
    # 3) Trend score (entry + confirm)
    # ------------------------------
    trend_dir_e = _trend_direction(last_e, side)
    trend_dir_c = _trend_direction(last_c, side)
    slope_e = _trend_slope(df_entry, side, lookback=6)
    slope_c = _trend_slope(df_confirm, side, lookback=4)

    trend_score_raw = (trend_dir_e * 0.4 +
                       trend_dir_c * 0.4 +
                       slope_e * 0.1 +
                       slope_c * 0.1)
    # Escalamos a 0–40 puntos
    trend_score = float(np.clip((trend_score_raw + 1) / 2 * 40, 0, 40))

    if trend_dir_e > 0 and trend_dir_c > 0:
        reasons.append("Tendencia alineada en ambos timeframes.")
    elif trend_dir_e > 0 or trend_dir_c > 0:
        reasons.append("Tendencia mixta, parcialmente alineada.")
    else:
        reasons.append("Tendencia global en contra de la dirección de la señal.")

    # ------------------------------
    # 4) Momentum score (entry)
    # ------------------------------
    mom_raw = _momentum_score(last_e, side)
    # 0–30 puntos
    momentum_score = float(np.clip((mom_raw + 1) / 2 * 30, 0, 30))

    if mom_raw > 0.3:
        reasons.append("Momentum todavía fuerte a favor de la operación.")
    elif mom_raw < -0.3:
        reasons.append("Momentum debilitado / posible rebote en contra.")
    else:
        reasons.append("Momentum neutro o poco definido.")

    # ------------------------------
    # 5) Volatilidad / elasticidad
    # ------------------------------
    ratio_atr, bb_width = _volatility_info(last_e)
    # ratio_atr típico entre 0.003 y 0.05 aprox
    # Escalamos a 0–20, pero penalizamos extremos demasiado altos.
    if ratio_atr <= 0:
        vol_score = 10.0
        reasons.append("Volatilidad desconocida, se asume neutra.")
    else:
        # preferimos una volatilidad moderada (~1–3%)
        ideal = 0.015
        dist = abs(ratio_atr - ideal) / ideal
        vol_score = max(0.0, 20.0 * (1 - dist))
        if dist < 0.5:
            reasons.append("Volatilidad saludable para continuar el movimiento.")
        else:
            reasons.append("Volatilidad poco óptima (demasiado baja o demasiado alta).")

    volatility_score = float(vol_score)

    # ------------------------------
    # 6) Agotamiento (RSI + bandas)
    # ------------------------------
    exhaustion_penalty = _exhaustion_penalty(last_e, side)
    if exhaustion_penalty < 0:
        reasons.append("Señales de agotamiento en la dirección de la operación.")

    # ------------------------------
    # 7) Divergencias (hint externo)
    # ------------------------------
    divergence_penalty = _divergence_penalty(divergences_hint, side)
    if divergence_penalty < 0:
        reasons.append("Divergencias técnicas activas en contra de la dirección.")

    # ------------------------------
    # 8) Composición de score final
    # ------------------------------
    total_score = (
        trend_score +
        momentum_score +
        volatility_score +
        exhaustion_penalty * 20 +   # cada -0.5 quita ~10 puntos
        divergence_penalty * 25     # cada -0.6 quita ~15 puntos
    )

    # Recortamos a [0,100]
    total_score = float(np.clip(total_score, 0, 100))

    # ------------------------------
    # 9) Decisión según score
    # ------------------------------
    if total_score >= 65:
        decision: Decision = "reactivar"
        reasons.append("Score alto: reactivación técnicamente sólida.")
    elif total_score >= 40:
        decision = "esperar"
        reasons.append("Score medio: mejor esperar confirmaciones extra.")
    else:
        decision = "cancelar"
        reasons.append("Score bajo: alto riesgo de reversión, mejor no reactivar.")

    scores = ReactivationScores(
        trend_score=trend_score,
        momentum_score=momentum_score,
        volatility_score=volatility_score,
        exhaustion_penalty=exhaustion_penalty,
        divergence_penalty=divergence_penalty,
        total_score=total_score,
    )

    # ------------------------------
    # 10) Métricas para debug / logs
    # ------------------------------
    metrics: Dict[str, Any] = {
        "tf_entry": tf_entry,
        "tf_confirm": tf_confirm,
        "entry_price": float(entry_price),
        "close_entry_tf": float(last_e["close"]),
        "rsi_entry": float(last_e.get("rsi", np.nan)),
        "macd_hist_entry": float(last_e.get("macd_hist", np.nan)),
        "stoch_k_entry": float(last_e.get("stoch_k", np.nan)),
        "stoch_d_entry": float(last_e.get("stoch_d", np.nan)),
        "ratio_atr": ratio_atr,
        "bb_width": bb_width,
        "trend_dir_entry": trend_dir_e,
        "trend_dir_confirm": trend_dir_c,
        "slope_entry": slope_e,
        "slope_confirm": slope_c,
        "divergences_hint": divergences_hint or {},
    }

    decision_obj = ReactivationDecision(
        symbol=symbol,
        side=side,
        decision=decision,
        score=total_score,
        reasons=reasons,
        scores=scores,
        metrics=metrics,
    )

    return decision_obj.to_dict()
