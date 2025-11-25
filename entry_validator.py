import logging

logger = logging.getLogger("entry_validator")

from indicators import (
    get_multi_tf_trend,
    get_rsi,
    get_macd,
    detect_divergence_rsi,
    detect_divergence_macd,
    get_bollinger,
    get_stoch,
)

from bybit_client import get_ohlcv_data


# ================================================================
#   MÓDULO DE ENTRADA INTELIGENTE v1.0
# ================================================================

class EntryDecision:
    OK = "ENTRY_OK"
    CAUTION = "ENTRY_RISKY"
    BLOCK = "ENTRY_BLOCKED"


def evaluate_entry(symbol: str, direction: str, entry_price: float):
    """
    Analiza si la entrada es adecuada según:
    - divergencias
    - momentum
    - volatilidad
    - estructura 15m y 1h
    - agotamiento (extension EMA-BB)
    """
    logger.info(f"🧠 Evaluando entrada inteligente para {symbol} ({direction})...")

    # --------------------------------------------------------------
    # 📌 1. Obtener datos multi-temporalidad
    # --------------------------------------------------------------
    try:
        df15 = get_ohlcv_data(symbol, "15")
        df1h = get_ohlcv_data(symbol, "60")

        if df15 is None or df15.empty:
            return EntryDecision.CAUTION

    except Exception as e:
        logger.error(f"❌ Error obteniendo datos para entrada inteligente: {e}")
        return EntryDecision.CAUTION

    # --------------------------------------------------------------
    # 📌 2. Detectar divergencias (contra la señal = bloqueo)
    # --------------------------------------------------------------
    try:
        rsi_div_15 = detect_divergence_rsi(df15)
        macd_div_15 = detect_divergence_macd(df15)

        rsi_div_1h = detect_divergence_rsi(df1h)
        macd_div_1h = detect_divergence_macd(df1h)

        # SHORT → divergencia alcista es peligrosísima
        if direction == "SHORT":
            if rsi_div_15 == "bullish" or rsi_div_1h == "bullish":
                logger.info("❌ Divergencia RSI alcista en contra → Bloqueo entrada SHORT")
                return EntryDecision.BLOCK

            if macd_div_15 == "bullish" or macd_div_1h == "bullish":
                logger.info("❌ Divergencia MACD alcista en contra → Bloqueo entrada SHORT")
                return EntryDecision.BLOCK

        # LONG → divergencia bajista invalida la entrada
        if direction == "LONG":
            if rsi_div_15 == "bearish" or rsi_div_1h == "bearish":
                logger.info("❌ Divergencia RSI bajista en contra → Bloqueo entrada LONG")
                return EntryDecision.BLOCK

            if macd_div_15 == "bearish" or macd_div_1h == "bearish":
                logger.info("❌ Divergencia MACD bajista en contra → Bloqueo entrada LONG")
                return EntryDecision.BLOCK

    except:
        pass

    # --------------------------------------------------------------
    # 📌 3. Momentum MACD (fuerza real)
    # --------------------------------------------------------------
    try:
        macd15 = get_macd(df15)
        last_hist = macd15["hist"].iloc[-1]
        prev_hist = macd15["hist"].iloc[-3]

        momentum_direction = "up" if last_hist > prev_hist else "down"

        if direction == "LONG" and momentum_direction == "down":
            logger.info("⚠️ Momentum débil para LONG → Entrada arriesgada")
            return EntryDecision.CAUTION

        if direction == "SHORT" and momentum_direction == "up":
            logger.info("⚠️ Momentum débil para SHORT → Entrada arriesgada")
            return EntryDecision.CAUTION

    except:
        pass

    # --------------------------------------------------------------
    # 📌 4. Agotamiento (Bollinger + EMAs)
    # --------------------------------------------------------------
    try:
        upper, middle, lower = get_bollinger(df15)
        last_close = df15["close"].iloc[-1]

        # LONG comprado en banda superior → exceso = peligro
        if direction == "LONG" and last_close > upper:
            logger.info("❌ Señal LONG en extensión (Bollinger) → Bloqueo entrada")
            return EntryDecision.BLOCK

        # SHORT en banda inferior → riesgo extremo
        if direction == "SHORT" and last_close < lower:
            logger.info("❌ Señal SHORT en extensión (Bollinger) → Bloqueo entrada")
            return EntryDecision.BLOCK

    except:
        pass

    # --------------------------------------------------------------
    # 📌 5. Stochastic: cambios de dirección inmediatos
    # --------------------------------------------------------------
    try:
        stoch = get_stoch(df15)
        k = stoch["k"].iloc[-1]
        d = stoch["d"].iloc[-1]

        # LONG pero stoch cruza hacia abajo desde sobrecompra
        if direction == "LONG" and k < d and k > 80:
            logger.info("❌ STC cruzando abajo → Rechazo entrada LONG")
            return EntryDecision.BLOCK

        # SHORT pero stoch cruza hacia arriba desde sobreventa
        if direction == "SHORT" and k > d and k < 20:
            logger.info("❌ STC cruzando arriba → Rechazo entrada SHORT")
            return EntryDecision.BLOCK

    except:
        pass

    # --------------------------------------------------------------
    # 📌 6. Si pasa todos los filtros → Entrada válida
    # --------------------------------------------------------------
    logger.info("✅ Entrada inteligente aprobada.")
    return EntryDecision.OK
