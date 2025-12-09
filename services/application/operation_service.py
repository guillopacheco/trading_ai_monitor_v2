import logging
from database import save_operation_event
from services.telegram_service.notifier import Notifier
from services.bybit.bybit_private import (
    get_open_positions,
    close_position,
    reverse_position,
)

logger = logging.getLogger("operation_service")


class OperationService:
    """
    Maneja operaciones abiertas, cierres, reversión y registro de eventos.
    """

    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    # ============================================================
    # 🔍 OBTENER OPERACIONES ABIERTAS
    # ============================================================
    async def get_positions(self):
        positions = await get_open_positions()
        return positions or []

    # ============================================================
    # ❌ CERRAR OPERACIÓN
    # ============================================================
    async def close(self, symbol: str, reason: str = "manual"):
        ok = await close_position(symbol)

        if ok:
            save_operation_event(symbol, "close", reason)
            await self.notifier.send(f"🛑 Operación cerrada en {symbol} — Motivo: {reason}")
        else:
            await self.notifier.send(f"⚠️ No se pudo cerrar {symbol}")

        return ok

    # ============================================================
    # 🔁 REVERTIR OPERACIÓN
    # ============================================================
    async def reverse(self, symbol: str, reason: str = "manual"):
        ok = await reverse_position(symbol)

        if ok:
            save_operation_event(symbol, "reverse", reason)
            await self.notifier.send(
                f"🔄 Se revirtió posición en {symbol} — ahora va en la dirección opuesta."
            )
        else:
            await self.notifier.send(f"⚠️ No se pudo revertir {symbol}")

        return ok

    # ============================================================
    # 📉 EVALUAR PÉRDIDAS CRÍTICAS
    # ============================================================
    async def evaluate_losses(self, symbol: str, loss_pct: float):
        """
        Lógica base para decisiones por pérdidas (-30%, -50%, -70%, etc.)
        """

        if loss_pct <= -70:
            await self.reverse(symbol, "loss_70")
            return "reverse"

        if loss_pct <= -50:
            await self.close(symbol, "loss_50")
            return "close"

        if loss_pct <= -30:
            return "warning"

        return "hold"
