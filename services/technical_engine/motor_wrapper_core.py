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



from services.bybit_service.bybit_client import get_ohlcv_data
from config import (
    EMA_SHORT_PERIOD,
    EMA_LONG_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    ANALYSIS_MODE
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
    """Añade EMA, MACD, RSI y ATR al DataFrame."""
    close = df["close"]

    # EMAs
    df["ema_short"] = ta.ema(close, length=EMA_SHORT_PERIOD)
    df["ema_long"] = ta.ema(close, length=EMA_LONG_PERIOD)

    # MACD
    macd = ta.macd(close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    if macd is not None:
        df["macd"] = macd.iloc[:, 0]
        df["macd_signal"] = macd.iloc[:, 1]
        df["macd_hist"] = macd.iloc[:, 2]
    else:
        df["macd"] = np.nan
        df["macd_signal"] = np.nan
        df["macd_hist"] = 0.0

    # RSI
    df["rsi"] = ta.rsi(close, length=14)

    # ATR (para módulo de volatilidad)
    try:
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    except Exception:
        df["atr"] = np.nan

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
      "close": 0.1250,
      "atr": 0.0021,
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

    atr_val = 0.0
    if "atr" in df.columns:
        try:
            atr_raw = float(df["atr"].iloc[-1])
            if not np.isnan(atr_raw):
                atr_val = atr_raw
        except Exception:
            atr_val = 0.0

    # Votos de tendencia
    bull = 0
    bear = 0

    # Precio vs EMA larga
    if close > ema_l:
        bull += 1
    elif close < ema_l:
        bear += 1

    # EMA corta vs larga
    if ema_s > ema_l:
        bull += 1
    elif ema_s < ema_l:
        bear += 1

    # MACD hist
    if macd_hist > 0:
        bull += 1
    elif macd_hist < 0:
        bear += 1

    # RSI (≥55 alcista; ≤45 bajista)
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
        "atr": atr_val,
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
      "timeframes": [...],
      "major_trend_label": "...",
      "major_trend_code": "bull/bear/sideways",
      "trend_score": float 0–1,
      "match_ratio": float 0–100,
      "divergences": { "RSI": "...", "MACD": "..." },
      "smart_bias_code": "...",
      "confidence": float 0–1,
      "technical_score": float 0–100,
      "grade": "A" / "B" / "C" / "D",
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
    weights: Dict[str, float] = {}
    total_tfs = len(tf_results)
    for idx, tf_res in enumerate(tf_results):
        # Ej: para 4 TF → pesos 4,3,2,1
        weights[tf_res["tf"]] = float(total_tfs - idx)

    bull_w = bear_w = side_w = 0.0

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

    # ---------------------- Divergencias agregadas (texto) ----------------------
    div_rsi_global = "Ninguna"
    div_macd_global = "Ninguna"

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

    # ---------------------- Confianza global (igual que antes) ----------------------
    if ANALYSIS_MODE == "aggressive":
        base_conf = 0.35
    elif ANALYSIS_MODE == "conservative":
        base_conf = 0.25
    else:  # balanced
        base_conf = 0.30

    conf = base_conf + (match_ratio / 100.0) * 0.5 + (trend_score * 0.2)

    if direction_hint:
        if direction_hint == "long" and "Bajista" in (div_rsi_global + div_macd_global):
            conf -= 0.15
        if direction_hint == "short" and "Alcista" in (div_rsi_global + div_macd_global):
            conf -= 0.15

    conf = max(0.0, min(conf, 1.0))

    # ============================================================
    # 🧮 NUEVO SISTEMA DE PUNTAJES + ESCALA A–D
    # ============================================================

    # 1) Trend Score (0–40 pts)
    trend_pts = float(trend_score) * 40.0

    # 2) Multi-TF Coherency Score (0–25 pts)
    aligned = sum(1 for r in tf_results if r["trend_code"] == major_trend_code)
    total = len(tf_results) or 1
    if aligned >= 3:
        mtf_pts = 25.0
    elif aligned == 2:
        mtf_pts = 15.0
    elif aligned == 1:
        mtf_pts = 5.0
    else:
        mtf_pts = 0.0

    # 3) Divergence Score (20 / 10 / 5 / -10)
    support_div = 0
    contra_div = 0
    for r in tf_results:
        local_trend = r["trend_code"]
        for d in (r["div_rsi"], r["div_macd"]):
            if d == "alcista":
                if local_trend == "bull":
                    support_div += 1
                elif local_trend == "bear":
                    contra_div += 1
            elif d == "bajista":
                if local_trend == "bear":
                    support_div += 1
                elif local_trend == "bull":
                    contra_div += 1

    if support_div == 0 and contra_div == 0:
        div_pts = 10.0  # neutro
    elif contra_div > support_div:
        div_pts = -10.0  # divergencias contra estructura
    elif support_div > 0 and contra_div == 0:
        div_pts = 20.0 if support_div >= 2 else 10.0
    else:
        div_pts = 5.0  # mixtas

    # 4) Volatility & ATR Score (10 / 5 / -5)
    vol_pts = 5.0  # neutro por defecto
    base_tf = None
    for pref in ("30m", "1h", "15m", "4h", "5m", "1m"):
        for r in tf_results:
            if r["tf_label"] == pref:
                base_tf = r
                break
        if base_tf:
            break

    if base_tf and base_tf.get("atr", 0.0) > 0 and base_tf["close"] > 0:
        atr_pct = (base_tf["atr"] / base_tf["close"]) * 100.0
        if 0.3 <= atr_pct <= 3.0:
            vol_pts = 10.0   # ATR ideal
        elif 0.1 <= atr_pct < 0.3 or 3.0 < atr_pct <= 8.0:
            vol_pts = 5.0    # aceptable
        else:
            vol_pts = -5.0   # demasiado bajo o demasiado alto

    # 5) Smart Bias / Structure Bias Score (5 / 2 / -5)
    if smart_bias_code == "continuation":
        sb_pts = 5.0
    elif smart_bias_code == "neutral":
        sb_pts = 2.0
    else:  # reversals
        sb_pts = -5.0

    technical_score = trend_pts + mtf_pts + div_pts + vol_pts + sb_pts
    technical_score = max(0.0, min(technical_score, 100.0))

    # ============================================================
    # ⚠️ AJUSTE: Penalización por divergencia contraria en 1h/4h
    # ============================================================

    penalty = 0.0
    conf_penalty = 0.0
    warning_divergence = False

    # Detectar divergencias contrarias fuertes (solo 1h y 4h)
    for r in tf_results:
        if r["tf_label"] in ("1h", "4h"):
            # Divergencia alcista contra SHORT
            if direction_hint == "short" and (
                r["div_rsi"] == "alcista" or r["div_macd"] == "alcista"
            ):
                penalty += 20.0
                conf_penalty += 0.25
                warning_divergence = True

            # Divergencia bajista contra LONG
            if direction_hint == "long" and (
                r["div_rsi"] == "bajista" or r["div_macd"] == "bajista"
            ):
                penalty += 20.0
                conf_penalty += 0.25
                warning_divergence = True

            if warning_divergence:
                result_warning = "⚠️ Divergencia fuerte contraria detectada (1h/4h)."
            else:
                result_warning = ""

    # Aplicar penalización correctamente usando conf (variable real del motor)
    technical_score = max(0.0, technical_score - penalty)

    try:
        conf = max(0.0, conf - conf_penalty)
    except Exception:
        # Si conf no existiera por algún flujo raro, usamos valor estable
        conf = max(0.0, (locals().get("conf", 0.3)) - conf_penalty)

    if technical_score >= 85.0:
        grade = "A"
    elif technical_score >= 70.0:
        grade = "B"
    elif technical_score >= 50.0:
        grade = "C"
    else:
        grade = "D"

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
        "technical_score": float(technical_score),
        "grade": grade,
    }