# smart_divergences.py
# ------------------------------------------------------------
# Detección de divergencias "tipo TradingView":
# - Precio vs RSI
# - Precio vs MACD Histograma
# - Usa volumen y MFI como filtros de fuerza
# Devuelve un dict detallado para análisis manual y futuro auto-trading.
# ------------------------------------------------------------

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("smart_divergences")


def _find_swings(series: pd.Series, window: int = 3, kind: str = "low"):
    """
    Encuentra índices de swings (pivots) en una serie.
    kind = "low"  → mínimos locales
    kind = "high" → máximos locales
    """
    idxs = []
    values = series.values
    length = len(values)
    if length < 2 * window + 1:
        return idxs

    for i in range(window, length - window):
        chunk = values[i - window : i + window + 1]
        if kind == "low":
            if values[i] == chunk.min():
                idxs.append(i)
        else:
            if values[i] == chunk.max():
                idxs.append(i)
    return idxs


def _classify_strength(price_delta: float, indi_delta: float) -> str:
    """
    Clasifica fuerza de la divergencia en función de cuánto se mueve el indicador
    frente al movimiento relativo del precio.
    """
    if price_delta == 0:
        ratio = abs(indi_delta)
    else:
        ratio = abs(indi_delta) / (abs(price_delta) + 1e-9)

    if ratio > 3:
        return "strong"
    elif ratio > 1.5:
        return "medium"
    else:
        return "weak"


def detect_smart_divergences(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Detecta divergencias usando swings recientes de:
      - Precio vs RSI
      - Precio vs MACD Hist
    Usa MFI y volumen como filtros de confirmación.
    Requiere columnas: high, low, close, volume, rsi, macd_hist, mfi (y opcionalmente ema_short/ema_long).

    Returns (formato detallado):
    {
        "divergences": {
            "rsi": {
                "type": "bullish"/"bearish"/"none",
                "confirmed": bool,
                "strength": "weak"/"medium"/"strong"
            },
            "macd": { ... }
        },
        "overall_bias": "bullish-reversal" / "bearish-reversal" / "continuation" / "neutral",
        "confidence": float  # 0.0 - 1.0
    }
    """
    try:
        if df is None or df.empty:
            return _empty_result()

        if len(df) > lookback:
            df = df.tail(lookback).copy()

        required_cols = {"high", "low", "close", "volume", "rsi", "macd_hist", "mfi"}
        if not required_cols.issubset(df.columns):
            logger.debug(f"smart_divergences: columnas faltantes {required_cols - set(df.columns)}")
            return _empty_result()

        highs = df["high"]
        lows = df["low"]
        close = df["close"]
        rsi = df["rsi"]
        macd_hist = df["macd_hist"]
        mfi = df["mfi"]

        # ------------------------------------------
        # Swings de precio
        # ------------------------------------------
        low_idxs = _find_swings(lows, window=2, kind="low")
        high_idxs = _find_swings(highs, window=2, kind="high")

        # Usamos los dos últimos swings significativos
        rsi_div = {"type": "none", "confirmed": False, "strength": "weak"}
        macd_div = {"type": "none", "confirmed": False, "strength": "weak"}

        # ========== RSI ==========
        if len(low_idxs) >= 2 and len(rsi) >= max(low_idxs) + 1:
            i1, i2 = low_idxs[-2], low_idxs[-1]
            p1, p2 = lows.iloc[i1], lows.iloc[i2]
            r1, r2 = rsi.iloc[i1], rsi.iloc[i2]

            # Divergencia alcista → precio hace mínimo más bajo, RSI mínimo más alto
            if p2 < p1 and r2 > r1:
                price_delta = (p2 - p1) / max(abs(p1), 1e-9)
                indi_delta = r2 - r1
                strength = _classify_strength(price_delta, indi_delta)
                rsi_div["type"] = "bullish"
                rsi_div["strength"] = strength

        if len(high_idxs) >= 2 and len(rsi) >= max(high_idxs) + 1:
            j1, j2 = high_idxs[-2], high_idxs[-1]
            p1, p2 = highs.iloc[j1], highs.iloc[j2]
            r1, r2 = rsi.iloc[j1], rsi.iloc[j2]

            # Divergencia bajista → precio hace máximo más alto, RSI máximo más bajo
            if p2 > p1 and r2 < r1:
                price_delta = (p2 - p1) / max(abs(p1), 1e-9)
                indi_delta = r2 - r1
                strength = _classify_strength(price_delta, indi_delta)
                rsi_div["type"] = "bearish"
                rsi_div["strength"] = strength

        # ========== MACD Hist ==========
        if len(low_idxs) >= 2 and len(macd_hist) >= max(low_idxs) + 1:
            i1, i2 = low_idxs[-2], low_idxs[-1]
            p1, p2 = lows.iloc[i1], lows.iloc[i2]
            m1, m2 = macd_hist.iloc[i1], macd_hist.iloc[i2]

            # Divergencia alcista MACD → precio baja, histograma sube
            if p2 < p1 and m2 > m1:
                price_delta = (p2 - p1) / max(abs(p1), 1e-9)
                indi_delta = m2 - m1
                strength = _classify_strength(price_delta, indi_delta)
                macd_div["type"] = "bullish"
                macd_div["strength"] = strength

        if len(high_idxs) >= 2 and len(macd_hist) >= max(high_idxs) + 1:
            j1, j2 = high_idxs[-2], high_idxs[-1]
            p1, p2 = highs.iloc[j1], highs.iloc[j2]
            m1, m2 = macd_hist.iloc[j1], macd_hist.iloc[j2]

            # Divergencia bajista MACD → precio sube, histograma baja
            if p2 > p1 and m2 < m1:
                price_delta = (p2 - p1) / max(abs(p1), 1e-9)
                indi_delta = m2 - m1
                strength = _classify_strength(price_delta, indi_delta)
                macd_div["type"] = "bearish"
                macd_div["strength"] = strength

        # ------------------------------------------
        # Confirmación con estructura + MFI + Volumen
        # ------------------------------------------
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) >= 2 else last_close
        last_mfi = mfi.iloc[-1]
        prev_mfi = mfi.iloc[-2] if len(mfi) >= 2 else last_mfi

        ema_short = df.get("ema_short", pd.Series([np.nan] * len(df)))
        ema_long = df.get("ema_long", pd.Series([np.nan] * len(df)))
        last_es = ema_short.iloc[-1] if len(ema_short) else np.nan
        last_el = ema_long.iloc[-1] if len(ema_long) else np.nan

        # Confirmación bullish → precio deja de caer, MFI sube, EMA corta se gira
        if rsi_div["type"] == "bullish" or macd_div["type"] == "bullish":
            if last_close > prev_close and last_mfi > prev_mfi:
                if not np.isnan(last_es) and not np.isnan(last_el):
                    if last_es > last_el or last_es > ema_short.iloc[-2]:
                        if rsi_div["type"] == "bullish":
                            rsi_div["confirmed"] = True
                        if macd_div["type"] == "bullish":
                            macd_div["confirmed"] = True

        # Confirmación bearish → precio deja de subir, MFI baja, EMA corta se inclina abajo
        if rsi_div["type"] == "bearish" or macd_div["type"] == "bearish":
            if last_close < prev_close and last_mfi < prev_mfi:
                if not np.isnan(last_es) and not np.isnan(last_el):
                    if last_es < last_el or last_es < ema_short.iloc[-2]:
                        if rsi_div["type"] == "bearish":
                            rsi_div["confirmed"] = True
                        if macd_div["type"] == "bearish":
                            macd_div["confirmed"] = True

        # ------------------------------------------
        # Bias general + confianza
        # ------------------------------------------
        bullish_score = 0.0
        bearish_score = 0.0

        for d in (rsi_div, macd_div):
            if d["type"] == "bullish":
                base = 0.2
                if d["strength"] == "medium":
                    base = 0.3
                elif d["strength"] == "strong":
                    base = 0.4
                if d["confirmed"]:
                    base += 0.1
                bullish_score += base
            elif d["type"] == "bearish":
                base = 0.2
                if d["strength"] == "medium":
                    base = 0.3
                elif d["strength"] == "strong":
                    base = 0.4
                if d["confirmed"]:
                    base += 0.1
                bearish_score += base

        # Volumen extra (opcional): si el último volumen es mayor a la media,
        # damos un pequeño plus al lado de la divergencia predominante.
        vol = df["volume"]
        if len(vol) >= 10:
            vol_mean = vol.tail(10).mean()
            if vol.iloc[-1] > 1.3 * vol_mean:
                if bullish_score > bearish_score:
                    bullish_score += 0.05
                elif bearish_score > bullish_score:
                    bearish_score += 0.05

        if bullish_score == 0 and bearish_score == 0:
            overall = "neutral"
            confidence = 0.0
        elif bullish_score > bearish_score:
            overall = "bullish-reversal"
            confidence = min(1.0, bullish_score)
        elif bearish_score > bullish_score:
            overall = "bearish-reversal"
            confidence = min(1.0, bearish_score)
        else:
            overall = "neutral"
            confidence = min(1.0, bullish_score)

        result = {
            "divergences": {
                "rsi": rsi_div,
                "macd": macd_div,
            },
            "overall_bias": overall,
            "confidence": float(round(confidence, 3)),
        }
        return result

    except Exception as e:
        logger.error(f"❌ Error en detect_smart_divergences: {e}")
        return _empty_result()


def _empty_result():
    return {
        "divergences": {
            "rsi": {"type": "none", "confirmed": False, "strength": "weak"},
            "macd": {"type": "none", "confirmed": False, "strength": "weak"},
        },
        "overall_bias": "neutral",
        "confidence": 0.0,
    }
