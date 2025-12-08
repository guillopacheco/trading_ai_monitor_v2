import logging

from services.technical_engine.technical_engine import analyze as engine_analyze
from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot

logger = logging.getLogger("analysis_service")


class AnalysisService:
    """
    Capa empresarial de análisis técnico.
    Unifica acceso a:
    - analyze_symbol()
    - snapshots multi-TF
    - mensajes formateados para Telegram
    - integración con coordinadores
    """

    # ============================================================
    # 1) Análisis técnico estándar
    # ============================================================

    async def analyze_symbol(self, symbol: str, direction: str):
        """
        Realiza análisis completo igual que el motor original:
        - Obtiene snapshot MTF
        - Ejecuta motor técnico (smart bias, score, divergencias, etc.)
        - Devuelve un dict limpio
        """

        logger.info(f"📊 AnalysisService.analyze_symbol → {symbol} ({direction})")

        snapshot = await get_multi_tf_snapshot(symbol)
        if not snapshot:
            raise ValueError(f"No se pudo obtener snapshot multi-TF para {symbol}")

        result = engine_analyze(symbol, direction, snapshot)
        return {
            "symbol": symbol,
            "direction": direction,
            "snapshot": snapshot,
            "decision": result
        }

    # ============================================================
    # 2) Snapshot detallado (comando /detalles)
    # ============================================================

    async def build_detailed_snapshot(self, symbol: str):
        """
        Devuelve snapshot multi-TF detallado para /detalles
        """

        logger.info(f"📘 AnalysisService.build_detailed_snapshot → {symbol}")

        snapshot = await get_multi_tf_snapshot(symbol)
        if not snapshot:
            return f"❌ No hay datos suficientes para {symbol}."

        msg = f"📊 *Detalle técnico de {symbol}*\n\n"
        msg += f"• Tendencia mayor: {snapshot.get('major_trend_label')}\n"
        msg += f"• Smart Bias: {snapshot.get('smart_bias_code')}\n"
        msg += f"• Confianza: {snapshot.get('confidence', 0)*100:.1f}% (Grado {snapshot.get('grade')})\n\n"
        msg += "⏱ *Temporalidades:*\n"

        for tf in snapshot.get("timeframes", []):
            msg += f"• {tf['tf_label']}: {tf['trend_label']} | RSI {tf['rsi']:.1f} | MACD_hist {tf['macd_hist']:.5f}\n"

        return msg

    # ============================================================
    # 3) Mensajes formateados para posiciones abiertas
    # ============================================================

    def build_open_position_message(self, symbol, direction, analysis, loss_pct):
        d = analysis["decision"]
        s = analysis["snapshot"]

        msg = f"""
📊 *Evaluación de operación abierta — {symbol} ({direction})*

🔹 *Pérdida actual:* {loss_pct:.2f}%
🔹 *Tendencia mayor:* {s.get('major_trend_label')}
🔹 *Smart Bias:* {s.get('smart_bias_code')}
🔹 *Confianza:* {s.get('confidence',0)*100:.1f}% (grado {s.get('grade')})

🎯 *Decisión del motor:* {d.get('decision')}
• Motivo principal: {d.get('decision_reasons',[ 'N/A'])[0]}

⏱ *Temporalidades:*
"""        
        for tf in s.get("timeframes", []):
            msg += f"• {tf['tf_label']}: {tf['trend_label']}\n"

        return msg

    # ============================================================
    # 4) Mensaje para auto-loss-check
    # ============================================================

    def build_loss_warning_message(self, symbol, direction, loss_pct, analysis, level):
        d = analysis["decision"]

        return f"""
⚠️ *Advertencia — nivel -{level}% activado en {symbol}*

🔹 Dirección: {direction}
🔹 Pérdida actual: {loss_pct:.2f}%

📘 Motor técnico sugiere:
➡️ {d.get('decision')} (confianza {d.get('confidence',0)*100:.1f}%)

Motivo: {d.get('decision_reasons', ['N/A'])[0]}
"""

    # ============================================================
    # 5) Mensaje para comando /reversion
    # ============================================================

    def build_reversal_message(self, symbol, direction, analysis):
        d = analysis["decision"]

        return f"""
🔄 *Evaluación de reversión — {symbol} ({direction})*

Decisión del motor:
➡️ {d.get('decision')} (confianza {d.get('confidence',0)*100:.1f}%)

Motivo:
{d.get('decision_reasons',['N/A'])[0]}
"""

    # ============================================================
    # 6) Mensaje para auto-reversal
    # ============================================================

    def build_auto_reversal_decision(self, symbol, direction, analysis, loss_pct):
        d = analysis["decision"]

        return f"""
🚨 *Reversión automática — {symbol}*

🔹 Dirección actual: {direction}
🔹 Pérdida: {loss_pct:.2f}%

📘 Motor:
➡️ {d.get('decision')} (confianza {d.get('confidence',0)*100:.1f}%)

Motivo:
{d.get('decision_reasons',['N/A'])[0]}
"""


    # ============================================================
    # 7) Función de compatibilidad legacy
    # ============================================================

    async def manual_analysis(self, symbol: str, direction: str):
        """Alias para mantener compatibilidad con coordinadores."""
        return await self.analyze_symbol(symbol, direction)
