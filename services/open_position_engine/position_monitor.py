# services/open_position_engine/position_monitor.py

import asyncio
import logging
from services.bybit_service.bybit_client import get_open_positions, get_ohlcv_data

logger = logging.getLogger("position_monitor")


class PositionMonitor:

    def __init__(self, engine, notifier, interval_low=600, interval_high=300):
        """
        engine        → instancia de OpenPositionEngine
        notifier      → Notifier (safe_send async)
        interval_low  → segundos cuando mercado está estable (10 min)
        interval_high → segundos para mercado volátil (5 min)
        """
        self.engine = engine
        self.notifier = notifier
        self.interval_low = interval_low
        self.interval_high = interval_high

        self._running = False
        self._last_state = {}  # evita spam, guarda última acción recomendada

    # ============================================================
    # 🔄 Lazo principal (background task)
    # ============================================================
    async def start(self):
        if self._running:
            logger.warning("⚠️ PositionMonitor ya está en ejecución.")
            return

        self._running = True
        logger.info("🟦 PositionMonitor iniciado (async).")

        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.exception(f"❌ Error en ciclo PositionMonitor: {e}")

            # calcular intervalo dinámico
            sleep_time = await self._compute_dynamic_interval()
            logger.info(
                f"🕒 Próxima evaluación de posiciones en {sleep_time} segundos."
            )
            await asyncio.sleep(sleep_time)

    def is_running(self) -> bool:
        return self._running

    # ============================================================
    # 🔴 Detener monitor
    # ============================================================
    def stop(self):
        logger.info("🟥 PositionMonitor detenido por comando.")
        self._running = False

    # ============================================================
    # 🔍 Evaluación ciclo por ciclo
    # ============================================================
    async def _run_cycle(self):
        positions = await get_open_positions()

        if not positions:
            logger.info("🟦 No hay posiciones abiertas actualmente.")
            return

        logger.info(f"📌 Evaluando {len(positions)} operación(es) abierta(s)...")

        for pos in positions:
            await self._evaluate_single_position(pos)

    # ============================================================
    # 🧩 Evaluación individual
    # ============================================================
    async def _evaluate_single_position(self, pos):
        symbol = pos.get("symbol")
        side = pos.get("side", "").lower()
        entry = float(pos.get("entryPrice"))
        mark = float(pos.get("markPrice"))

        raw_move = (mark - entry) / entry * 100
        pnl_pct = raw_move if side == "long" else -raw_move

        logger.info(f"🔎 {symbol} ({side}) → PnL: {pnl_pct:.2f}%")

        # llamar a motor táctico
        decision = await self.engine.evaluate_single(
            symbol=symbol, side=side, pnl_pct=pnl_pct
        )

        # evitar spam: enviar solo si cambia acción
        last = self._last_state.get(symbol)

        if not last or last != decision.action:
            await self.notifier.safe_send(
                self._format_msg(symbol, side, pnl_pct, decision)
            )
            self._last_state[symbol] = decision.action

    # ============================================================
    # 📄 Formato del mensaje
    # ============================================================
    def _format_msg(self, symbol, side, pnl_pct, decision):
        reasons = "\n".join([f"• {r}" for r in decision.reasons])

        return (
            f"📊 *Evaluación de operación abierta*\n"
            f"🪙 *Par:* {symbol}\n"
            f"📌 *Dirección:* {side}\n"
            f"💰 *PnL actual:* {pnl_pct:.2f}%\n"
            f"🎯 *Score técnico:* {decision.score}\n"
            f"🧭 *Acción sugerida:* `{decision.action}`\n"
            f"⚠️ *Riesgo:* {decision.risk}\n\n"
            f"📝 *Motivos:*\n{reasons}"
        )

    # ============================================================
    # ⚙️ Intervalo dinámico según ATR
    # ============================================================
    async def _compute_dynamic_interval(self):
        """
        Reduce el intervalo cuando el mercado está volátil.
        Usa ATR del par más relevante (ej: BTCUSDT).
        """
        try:
            df = await get_ohlcv_data("BTCUSDT", "60", limit=50)
            if df is None or df.empty:
                return self.interval_low

            atr = df.ta.atr(length=14).iloc[-1]

            # ATR > 200 → mercado volátil → revisar rápido
            if atr > 200:
                return self.interval_high
            else:
                return self.interval_low

        except Exception as e:
            logger.exception(f"❌ No se pudo calcular ATR dinámico: {e}")
            return self.interval_low
