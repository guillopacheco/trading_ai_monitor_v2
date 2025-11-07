"""
indicators.py
Cálculo de indicadores y armado de datasets por timeframe para análisis intradía.
Optimizado para 1m/5m/15m con fallback automático si falta 1m.

Requiere una función de OHLCV:
- Preferido: bybit_client.get_ohlcv(symbol: str, timeframe: str, limit: int) -> pd.DataFrame
  con columnas: ["timestamp","open","high","low","close","volume"] (timestamp en ms o s).

Devuelve un dict por timeframe listo para trend_analysis y divergence_detector.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("indicators")

# ------------------------------------------------------------------
# 🔌 Entrada de datos: intenta usar bybit_client.get_ohlcv si existe
# ------------------------------------------------------------------
try:
    from bybit_client import get_ohlcv as _get_ohlcv  # tipo esperado
except Exception:  # pragma: no cover
    _get_ohlcv = None


# ================================================================
# 📊 Parámetros técnicos por defecto
# ================================================================
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_PERIOD = 14
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2.0


# ================================================================
# 🧮 Indicadores base
# ================================================================
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(method="bfill").fillna(50)

def macd(series: pd.Series, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def bbands(series: pd.Series, period: int = BB_PERIOD, stdev: float = BB_STD):
    ma = series.rolling(period).mean()
    sd = series.rolling(period).std()
    upper = ma + stdev * sd
    lower = ma - stdev * sd
    width = (upper - lower) / ma.replace(0, np.nan)
    return upper, ma, lower, width


# ================================================================
# 🔎 Carga OHLCV
# ================================================================
def _fetch_ohlcv(symbol: str, timeframe: str, limit: int = 300) -> Optional[pd.DataFrame]:
    """
    Wrapper para obtener OHLCV. Debe devolver DataFrame con:
    ['timestamp','open','high','low','close','volume']
    """
    if _get_ohlcv is None:
        logger.error("No se encontró bybit_client.get_ohlcv(). Agrega esta función en bybit_client.py")
        return None

    try:
        df = _get_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if df is None or df.empty:
            logger.warning(f"OHLCV vacío: {symbol} {timeframe}")
            return None

        # Normaliza columnas
        cols = {c.lower(): c for c in df.columns}
        need = ["timestamp", "open", "high", "low", "close", "volume"]
        for n in need:
            if n not in [c.lower() for c in df.columns]:
                raise ValueError(f"Falta columna '{n}' en OHLCV {timeframe}")

        # Asegurar nombres en minúscula
        df = df.rename(columns={c: c.lower() for c in df.columns})
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        df = df.dropna().reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error cargando OHLCV {symbol} {timeframe}: {e}")
        return None


# ================================================================
# 🧱 Armado de dataset por timeframe
# ================================================================
def _build_tf_block(df: pd.DataFrame) -> Optional[Dict]:
    if df is None or df.empty or len(df) < max(EMA_LONG_PERIOD, BB_PERIOD, ATR_PERIOD) + 5:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]

    ema_s = ema(close, EMA_SHORT_PERIOD)
    ema_l = ema(close, EMA_LONG_PERIOD)
    rsi_s = rsi(close, 14)
    macd_line, macd_signal, macd_hist = macd(close)
    atr_s = atr(df, ATR_PERIOD)
    bb_u, bb_m, bb_l, bb_w = bbands(close, BB_PERIOD, BB_STD)

    # valores actuales (último)
    block = {
        # series para divergencias:
        "price": close.tolist(),
        "rsi_series": rsi_s.tolist(),
        "macd_line_series": macd_line.tolist(),
        "volume": vol.tolist(),

        # últimos valores (para scoring rápido):
        "ema_short_value": float(ema_s.iloc[-1]),
        "ema_long_value": float(ema_l.iloc[-1]),
        "rsi_value": float(rsi_s.iloc[-1]),
        "macd_line_value": float(macd_line.iloc[-1]),
        "macd_signal_value": float(macd_signal.iloc[-1]),
        "macd_hist_value": float(macd_hist.iloc[-1]),

        # métricas de volatilidad relativas
        "atr_rel": float((atr_s.iloc[-1] / close.iloc[-1]) if close.iloc[-1] else 0.0),
        "bb_width": float(bb_w.iloc[-1]) if not np.isnan(bb_w.iloc[-1]) else 0.0,
    }
    return block


def select_timeframes_available(symbol: str,
                                base_tfs: List[str] = ["1m", "5m", "15m"],
                                fallback_tfs: List[str] = ["5m", "15m", "30m"]) -> List[str]:
    """
    Verifica si 1m tiene suficientes datos; si no, usa fallback (5m/15m/30m).
    """
    test_1m = _fetch_ohlcv(symbol, base_tfs[0], limit=220)
    if test_1m is not None and len(test_1m) >= 120:
        return base_tfs
    logger.info(f"Usando fallback de timeframes para {symbol}: {fallback_tfs}")
    return fallback_tfs


def get_indicators(symbol: str,
                   timeframes: Optional[List[str]] = None,
                   limit: int = 300) -> Dict[str, Dict]:
    """
    Carga OHLCV y construye indicadores por timeframe.
    Devuelve dict: { '1m': {price:[], rsi_series:[], macd_line_series:[], volume:[],
                            ema_short_value:..., ema_long_value:..., rsi_value:...,
                            macd_*_value:..., atr_rel:..., bb_width:...}, ... }
    """
    if timeframes is None:
        timeframes = select_timeframes_available(symbol)

    out: Dict[str, Dict] = {}
    for tf in timeframes:
        df = _fetch_ohlcv(symbol, tf, limit=limit)
        block = _build_tf_block(df) if df is not None else None
        if block:
            out[tf] = block
        else:
            logger.warning(f"Datos insuficientes en {symbol} {tf}")

    return out
