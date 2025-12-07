"""
application_layer.py
Capa intermedia entre Telegram/Bybit y el motor técnico.

OBJETIVO:
- Normalizar datos
- Llamar al motor técnico de forma unificada
- Traducir decisiones del motor a acciones del sistema
- Evitar que Telegram/Bybit dependan del motor
"""

import logging

from services.technical_engine.technical_engine import analyze_market


logger = logging.getLogger("application")


# ============================================================================
# 🟦 1) Análisis manual (usado por /analizar)
# ============================================================================
async def manual_analysis(symbol: str, direction: str = "auto") -> str:
    """
    Envuelve el motor técnico y devuelve un mensaje amigable para Telegram.
    """
    try:
        result = await analyze_market(symbol, direction)

        # formateo limpio para Telegram
        msg = (
            f"📊 *Análisis de {symbol} ({direction})*\n"
            f"• Tendencia mayor: {result['major_trend_label']}\n"
            f"• Smart Bias: {result['smart_bias_code']}\n"
            f"• Confianza: {result['confidence']*100:.1f}% (Grado {result['grade']})\n\n"
            f"📌 *Recomendación:* {result['decision']} "
            f"({result['confidence']*100:.1f}% confianza)\n"
            f"➡️ Acción sugerida: {result['decision']}\n"
            f"📝 Motivo principal: {result['decision_reasons'][0]}\n\n"
            f"ℹ️ Contexto analizado: entry"
        )
        return msg

    except Exception as e:
        logger.exception("Error en manual_analysis")
        return f"❌ Error analizando {symbol}: {e}"


# ============================================================================
# 🟦 2) Evaluación para “reactivación de señales”
# ============================================================================
async def evaluate_signal_reactivation(signal):
    """
    Parámetros esperados desde telegram_reader:
    - symbol
    - direction (long/short)
    - entry_price
    - timestamp

    La capa de Telegram NO analiza, solo entrega datos crudos aquí.
    """

    logger.info(f"♻️ Evaluando reactivación: {signal['symbol']} {signal['direction']}")

    # llamamos al motor
    result = await analyze_market(signal["symbol"], signal["direction"])

    decision = result["decision"]

    # El motor decide y nosotros traducimos a acción del sistema:
    if decision in ["enter", "ok", "safe"]:
        action = "REACTIVATE"
    elif decision in ["skip", "block"]:
        action = "IGNORE"
    else:
        action = "UNKNOWN"

    return {
        "symbol": signal["symbol"],
        "direction": signal["direction"],
        "decision": decision,
        "action": action,
        "engine_output": result,
    }


# ============================================================================
# 🟦 3) Evaluación de operaciones abiertas
# ============================================================================
async def evaluate_open_position(position):
    """
    Parámetros esperados (desde Bybit):
    - symbol
    - side (Buy/Sell)
    - entry_price
    - mark_price
    - roi_pct
    """

    logger.info(f"📡 Analizando posición abierta: {position['symbol']} | ROI={position['roi_pct']}%")

    # Convertimos side de bybit a dirección
    direction = "long" if position["side"].lower() == "buy" else "short"

    result = await analyze_market(position["symbol"], direction)

    # lógica universal
    if result["decision"] in ["skip", "block"]:
        return {
            "action": "hold",
            "reason": "Condiciones no favorables para cerrar ni revertir",
            "engine": result
        }

    if result["decision"] == "exit":
        return {
            "action": "exit",
            "reason": "Motor detecta riesgo o reversión",
            "engine": result
        }

    if result["decision"] == "reverse":
        return {
            "action": "reverse",
            "reason": "Tendencia mayor en contra, reversión fuerte",
            "engine": result
        }

    return {
        "action": "hold",
        "reason": "Neutral",
        "engine": result
    }


# ============================================================================
# 🟦 4) Evaluación en caso de STOP LOSS crítico (-50%)
# ============================================================================
async def evaluate_stoploss_reversal(position):
    """
    Casos de pérdida extrema.
    """

    logger.warning(f"⚠️ Evaluación crítica (-50%) para {position['symbol']}")

    direction = "long" if position["side"].lower() == "buy" else "short"

    result = await analyze_market(position["symbol"], direction)

    if result["decision"] == "reverse":
        return {
            "action": "reverse",
            "reason": "Reversión detectada — mejor invertir la posición",
            "engine": result
        }

    if result["decision"] in ["exit", "block"]:
        return {
            "action": "exit",
            "reason": "Condiciones malas → cerrar para limitar pérdidas",
            "engine": result
        }

    return {
        "action": "hold",
        "reason": "Motor considera que puede recuperarse",
        "engine": result
    }
