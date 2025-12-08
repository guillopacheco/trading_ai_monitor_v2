"""
operation_tracker.py — FIX ROI + leverage (2025-12-07)
"""

import logging
import asyncio
from typing import Any, Dict, Callable, Awaitable, List, Union

from services.bybit_service.bybit_client import get_open_positions
from helpers import (
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

    def __init__(self, fetch_positions_func, process_position_callback, interval_seconds: int = 20):
        self._fetch_positions_func = fetch_positions_func
        self._process_position_callback = process_position_callback
        self._interval_seconds = interval_seconds

    # ------------------------------------------------------
    @staticmethod
    def _normalize_side(raw_side: str) -> str:
        if not raw_side:
            return "unknown"
        s = raw_side.lower()
        if "buy" in s or s == "long":
            return "long"
        if "sell" in s or s == "short":
            return "short"
        return raw_side.lower()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0):
        try:
            return float(value)
        except Exception:
            return default

    # ------------------------------------------------------
    def _enrich_position(self, raw: Dict[str, Any]) -> PositionDict:
        symbol = raw.get("symbol") or raw.get("symbolName") or "UNKNOWN"

        side_raw = raw.get("side", "")
        side = self._normalize_side(side_raw)

        size = self._safe_float(raw.get("size") or raw.get("qty") or raw.get("positionSize"))
        
        # 🔥🔥🔥 FIX OBLIGATORIO
        leverage = self._safe_float(raw.get("leverage") or raw.get("leverageR") or 20)

        entry_price = self._safe_float(
            raw.get("entryPrice") or raw.get("avgPrice") or raw.get("avgEntryPrice")
        )

        mark_price = self._safe_float(
            raw.get("markPrice") or raw.get("lastPrice") or raw.get("marketPrice")
        )

        pnl = calculate_pnl(entry_price, mark_price, size, side)

        # 🔥🔥🔥 FIX OBLIGATORIO: ROI ahora exige leverage como 4to parámetro
        roi = calculate_roi(entry_price, mark_price, side, leverage)

        # 🔥🔥🔥 FIX OBLIGATORIO: calculate_loss_pct_from_roi TAMBIÉN EXIGE leverage
        loss_pct = calculate_loss_pct_from_roi(roi, leverage)

        return {
            "symbol": symbol,
            "side": side,
            "size": size,
            "leverage": leverage,
            "entry_price": entry_price,
            "mark_price": mark_price,
            "pnl": pnl,
            "roi": roi,
            "loss_pct": loss_pct,
            "raw": raw,
        }

    # ------------------------------------------------------
    async def _call_callback(self, position: PositionDict):
        try:
            result = self._process_position_callback(position)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"❌ Error en callback para {position.get('symbol')}: {e}", exc_info=True)

    # ------------------------------------------------------
    async def run_once(self):
        logger.info("📡 Evaluando posiciones abiertas…")

        try:
            positions: List[Dict[str, Any]] = get_open_positions()
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones Bybit: {e}", exc_info=True)
            return

        if not positions:
            logger.info("📭 No hay posiciones abiertas.")
            return

        logger.info(f"🔍 {len(positions)} posiciones detectadas:")

        for raw_pos in positions:
            try:
                position = self._enrich_position(raw_pos)

                logger.info(
                    f"🔎 {position['symbol']} | {position['side'].upper()} | "
                    f"ROI={position['roi']:.2f}% | loss={position['loss_pct']:.2f}%"
                )

                await self._call_callback(position)

            except Exception as e:
                logger.error(f"❌ Error evaluando posición {raw_pos}: {e}", exc_info=True)

    # ------------------------------------------------------
    async def run_forever(self):
        logger.info("🔄 OperationTrackerAdapter.run_forever() iniciado.")
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"❌ Error ciclo OperationTracker: {e}", exc_info=True)
            await asyncio.sleep(self._interval_seconds)


# ------------------------------------------------------
async def start_operation_tracker():
    async def _log_only_callback(position: PositionDict):
        logger.info(
            f"🧩 Callback LITE: {position['symbol']} | "
            f"{position['side'].upper()} | ROI={position['roi']:.2f}%"
        )

    adapter = OperationTrackerAdapter(
        fetch_positions_func=get_open_positions,
        process_position_callback=_log_only_callback,
        interval_seconds=20,
    )

    await adapter.run_forever()
