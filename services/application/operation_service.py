import logging
from typing import Optional

from services.bybit_service.bybit_client import (
    get_open_positions,
    close_position,
    reverse_position,
)

from database import save_position_action
from services.telegram_service.notifier import Notifier

logger = logging.getLogger("operation_service")


class OperationService:
    """
    Gestiona operaciones abiertas, cierres, reversión y registro.
    """

    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    # -----------------------------------------------------------
    # Obtener posiciones abiertas
    # -----------------------------------------------------------
    async def get_positions(self, symbol: Optional[str] = None) -> list:
        try:
            positions = await get_open_positions(symbol)
            return positions or []
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones: {e}")
            return []

    # -----------------------------------------------------------
    # Cerrar posición
    # -----------------------------------------------------------
    async def close(self, symbol: str) -> bool:
        try:
            ok = await close_position(symbol)

            if ok:
                save_position_action(symbol, "close", "closed_by_user")
                await self.notifier.send_operation_closed(symbol)

            return ok

        except Exception as e:
            logger.error(f"❌ Error al cerrar posición {symbol}: {e}")
            return False

    # -----------------------------------------------------------
    # Revertir posición
    # -----------------------------------------------------------
    async def reverse(self, symbol: str) -> bool:
        try:
            ok = await reverse_position(symbol)

            if ok:
                save_position_action(symbol, "reverse", "reversed")
                await self.notifier.send_operation_reversed(symbol)

            return ok

        except Exception as e:
            logger.error(f"❌ Error al revertir posición {symbol}: {e}")
            return False
