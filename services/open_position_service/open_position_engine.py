# services/open_position_engine/open_position_engine.py

import logging
from services.bybit_service.bybit_client import get_open_positions, get_ohlcv_data
from services.technical_engine.technical_engine import analyze
from services.positions_service.operation_tracker import OperationTracker

logger = logging.getLogger("open_position_engine")


class OpenPositionEngine:
    """
    Motor encargado de evaluar operaciones abiertas en Bybit y decidir:
    - mantener
    - cerrar
    - revertir
    - evaluar (drawdown intermedio)
    """

    def __init__(self, notifier, tracker: OperationTracker):
        self.notifier = notifier
        self.tracker = tracker

    # ================================================================
    # 🔍 Evaluación completa (llamada por position_monitor.py)
    # ================================================================
    async def evaluate_open_positions(self):
        """
        1. Obtiene posiciones abiertas
        2. Evalúa drawdown
        3. Aplica análisis técnico
        4. Decide acción recomendada
        """
        positions = await get_open_positions()

        if not positions:
            logger.info("🟦 No hay posiciones abiertas.")
            return

        for pos in positions:
            symbol = pos["symbol"]
            side = pos["side"].lower()
            entry_price = float(pos["entryPrice"])
            mark = float(pos["markPrice"])
            pct = (
                ((mark - entry_price) / entry_price)
                * 100
                * (1 if side == "long" else -1)
            )

            logger.info(f"Evaluando {symbol} ({side}) → PnL {pct:.2f}%")

            await self._evaluate_position(symbol, side, pct)

    # ================================================================
    # 📘 Evaluación por símbolo individual
    # ================================================================
    async def _evaluate_position(self, symbol: str, side: str, pnl_pct: float):
        """
        Internamente decide la acción:
        - pérdida ≥ 30% → evaluación intermedia
        - pérdida ≥ 50% → posible reversión
        - pérdida ≥ 70% → reversión sugerida fuerte
        - pérdida ≥ 90% → cierre urgente
        """

        # ------------------------------------------------------------
        # Fase 1 — Activar análisis técnico completo
        # ------------------------------------------------------------
        result = await analyze(symbol, side, context="open_position")

        technical_score = result.get("technical_score", 0)
        match_ratio = result.get("match_ratio", 0)
        bias = result.get("smart_bias_code")
        grade = result.get("grade")

        # ------------------------------------------------------------
        # Fase 2 — Lógica táctica por drawdown
        # ------------------------------------------------------------
        if pnl_pct <= -90:
            decision = "close"
            reason = "Drawdown extremo (≥ -90%) → cierre urgente"

        elif pnl_pct <= -70:
            decision = "reverse"
            reason = "Pérdida severa (≥ -70%) + análisis confirma tendencia contraria"

        elif pnl_pct <= -50:
            decision = (
                "reverse"
                if bias.startswith("bull") or bias.startswith("bear")
                else "close"
            )
            reason = "Pérdida fuerte (≥ -50%). Se evalúa reversión."

        elif pnl_pct <= -30:
            decision = "evaluate"
            reason = "Pérdida moderada (≥ -30%). Evaluación intermedia."

        else:
            decision = "hold"
            reason = "Operación saludable."

        # ------------------------------------------------------------
        # Fase 3 — Ajustes con análisis técnico
        # ------------------------------------------------------------
        if decision in ["reverse", "close"]:
            if technical_score < 40 and match_ratio < 60:
                # Condiciones muy débiles → preferir cierre
                decision = "close"

            if grade == "A" and pnl_pct > -50:
                # Muy buena señal técnica → evitar cerrar a pérdidas
                decision = "hold"

        # ------------------------------------------------------------
        # Fase 4 — Notificación
        # ------------------------------------------------------------
        msg = (
            f"📊 *Evaluación de {symbol}*\n"
            f"🔹 *Side:* {side}\n"
            f"🔹 *PnL:* {pnl_pct:.2f}%\n"
            f"🔹 *Score:* {technical_score}\n"
            f"🔹 *Match:* {match_ratio}%\n"
            f"🔹 *Bias:* {bias}\n"
            f"🔹 *Grade:* {grade}\n\n"
            f"📌 *Acción sugerida:* `{decision}`\n"
            f"📝 *Motivo:* {reason}"
        )

        await self.notifier.safe_send(msg)

        # Registrar evento
        self.tracker.log_open_position_event(symbol, side, pnl_pct, decision, reason)
