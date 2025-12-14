# services/open_position_engine/open_position_engine.py

import logging
from services.bybit_service.bybit_client import get_open_positions
from helpers import (
    calculate_price_change,
    calculate_roi,
    normalize_leverage,
)

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    def __init__(self, notifier, analysis_service):
        self.notifier = notifier
        self.analysis_service = analysis_service

    async def evaluate_open_positions(self):
        """
        Evalúa posiciones abiertas en Bybit con ROI real (apalancamiento incluido).
        NUNCA debe romper la app.
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

                leverage = normalize_leverage(p.get("leverage", 20))

                if entry <= 0 or mark <= 0:
                    logger.warning(f"⚠️ {symbol}: precios inválidos")
                    continue

                price_change_pct = calculate_price_change(
                    entry, mark, direction
                )  # sin apalancamiento

                roi_pct = calculate_roi(
                    entry, mark, direction, leverage
                )  # con apalancamiento (20x incluido)

                logger.info(
                    f"🔎 {symbol} ({direction}) → "
                    f"price={price_change_pct:.2f}% | "
                    f"ROI={roi_pct:.2f}% (x{leverage})"
                )

                # 🔜 B4 / C:
                # if roi_pct <= -30: warning
                # if roi_pct <= -50: evaluar cierre / reversión

            except Exception as e:
                logger.exception(f"❌ Error evaluando posición {symbol}: {e}")
