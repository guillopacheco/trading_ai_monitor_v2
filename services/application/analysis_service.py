# services/application/analysis_service.py

import logging

from services.technical_engine.technical_engine import analyze as engine_analyze
from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot

logger = logging.getLogger("analysis_service")


class AnalysisResult:
    """DTO limpio para transportar resultados del motor técnico."""
    def __init__(self, symbol, direction, snapshot, decision):
        self.symbol = symbol
        self.direction = direction
        self.snapshot = snapshot
        self.decision = decision


async def analyze_symbol(symbol: str, direction: str) -> AnalysisResult:
    """
    Ejecuta análisis técnico completo:
    - Carga snapshot multi-TF
    - Ejecuta motor técnico
    - Devuelve DTO limpio para Application Layer
    """

    logger.info(f"📊 Iniciando análisis para {symbol} ({direction}) ...")

    try:
        # 1) Snapshot multi-TF
        snapshot = await get_multi_tf_snapshot(symbol)

        if not snapshot:
            raise ValueError(f"No se pudo obtener snapshot multi-TF para {symbol}")

        # 2) Motor técnico (smart bias, match, score, divergencias, etc.)
        decision = engine_analyze(symbol, direction, snapshot)

        logger.info(f"📘 Motor técnico respondió para {symbol}: {decision}")

        return AnalysisResult(
            symbol=symbol,
            direction=direction,
            snapshot=snapshot,
            decision=decision
        )

    except Exception as e:
        logger.exception(f"❌ Error analizando {symbol}: {e}")
        raise


def format_analysis_for_telegram(result: AnalysisResult) -> str:
    """
    Convierte el resultado del motor a un mensaje limpio para Telegram.
    """

    s = result.snapshot
    d = result.decision

    tf_info = "\n".join(
        [f"• {tf['tf_label']}: {tf['trend_label']}" for tf in s.get("timeframes", [])]
    )

    return f"""📊 Análisis de {result.symbol} ({result.direction})
• Tendencia mayor: {s.get('major_trend_label')}
• Smart Bias: {s.get('smart_bias_code')}
• Confianza global: {s.get('confidence', 0)*100:.1f}% (Grado {s.get('grade')})
• Match técnico: {s.get('match_ratio')}% | Score: {s.get('technical_score')}

⏱ Temporalidades:
{tf_info}

🎯 Smart Entry
• Permitido: {"Sí" if d.get("allowed") else "No"} (modo: {d.get("entry_mode")}, grado {d.get("grade")})
• Score entrada: {d.get("technical_score")}
• Motivo principal: {d.get("decision_reasons", ["N/A"])[0]}

📌 Decisión final del motor
• Decisión: {d.get("decision")} ({d.get("confidence", 0)*100:.1f}% confianza)
• Motivo principal: {d.get("decision_reasons", ["N/A"])[0]}

ℹ️ Contexto analizado: {d.get("context")}
"""
