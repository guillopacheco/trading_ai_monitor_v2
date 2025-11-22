"""
motor_wrapper_core.py — Motor técnico multi-TF (núcleo)
-------------------------------------------------------
Responsabilidades:

- Elegir temporalidades en función de los datos disponibles:
  Preferencia: 4h, 1h, 30m, 15m
  Si 4h no tiene suficientes velas → 1h, 30m, 15m, 5m

- Descargar OHLCV desde Bybit (bybit_client.get_ohlcv_data)
- Calcular indicadores clave:
  * EMA corta / larga (por defecto 10 / 30)
  * MACD (12/26/9 por defecto)
  * RSI (14)
- Clasificar tendencia por timeframe (Alcista / Bajista / Lateral)
- Detectar divergencias simples RSI / MACD (alcista / bajista)
- Calcular votación de tendencia y compatibilidad con la dirección
  sugerida por la señal (LONG/SHORT).

Este módulo NO formatea mensajes para Telegram; eso lo hace
trend_system_final.py en analyze_and_format().
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta

from bybit_client import get_ohlcv_data
from config import (
    EMA_SHORT_PERIOD,
    EMA_LONG_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ANALYSIS_MODE,
)

logger = logging.getLogger("motor_wrapper")


# ============================================================
# 🔧 Utilidades internas
# ============================================================
MIN_BARS_PER_TF = 120  # mínimo para considerar un TF “usable”


def _get_ohlcv(symbol: str, interval: str, limit: int = 300) -> pd.DataFrame | None:
    """Wrapper seguro sobre get_ohlcv_data."""
    try:
        df = get_ohlcv_data(symbol, interval=interval, limit=limit)
        if df is None or df.empty:
            return None

        # Asegurar columnas estándar
        cols = {"open", "high", "low", "close", "volume"}
        if not cols.issubset(df.columns):
            logger.warning(f"⚠️ {symbol} ({interval}) sin columnas OHLCV completas.")
            return None

        return df.copy()
    except Exception as e:
        logger.error(f"❌ Error obteniendo OHLCV {symbol} ({interval}): {e}")
        return None


def _choose_timeframes(symbol: str) -> List[str]:
    """
    Elige las temporalidades usando la política acordada:

    Preferencia:
      ["240", "60", "30", "15"]  (4h, 1h, 30m, 15m)

    Si 4h no tiene suficientes velas:
      ["60", "30", "15", "5"]   (1h, 30m, 15m, 5m)
    """
    preferred = ["240", "60", "30", "15"]
    fallback = ["60", "30", "15", "5"]

    # Comprobar 4h solamente; si no hay datos suficientes, usamos fallback
    df_4h = _get_ohlcv(symbol, "240", limit=MIN_BARS_PER_TF)
    if df_4h is None or len(df_4h) < MIN_BARS_PER_TF:
        logger.info(f"ℹ️ {symbol}: 4h insuficiente → usando TF fallback.")
        tfs = []
        for tf in fallback:
            df = _get_ohlcv(symbol, tf, limit=MIN_BARS_PER_TF)
            if df is not None and len(df) >= MIN_BARS_PER_TF:
                tfs.append(tf)
        return tfs

    # 4h sí disponible → intentar usar los 4 TF preferidos
    tfs: List[str] = []
    for tf in preferred:
        df = _get_ohlcv(symbol, tf, limit=MIN_BARS_PER_TF)
        if df is not None and len(df) >= MIN_BARS_PER_TF:
            tfs.append(tf)

    # En caso extremo, si algo falla, devolvemos lo que haya
    if not tfs:
        for tf in fallback:
            df = _get_ohlcv(symbol, tf, limit=MIN_BARS_PER_TF)
            if df is not None and len(df) >= MIN_BARS_PER_TF:
                tfs.append(tf)

    return tfs


def _calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Añade EMA, MACD y RSI al DataFrame."""
    close = df["close"]

    df["ema_short"] = ta.ema(close, length=EMA_SHORT_PERIOD)
    df["ema_long"] = ta.ema(close, length=EMA_LONG_PERIOD)

    macd = ta.macd(close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    if macd is not None:
        df["macd"] = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_hist"] = macd["MACDh_12_26_9"]
    else:
        df["macd"] = np.nan
        df["macd_signal"] = np.nan
        df["macd_hist"] = 0.0

    df["rsi"] = ta.rsi(close, length=14)

    return df


def _trend_from_votes(bull: int, bear: int) -> Tuple[str, str]:
    """
    Devuelve (trend_label, trend_code):

    - trend_label: 'Alcista' / 'Bajista' / 'Lateral / Mixta'
    - trend_code:  'bull' / 'bear' / 'sideways'
    """
    if bull >= bear + 1:
        return "Alcista", "bull"
    if bear >= bull + 1:
        return "Bajista", "bear"
    return "Lateral / Mixta", "sideways"


def _detect_simple_divergence(
    price: pd.Series,
    indicator: pd.Series,
    lookback: int = 40,
    tolerance: float = 0.01,
) -> str:
    """
    Detección MUY SIMPLE de divergencias:

    - Divergencia bajista:
        precio hace máx. más alto y el indicador un máx. más bajo.
    - Divergencia alcista:
        precio hace mín. más bajo y el indicador un mín. más alto.

    Usamos solo el tramo reciente (lookback).
    Retorna: 'alcista', 'bajista' o 'ninguna'.
    """
    price = price.dropna()
    indicator = indicator.dropna()
    if len(price) < lookback + 5 or len(indicator) < lookback + 5:
        return "ninguna"

    p = price.iloc[-lookback:]
    i = indicator.iloc[-lookback:]

    # Máximos y mínimos “globales” en la ventana
    p1_high = p.iloc[:-5].max()
    p2_high = p.iloc[-5:].max()
    i1_high = i.iloc[:-5].max()
    i2_high = i.iloc[-5:].max()

    p1_low = p.iloc[:-5].min()
    p2_low = p.iloc[-5:].min()
    i1_low = i.iloc[:-5].min()
    i2_low = i.iloc[-5:].min()

    # Bearish: precio sube, indicador baja
    if p2_high > p1_high * (1 + tolerance) and i2_high < i1_high * (1 - tolerance):
        return "bajista"

    # Bullish: precio baja, indicador sube
    if p2_low < p1_low * (1 - tolerance) and i2_low > i1_low * (1 + tolerance):
        return "alcista"

    return "ninguna"


# ============================================================
# 🔍 Análisis por timeframe
# ============================================================
def analyze_single_tf(
    symbol: str,
    tf: str,
) -> Dict[str, Any] | None:
    """
    Devuelve un dict con el análisis de UN timeframe:

    {
      "tf": "60",
      "tf_label": "1h",
      "trend_label": "Alcista",
      "trend_code": "bull",
      "votes_bull": 3,
      "votes_bear": 1,
      "rsi": 62.5,
      "macd_hist": 0.0012,
      "ema_short": 0.1234,
      "ema_long": 0.1200,
      "div_rsi": "alcista" / "bajista" / "ninguna",
      "div_macd": "alcista" / "bajista" / "ninguna",
    }
    """
    df = _get_ohlcv(symbol, tf, limit=260)
    if df is None or len(df) < MIN_BARS_PER_TF:
        return None

    df = _calc_indicators(df)

    last = df.iloc[-1]
    rsi = float(last["rsi"])
    ema_s = float(last["ema_short"])
    ema_l = float(last["ema_long"])
    macd_hist = float(last["macd_hist"])
    close = float(last["close"])

    # Votos de tendencia
    bull = 0
    bear = 0

    # Precio vs EMA larga
    if close > ema_l:
        bull += 1
    elif close < ema_l:
        bear += 1

    # EMA corta vs larga (pendiente de la tendencia)
    if ema_s > ema_l:
        bull += 1
    elif ema_s < ema_l:
        bear += 1

    # MACD hist
    if macd_hist > 0:
        bull += 1
    elif macd_hist < 0:
        bear += 1

    # RSI (≥55 tendencia alcista; ≤45 bajista)
    if rsi >= 55:
        bull += 1
    elif rsi <= 45:
        bear += 1

    trend_label, trend_code = _trend_from_votes(bull, bear)

    # Divergencias simples
    div_rsi = _detect_simple_divergence(df["close"], df["rsi"])
    div_macd = _detect_simple_divergence(df["close"], df["macd"])

    tf_map = {
        "240": "4h",
        "60": "1h",
        "30": "30m",
        "15": "15m",
        "5": "5m",
        "1": "1m",
    }
    tf_label = tf_map.get(tf, tf)

    return {
        "tf": tf,
        "tf_label": tf_label,
        "trend_label": trend_label,
        "trend_code": trend_code,
        "votes_bull": bull,
        "votes_bear": bear,
        "rsi": rsi,
        "macd_hist": macd_hist,
        "ema_short": ema_s,
        "ema_long": ema_l,
        "close": close,
        "div_rsi": div_rsi,
        "div_macd": div_macd,
    }


# ============================================================
# 🧠 Motor principal multi-TF
# ============================================================
def get_multi_tf_snapshot(
    symbol: str,
    direction_hint: str | None = None,
) -> Dict[str, Any]:
    """
    Analiza el símbolo en varias temporalidades y devuelve un snapshot:

    {
      "symbol": "EPICUSDT",
      "direction_hint": "long" / "short" / None,
      "timeframes": [
          {...},  # TF más alto
          {...},  # ...
      ],
      "major_trend_label": "...",
      "major_trend_code": "bull/bear/sideways",
      "trend_score": float 0-1,
      "match_ratio": float 0-100,
      "divergences": { "RSI": "Alcista (1h)", "MACD": "Bajista (4h)" } ...
      ...
    }
    """
    direction_hint = (direction_hint or "").lower()
    if direction_hint not in ("long", "short"):
        direction_hint = None

    tfs = _choose_timeframes(symbol)
    if not tfs:
        raise RuntimeError(f"No se pudieron obtener temporalidades válidas para {symbol}.")

    tf_results: List[Dict[str, Any]] = []
    for tf in tfs:
        res = analyze_single_tf(symbol, tf)
        if res:
            tf_results.append(res)

    if not tf_results:
        raise RuntimeError(f"Falló el análisis técnico para {symbol}: sin TF válidos.")

    # ---------------------- Tendencia global ----------------------
    # Peso según jerarquía (TF más alto con mayor peso)
    weights: Dict[str, float] = {}
    total_tfs = len(tf_results)
    for idx, tf_res in enumerate(tf_results):
        # Ej: para 4 TF → pesos 4,3,2,1
        weights[tf_res["tf"]] = float(total_tfs - idx)

    bull_w = 0.0
    bear_w = 0.0
    side_w = 0.0

    for tf_res in tf_results:
        w = weights[tf_res["tf"]]
        code = tf_res["trend_code"]
        if code == "bull":
            bull_w += w
        elif code == "bear":
            bear_w += w
        else:
            side_w += w

    if bull_w >= bear_w and bull_w >= side_w:
        major_trend_code = "bull"
        major_trend_label = "Alcista"
    elif bear_w >= bull_w and bear_w >= side_w:
        major_trend_code = "bear"
        major_trend_label = "Bajista"
    else:
        major_trend_code = "sideways"
        major_trend_label = "Lateral / Mixta"

    total_w = bull_w + bear_w + side_w
    trend_score = bull_w / total_w if major_trend_code == "bull" else \
        (bear_w / total_w if major_trend_code == "bear" else side_w / total_w)

    # ---------------------- Match ratio con la señal ----------------------
    match_ratio = 50.0
    if direction_hint:
        prefer = "bull" if direction_hint == "long" else "bear"
        for_tf = 0.0
        against_tf = 0.0
        for tf_res in tf_results:
            w = weights[tf_res["tf"]]
            code = tf_res["trend_code"]
            if code == prefer:
                for_tf += w
            elif code in ("bull", "bear"):
                against_tf += w
        denom = for_tf + against_tf
        if denom > 0:
            match_ratio = 100.0 * for_tf / denom
        else:
            match_ratio = 50.0  # neutro si no hay definición clara

    # ---------------------- Divergencias agregadas ----------------------
    div_rsi_global = "Ninguna"
    div_macd_global = "Ninguna"

    # Priorizamos TF más alto donde haya divergencia
    for tf_res in tf_results:
        label = tf_res["tf_label"]
        if tf_res["div_rsi"] != "ninguna":
            direction = "Alcista" if tf_res["div_rsi"] == "alcista" else "Bajista"
            div_rsi_global = f"{direction} ({label})"
            break

    for tf_res in tf_results:
        label = tf_res["tf_label"]
        if tf_res["div_macd"] != "ninguna":
            direction = "Alcista" if tf_res["div_macd"] == "alcista" else "Bajista"
            div_macd_global = f"{direction} ({label})"
            break

    divergences = {
        "RSI": div_rsi_global,
        "MACD": div_macd_global,
    }

    # ---------------------- Smart bias ----------------------
    smart_bias_code = "neutral"

    # Condición de posible giro:
    # - Tendencia mayor alcista + divergencias bajistas importantes
    # - Tendencia mayor bajista + divergencias alcistas importantes
    has_bear_div = any(
        res["div_rsi"] == "bajista" or res["div_macd"] == "bajista"
        for res in tf_results
    )
    has_bull_div = any(
        res["div_rsi"] == "alcista" or res["div_macd"] == "alcista"
        for res in tf_results
    )

    if major_trend_code == "bull" and has_bear_div:
        smart_bias_code = "bearish-reversal"
    elif major_trend_code == "bear" and has_bull_div:
        smart_bias_code = "bullish-reversal"
    elif major_trend_code in ("bull", "bear") and trend_score >= 0.6:
        smart_bias_code = "continuation"

    # ---------------------- Confianza global ----------------------
    # Base en función de ANALYSIS_MODE
    if ANALYSIS_MODE == "aggressive":
        base_conf = 0.35
    elif ANALYSIS_MODE == "conservative":
        base_conf = 0.25
    else:  # balanced
        base_conf = 0.30

    conf = base_conf + (match_ratio / 100.0) * 0.5 + (trend_score * 0.2)

    # Penalizar divergencias contra la dirección sugerida
    if direction_hint:
        if direction_hint == "long" and "Bajista" in (div_rsi_global + div_macd_global):
            conf -= 0.15
        if direction_hint == "short" and "Alcista" in (div_rsi_global + div_macd_global):
            conf -= 0.15

    conf = max(0.0, min(conf, 1.0))

    return {
        "symbol": symbol,
        "direction_hint": direction_hint,
        "timeframes": tf_results,
        "major_trend_label": major_trend_label,
        "major_trend_code": major_trend_code,
        "trend_score": float(trend_score),
        "match_ratio": float(match_ratio),
        "divergences": divergences,
        "smart_bias_code": smart_bias_code,
        "confidence": float(conf),
    }
