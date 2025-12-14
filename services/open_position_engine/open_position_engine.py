# services/open_position_engine/open_position_engine.py
import logging
from services.bybit_service.bybit_client import get_open_positions
from services.helpers import calculate_price_change, calculate_roi, normalize_leverage

# ...
direction = "long" if pos["side"].lower() in ("buy", "long") else "short"
entry_price = float(pos["entryPrice"])
mark = float(pos["markPrice"])

leverage = normalize_leverage(pos.get("leverage", 20))  # fallback 20x si no viene

price_change_pct = calculate_price_change(
    entry_price, mark, direction
)  # sin apalancamiento
roi_pct = calculate_roi(entry_price, mark, direction, leverage)  # con apalancamiento

logger.info(
    f"Evaluando {symbol} ({direction}) → price={price_change_pct:.2f}% | ROI={roi_pct:.2f}% (x{leverage})"
)

await self._evaluate_position(symbol, direction, roi_pct, price_change_pct, leverage)


logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier, analysis_service):
        self.notifier = notifier
        self.analysis_service = analysis_service

    async def evaluate_open_positions(self):
        """
        Evalúa posiciones abiertas en Bybit con ROI real (apalancamiento incluido).
        NO debe romper nunca.
        """

        try:
            positions = await get_open_positions()
        except Exception as e:
            logger.exception(f"❌ Error obteniendo posiciones abiertas: {e}")
            return

        if not positions:
            logger.info("📭 No hay posiciones abiertas actualmente.")
            return

        logger.info(f"📌 Posiciones abiertas detectadas: {len(positions)}")

        for p in positions[:20]:
            try:
                symbol = p.get("symbol") or p.get("symbolName") or "UNKNOWN"
                side = p.get("side", "").lower()
                direction = "long" if side in ("buy", "long") else "short"

                entry = float(p.get("entryPrice", 0))
                mark = float(p.get("markPrice", 0))
                leverage = float(p.get("leverage", 20)) or 20

                if entry <= 0 or mark <= 0:
                    logger.warning(f"⚠️ {symbol}: precios inválidos")
                    continue

                price_change = (mark - entry) / entry
                if direction == "short":
                    price_change *= -1

                roi_pct = price_change * leverage * 100

                logger.info(
                    f"🔎 {symbol} ({direction}) "
                    f"entry={entry} mark={mark} lev=x{leverage} "
                    f"ROI={roi_pct:.2f}%"
                )

                # 🔔 aquí luego conectas lógica B4:
                # if roi_pct <= -30: warn
                # if roi_pct <= -50: evaluar cierre / reversión
                # etc.

            except Exception as e:
                logger.exception(f"❌ Error evaluando posición {p}: {e}")
