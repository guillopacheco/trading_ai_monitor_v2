import asyncio
import logging
import time

from motor_wrapper import analyze_for_signal
from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    mark_signal_not_reactivated,
    save_analysis_log,
)

logger = logging.getLogger("signal_reactivation_sync")


# =====================================================================
# 🧠 SISTEMA AVANZADO DE VALIDACIÓN DE REACTIVACIÓN
# =====================================================================
class SmartReactivationValidator:
    """
    Sistema avanzado que determina si una señal debe reactivarse.
    Incluye análisis de momentum, divergencias, agotamiento,
    volatilidad, microestructura y elasticidad de Bollinger.
    """

    @staticmethod
    def evaluate(symbol: str, result: dict, direction: str):
        """
        Retorna: (ok: bool, reason: str)
        """

        # Extraer data del motor técnico
        rsi = result.get("rsi")
        macd = result.get("macd")
        stok = result.get("stochastic")
        divergences = result.get("divergences", {})
        boll = result.get("bollinger", {})
        ema_fast = result.get("ema_fast")
        ema_slow = result.get("ema_slow")
        last_candle = result.get("last_candle")
        atr = result.get("atr")
        smart_bias = result.get("smart_bias")
        major_trend = result.get("major_trend")
        match_ratio = result.get("match_ratio", 0)

        # ================================================================
        # 1. MOMENTUM POST-TP
        # ================================================================
        if direction == "short":
            if rsi and rsi > 50:
                return False, "RSI cruzó 50 (momentum bajista agotado)"
            if macd and macd.get("hist", 0) > 0:
                return False, "MACD alcista (momentum contrario)"
        else:
            if rsi and rsi < 50:
                return False, "RSI debajo de 50 (momentum alcista débil)"
            if macd and macd.get("hist", 0) < 0:
                return False, "MACD bajista (momentum contrario)"

        # ================================================================
        # 2. AGOTAMIENTO / DIVERGENCIAS
        # ================================================================
        if direction == "short":
            if divergences.get("rsi") == "bullish" or divergences.get("macd") == "bullish":
                return False, "Divergencia alcista fuerte detectada"
        else:
            if divergences.get("rsi") == "bearish" or divergences.get("macd") == "bearish":
                return False, "Divergencia bajista fuerte detectada"

        # ================================================================
        # 3. ESTRUCTURA: EMA20 / EMA50
        # ================================================================
        if ema_fast is not None and ema_slow is not None:
            if direction == "short" and ema_fast > ema_slow:
                return False, "EMA rápida por encima de EMA lenta (riesgo de reversión)"
            if direction == "long" and ema_fast < ema_slow:
                return False, "EMA rápida debajo de EMA lenta (tendencia no cambia)"

        # ================================================================
        # 4. VOLATILIDAD Y MANIPULACIÓN
        # ================================================================
        if atr and last_candle:
            if last_candle.get("body", 0) > atr * 2.5:
                return False, "Vela extrema detectada (manipulación probable)"

        # ================================================================
        # 5. MICROESTRUCTURA: VELAS RECIENTES
        # ================================================================
        if last_candle and last_candle.get("type") in ["doji", "indecision"]:
            return False, "Vela de indecisión reciente"

        if last_candle and last_candle.get("rejection", False):
            return False, "Rechazo fuerte encontrado en la última vela"

        # ================================================================
        # 6. ELASTICIDAD DE BOLLINGER
        # ================================================================
        if boll:
            if direction == "short" and boll.get("squeeze", False):
                return False, "Squeeze activo (rebote posible)"

            if direction == "long" and boll.get("expansion", False):
                return False, "Expansión brusca (riesgo de caída)"

        # ================================================================
        # SI SUPERA TODOS LOS FILTROS
        # ================================================================
        return True, "Condiciones técnicas favorables para reactivar"


# =====================================================================
# LÓGICA PARA DECIDIR SI UNA SEÑAL PUEDE REACTIVARSE
# =====================================================================
def _can_reactivate(result: dict, direction: str):
    """
    Analiza si una señal debe reactivarse.
    """

    if not result:
        return False, "Motor técnico devolvió resultado vacío"

    match_ratio = result.get("match_ratio", 0)
    if match_ratio < 40:
        return False, f"Match ratio insuficiente ({match_ratio}%)"

    # Nueva capa avanzada
    ok, reason = SmartReactivationValidator.evaluate(
        result.get("symbol", "UNKNOWN"),
        result,
        direction
    )
    return ok, reason


# =====================================================================
# CICLO DE REACTIVACIÓN
# =====================================================================
async def run_reactivation_cycle():
    """
    Revisa señales pendientes y decide si reactivarlas o descartarlas.
    """

    logger.info("♻️ Ejecutando ciclo de reactivación…")

    pending = get_pending_signals_for_reactivation()
    if not pending:
        logger.info("♻️ No hay señales pendientes.")
        return

    logger.info(f"♻️ {len(pending)} señales pendientes encontradas.")

    for sig in pending:
        try:
            symbol = sig["symbol"]
            side = sig["side"]
            signal_id = sig["id"]

            logger.info(f"♻️ Revisando señal pendiente: {symbol} ({side}).")

            # Dirección normalizada
            direction = "long" if side.lower() == "buy" else "short"

            # Analizar mercado nuevamente
            result = analyze_for_signal(symbol, direction, validate=True)

            if not result:
                logger.warning(f"❌ Motor no devolvió resultado para {symbol}.")
                mark_signal_not_reactivated(signal_id, reason="motor_failed")
                continue

            # Decisión inteligente
            ok, reason = _can_reactivate(result, direction)

            if not ok:
                logger.info(f"⏳ Señal {symbol} NO reactivada: {reason}")

                mark_signal_not_reactivated(
                    signal_id,
                    reason=reason,
                    extra={
                        "match_ratio": result.get("match_ratio"),
                        "major_trend": result.get("major_trend"),
                        "overall_trend": result.get("overall_trend"),
                        "smart_bias": result.get("smart_bias"),
                        "divergences": result.get("divergences"),
                    }
                )
                continue

            # Si es válida → reactivar
            mark_signal_reactivated(signal_id)

            # Log del análisis técnico
            save_analysis_log(
                signal_id,
                result.get("match_ratio"),
                "reactivated",
                f"Reactivación aprobada ({reason})"
            )

            logger.info(f"♻️ Señal reactivada: {symbol}")

        except Exception as e:
            logger.error(f"❌ Error evaluando señal {sig}: {e}")

    logger.info("♻️ Revisión completada.")
    logger.info("🕒 Próxima revisión en 15 minutos.")


# =====================================================================
# LOOP PRINCIPAL
# =====================================================================
async def start_reactivation_monitor():
    logger.info("♻️  Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")

        await asyncio.sleep(15 * 60)  # 15 minutos
