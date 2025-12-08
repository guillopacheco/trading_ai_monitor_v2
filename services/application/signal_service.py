import logging
from database import Database
from services.application.analysis_service import AnalysisService

logger = logging.getLogger("signal_service")


class SignalService:
    """
    Servicio empresarial para el manejo de señales:
    - guardar señal en DB
    - obtener señal
    - analizar señal
    - formatear respuesta técnica
    """

    def __init__(self):
        self.db = Database()
        self.analysis = AnalysisService()

    # ============================================================
    # DB I/O
    # ============================================================

    def save_signal(self, symbol: str, direction: str):
        self.db.save_signal(symbol, direction)

    def load_signal(self, symbol: str):
        return self.db.get_signal(symbol)

    # ============================================================
    # Análisis principal de señal
    # ============================================================

    async def analyze_signal(self, symbol: str, direction: str):
        """
        Realiza análisis técnico completo usando AnalysisService.
        """
        result = await self.analysis.analyze_symbol(symbol, direction)
        return result

    # ============================================================
    # Mensajes formateados
    # ============================================================

    async def format_signal_analysis(self, symbol: str, direction: str) -> str:
        res = await self.analyze_signal(symbol, direction)
        d = res["decision"]
        s = res["snapshot"]

        msg = f"""
📊 *Análisis de {symbol} ({direction})*

🔹 Tendencia mayor: {s.get('major_trend_label')}
🔹 Smart Bias: {s.get('smart_bias_code')}
🔹 Confianza: {s.get('confidence',0)*100:.1f}% (Grado {s.get('grade')})
🔹 Match técnico: {d.get('match_ratio',0):.1f}% | Score: {d.get('technical_score',0):.1f}

🎯 *Smart Entry*
🔹 Permitido: {'Sí' if d.get('allowed') else 'No'}
🔹 Modo: {d.get('decision')}
🔹 Motivo principal: {d.get('decision_reasons',['N/A'])[0]}

📘 *Decisión final del motor:*
➡️ {d.get('decision')} ({d.get('confidence',0)*100:.1f}% confianza)
"""

        return msg.strip()
