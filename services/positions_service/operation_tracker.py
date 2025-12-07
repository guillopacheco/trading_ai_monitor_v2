import logging
import asyncio
from typing import Any, Dict, Callable, Awaitable, Optional, List, Union

from services.bybit_service.bybit_client import get_open_positions
from core.helpers import (
    calculate_roi,
    calculate_loss_pct_from_roi,
    calculate_pnl,
)

logger = logging.getLogger("operation_tracker")


PositionDict = Dict[str, Any]
AsyncCallback = Callable[[PositionDict], Awaitable[None]]
SyncCallback = Callable[[PositionDict], None]
CallbackType = Union[AsyncCallback, SyncCallback]


class OperationTrackerAdapter:
    """
    Adaptador limpio para monitoreo de posiciones abiertas.

    Responsabilidades:
    - Consultar Bybit para obtener posiciones abiertas.
    - Normalizar y enriquecer cada posición (ROI, pérdida %, PnL, etc.).
    - Delegar la decisión a un callback externo (Application Layer / Motor Técnico).

    NO:
    - Decide si cerrar / mantener / revertir.
    - Envía mensajes a Telegram.
    - Llama directamente al motor técnico.
    """

    def __init__(
        self,
        fetch_positions_func: Callable[[], Any],
        process_position_callback: CallbackType,
        interval_seconds: int = 20,
    ) -> None:
        """
        :param fetch_positions_func: Función que devuelve lista de posiciones abiertas
                                     (normalmente services.bybit_service.bybit_client.get_open_positions).
        :param process_position_callback: Función/corutina que recibe un dict con la
                                          posición enriquecida y decide qué hacer.
        :param interval_seconds: Intervalo entre evaluaciones (segundos).
        """
        self._fetch_positions_func = fetch_positions_func
        self._process_position_callback = process_position_callback
        self._interval_seconds = interval_seconds

    async def _call_callback(self, position: PositionDict) -> None:
        """Llama al callback, soportando tanto funciones sync como async."""
        try:
            result = self._process_position_callback(position)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            symbol = position.get("symbol", "UNKNOWN")
            logger.error(f"❌ Error en callback de posición {symbol}: {e}", exc_info=True)

    @staticmethod
    def _normalize_side(raw_side: str) -> str:
        """
        Normaliza el side a 'long' / 'short'.
        Bybit suele usar 'Buy' / 'Sell'.
        """
        if not raw_side:
            return "unknown"
        s = raw_side.lower()
        if "buy" in s or s == "long":
            return "long"
        if "sell" in s or s == "short":
            return "short"
        return raw_side.lower()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _enrich_position(self, raw: Dict[str, Any]) -> PositionDict:
        """
        Toma el dict crudo devuelto por Bybit y genera un dict “limpio”
        con campos estándar para el motor / capa de aplicación.
        """
        symbol = raw.get("symbol") or raw.get("symbolName") or "UNKNOWN"

        side_raw = raw.get("side", "")
        side = self._normalize_side(side_raw)

        # Tamaño / cantidad
        size = self._safe_float(raw.get("size") or raw.get("qty") or raw.get("positionSize"))

        # Precios
        entry_price = self._safe_float(
            raw.get("entryPrice")
            or raw.get("avgPrice")
            or raw.get("avgEntryPrice")
        )
        mark_price = self._safe_float(
            raw.get("markPrice")
            or raw.get("lastPrice")
            or raw.get("marketPrice")
        )

        # PnL y ROI usando helpers estándar
        pnl = calculate_pnl(entry_price, mark_price, size, side)
        roi = calculate_roi(entry_price, mark_price, side)
        loss_pct = calculate_loss_pct_from_roi(roi)

        return {
            "symbol": symbol,
            "side": side,                       # 'long' / 'short'
            "size": size,
            "entry_price": entry_price,
            "mark_price": mark_price,
            "pnl": pnl,
            "roi": roi,
            "loss_pct": loss_pct,
            "raw": raw,                        # posición original completa
        }

    async def run_once(self) -> None:
        """
        Ejecuta una pasada:
        - Obtiene posiciones abiertas.
        - Enriquecer cada posición.
        - Llama al callback externo por cada posición.
        """
        logger.info("📡 Iniciando evaluación de posiciones abiertas…")

        try:
            positions: List[Dict[str, Any]] = get_open_positions()

        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones desde Bybit: {e}", exc_info=True)
            return

        if not positions:
            logger.info("📭 No hay posiciones abiertas.")
            return

        logger.info(f"🔍 {len(positions)} posiciones abiertas detectadas.")

        for raw_pos in positions:
            try:
                position = self._enrich_position(raw_pos)
                symbol = position.get("symbol", "UNKNOWN")
                side = position.get("side", "unknown")
                roi = position.get("roi", 0.0)
                loss_pct = position.get("loss_pct", 0.0)

                logger.info(
                    f"🔎 {symbol} | {side.upper()} | ROI={roi:.2f}% | loss={loss_pct:.2f}% | "
                    f"Entry={position.get('entry_price')} Mark={position.get('mark_price')}"
                )

                await self._call_callback(position)

            except Exception as e:
                logger.error(f"❌ Error evaluando posición {raw_pos}: {e}", exc_info=True)

    async def run_forever(self) -> None:
        """
        Bucle principal: ejecuta run_once() cada N segundos.
        """
        logger.info("🔄 OperationTrackerAdapter.run_forever() iniciado.")
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"❌ Error en ciclo de OperationTrackerAdapter: {e}", exc_info=True)
            await asyncio.sleep(self._interval_seconds)


# ============================================================
# 🔗 Punto de entrada LITE (compatibilidad con main.py actual)
# ============================================================

async def start_operation_tracker() -> None:
    """
    Punto de entrada actual usado por main.py (Fase 1.2).

    🔹 Hace de “pegamento” temporal:
       - Usa OperationTrackerAdapter.
       - Callback interno SOLO registra las posiciones (no decide aún).
    🔹 En Fase 2, aquí conectaremos con el Application Layer real
       que decidirá mantener / cerrar / revertir usando el motor técnico.
    """

    async def _log_only_callback(position: PositionDict) -> None:
        """
        Callback LITE:
        - No toma decisiones.
        - Solo deja trazas claras para que podamos conectar luego el motor.
        """
        symbol = position.get("symbol", "UNKNOWN")
        side = position.get("side", "unknown")
        roi = position.get("roi", 0.0)
        loss_pct = position.get("loss_pct", 0.0)

        logger.info(
            f"🧩 [LITE] Posición procesada en callback: {symbol} "
            f"| {side.upper()} | ROI={roi:.2f}% | loss={loss_pct:.2f}%"
        )

    adapter = OperationTrackerAdapter(
        fetch_positions_func=get_open_positions,
        process_position_callback=_log_only_callback,
        interval_seconds=20,   # ⏱ igual que antes
    )

    logger.info("🔄 Iniciando start_operation_tracker() (modo LITE / adaptador limpio)…")
    await adapter.run_forever()
