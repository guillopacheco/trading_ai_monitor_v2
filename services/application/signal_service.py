import logging
from datetime import datetime

from database import (
    db_insert_signal,
    db_get_pending_signals,
    db_update_signal_status,
)

from services.application.analysis_service import analyze_symbol, format_analysis_for_telegram

logger = logging.getLogger("signal_service")


class SignalService:
    """
    Servicio de gestión de señales:
    - guardar en DB
    - analizar
    - obtener pendientes
    - actualizar estado
    """

    # -------------------------------
    #       ENTRADA DE SEÑALES
    # -------------------------------
    def process_incoming_signal(self, symbol: str, direction: str):
        """
        Guarda la señal en la base de datos.
        """
        logger.info(f"📥 Guardando señal entrante: {symbol} ({direction})")

        db_insert_signal(
            symbol=symbol,
            direction=direction,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )

        logger.info("💾 Señal guardada en DB correctamente.")

    # -------------------------------
    #   OBTENER PENDIENTES
    # -------------------------------
    def get_pending_signals(self):
        """
        Devuelve señales pendientes desde la DB.
        """
        return db_get_pending_signals()

    # -------------------------------
    #        ACTUALIZAR ESTADO
    # -------------------------------
    def update_status(self, signal_id: int, new_status: str):
        db_update_signal_status(signal_id, new_status)
        logger.info(f"🔄 Señal {signal_id} actualizada → {new_status}")

    # -------------------------------
    #   ANALIZAR UNA SEÑAL MANUAL
    # -------------------------------
    async def analyze_signal(self, symbol: str, direction: str):
        """
        Análisis técnico del símbolo.
        """
        result = await analyze_symbol(symbol, direction)
        return format_analysis_for_telegram(result)
