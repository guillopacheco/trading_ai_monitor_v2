import logging
import time

logger = logging.getLogger("operation_tracker")


class OperationTracker:
    """
    Tracker local para almacenar el estado de las operaciones abiertas.

    Funciones:
      - guardar estado actual
      - detectar cambios relevantes (ej: DD, reversión)
      - recuperar información para PositionMonitor

    (La conexión con Bybit REAL se implementará en Fase C)
    """

    def __init__(self):
        # Diccionario: {symbol: {entry, pnl, timestamp, extra...}}
        self.positions = {}

    # ----------------------------------------------------------------------
    # REGISTRO / ACTUALIZACIÓN
    # ----------------------------------------------------------------------
    def update_position(self, symbol: str, data: dict):
        """
        Guarda o actualiza una posición abierta.

        data puede contener:
            - entry_price
            - pnl_pct
            - size
            - direction
            - etc.
        """
        data["timestamp"] = time.time()
        self.positions[symbol] = data
        logger.info(f"📌 PositionTracker: posición actualizada para {symbol}: {data}")

    # ----------------------------------------------------------------------
    # CONSULTA
    # ----------------------------------------------------------------------
    def get_position(self, symbol: str):
        return self.positions.get(symbol)

    def get_all_positions(self):
        return self.positions

    # ----------------------------------------------------------------------
    # ELIMINAR
    # ----------------------------------------------------------------------
    def remove_position(self, symbol: str):
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"🗑 PositionTracker: posición eliminada para {symbol}")
