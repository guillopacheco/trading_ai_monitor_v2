# services/operation_service/operation_service.py

import logging
from typing import List, Dict, Optional, Tuple

from services.bybit_service.bybit_client import (
    get_open_positions,
    close_position as bybit_close_position,
    reverse_position as bybit_reverse_position,
)

logger = logging.getLogger("operation_service")


class OperationService:
    """
    Servicio de alto nivel para operaciones abiertas en Bybit.

    Responsabilidades:
    - Obtener y normalizar las posiciones abiertas desde Bybit.
    - Exponer acceso sencillo a:
        • listar todas las operaciones abiertas
        • obtener una operación por símbolo
        • cerrar o revertir una operación
    - Proveer una clasificación simple de riesgo según pérdida (%).
    """

    # Umbrales de pérdida para advertencias (-30, -50, -70, -90)
    LOSS_LEVELS = (30, 50, 70, 90)

    # ============================================================
    # Helpers internos
    # ============================================================

    async def _fetch_raw_positions(self) -> List[Dict]:
        """
        Llama al cliente Bybit para traer las posiciones abiertas.
        Siempre devuelve una lista (vacía en caso de error).
        """
        try:
            raw = await get_open_positions()
            if not raw:
                return []
            return raw
        except Exception:
            logger.exception("❌ Error obteniendo posiciones abiertas desde Bybit.")
            return []

    @staticmethod
    def _normalize_side(raw_side: str) -> str:
        """
        Normaliza el 'lado' de la operación a: long | short | unknown
        """
        if not raw_side:
            return "unknown"
        s = str(raw_side).lower()
        if "buy" in s or s == "long":
            return "long"
        if "sell" in s or s == "short":
            return "short"
        return s

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _normalize_position(self, raw: Dict) -> Dict:
        """
        Convierte el diccionario crudo de Bybit a un formato interno consistente.

        Campos clave que intentamos exponer:
        - symbol
        - direction (long|short)
        - entry_price
        - mark_price
        - loss_pct (si existe, si no, caemos a 0.0)
        - pnl_pct (si viene del cliente)
        - leverage (si está disponible)
        """

        symbol = raw.get("symbol") or raw.get("symbolName") or "UNKNOWN"

        direction = (
            raw.get("direction")
            or raw.get("side")
            or raw.get("positionSide")
            or ""
        )
        direction = self._normalize_side(direction)

        entry_price = self._safe_float(
            raw.get("entry_price")
            or raw.get("entryPrice")
            or raw.get("avgPrice")
            or raw.get("avgEntryPrice")
        )

        mark_price = self._safe_float(
            raw.get("mark_price")
            or raw.get("markPrice")
            or raw.get("lastPrice")
            or raw.get("marketPrice")
        )

        # Pérdida/ganancia en %
        pnl_pct = self._safe_float(
            raw.get("pnl_pct")
            or raw.get("pnlPercent")
            or raw.get("pnl_pct_usd")
        )

        # Pérdida "normalizada" (lo que usan los coordinadores)
        loss_pct = self._safe_float(
            raw.get("loss_pct")
            or raw.get("lossPercent")
        )

        leverage = self._safe_float(
            raw.get("leverage")
            or raw.get("leverageR")
            or raw.get("leverageValue")
            or 20  # fallback razonable para tu caso
        )

        normalized = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "mark_price": mark_price,
            "pnl_pct": pnl_pct,
            "loss_pct": loss_pct,
            "leverage": leverage,
            "raw": raw,
        }

        return normalized

    # ============================================================
    # API pública principal
    # ============================================================

    async def list_open_positions(self) -> List[Dict]:
        """
        Devuelve TODAS las operaciones abiertas en formato normalizado.
        """
        raw_positions = await self._fetch_raw_positions()
        return [self._normalize_position(p) for p in raw_positions]

    async def get_open_position(self, symbol: str) -> Optional[Dict]:
        """
        Devuelve la operación abierta para un símbolo concreto (si existe).
        Símbolo se compara en mayúsculas.
        """
        symbol_upper = symbol.upper()
        positions = await self.list_open_positions()

        for pos in positions:
            if pos.get("symbol", "").upper() == symbol_upper:
                return pos

        return None

    async def close(self, symbol: str) -> bool:
        """
        Cierra la posición de un símbolo concreto en Bybit.
        Devuelve True si la llamada no lanza excepción.
        """
        try:
            await bybit_close_position(symbol)
            logger.info(f"🛑 Operación cerrada en Bybit: {symbol}")
            return True
        except Exception:
            logger.exception(f"❌ Error cerrando posición en Bybit: {symbol}")
            return False

    async def reverse(self, symbol: str) -> bool:
        """
        Invierte la posición de un símbolo concreto en Bybit.
        Devuelve True si la llamada no lanza excepción.
        """
        try:
            await bybit_reverse_position(symbol)
            logger.info(f"🔄 Operación revertida en Bybit: {symbol}")
            return True
        except Exception:
            logger.exception(f"❌ Error revirtiendo posición en Bybit: {symbol}")
            return False

    # ============================================================
    # Clasificación de riesgo (reutilizable por coordinadores)
    # ============================================================

    @staticmethod
    def classify_risk(loss_pct: float) -> Tuple[str, str]:
        """
        Clasificación lógica de riesgo según % de pérdida.
        Devuelve: (riesgo, mensaje)
        Se asume que loss_pct es un valor NEGATIVO o magnitud de pérdida.
        """
        # Normalizamos a valor negativo por si llega como positivo
        lp = -abs(loss_pct)

        if lp <= -90:
            return "critical", "⚠️ Pérdida extrema (-90%) — acción inmediata recomendada."
        elif lp <= -70:
            return "very_high", "⚠️ Riesgo MUY alto (-70%) — revisión urgente."
        elif lp <= -50:
            return "high", "⚠️ Pérdida alta (-50%) — evaluar reversión/cierre."
        elif lp <= -30:
            return "medium", "⚠️ Pérdida moderada (-30%) — revisar condiciones."
        else:
            return "safe", "Operación estable o pérdida controlada."
