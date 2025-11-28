"""
reactivation_controller.py
---------------------------
Controlador oficial para reactivación de señales pendientes.

Reemplaza completamente signal_reactivation_sync.py.

Flujo:
    scheduler → ReactivationMonitor → db_service → signal_engine → telegram_service

Objetivo:
    Revisar señales pendientes en DB y determinar si ahora son viables
    para entrar con entrada inmediata.

Criterios típicos:
    - match_ratio >= threshold
    - tendencia alineada en MTF
    - reversión detectada a favor de la señal original
    - dirección coincide con la señal original
"""

import asyncio
import logging
from datetime import datetime

from core.signal_engine import analyze_signal
from services import db_service
from services.telegram_service import send_message

logger = logging.getLogger("reactivation_controller")

DEFAULT_INTERVAL_MIN = 15  # cada cuánto revisar las señales pendientes


# ============================================================
# 🔵 MONITOR PRINCIPAL DE REACTIVACIONES
# ============================================================
class ReactivationMonitor:

    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        if self.running:
            logger.warning("⚠️ ReactivationMonitor ya está activo.")
            return

        self.running = True
        self.task = asyncio.create_task(self._loop())
        await send_message("♻️ Monitor de reactivaciones activado.")
        logger.info("ReactivationMonitor iniciado.")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        await send_message("🛑 Monitor de reactivaciones detenido.")
        logger.info("ReactivationMonitor detenido.")

    # ========================================================
    async def _loop(self):
        """
        Loop continuo: revisa señales pendientes en la DB.
        """

        while self.running:
            try:
                await self.evaluate_pending_signals()
            except Exception as e:
                logger.error(f"❌ Error en evaluate_pending_signals(): {e}")

            await asyncio.sleep(DEFAULT_INTERVAL_MIN * 60)


    # ========================================================
    # 🔵 EVALUACIÓN DE SEÑALES PENDIENTES
    # ========================================================
    async def evaluate_pending_signals(self):
        pending = db_service.get_pending_signals()

        if not pending:
            logger.info("♻️ No hay señales pendientes para reactivación.")
            return

        logger.info(f"♻️ Revisando {len(pending)} señales pendientes…")

        for signal in pending:
            try:
                await self.evaluate_single_signal(signal)
            except Exception as e:
                logger.error(f"❌ Error evaluando señal pendiente {signal}: {e}")


    # ========================================================
    # 🔵 LÓGICA DE REACTIVACIÓN INDIVIDUAL
    # ========================================================
    async def evaluate_single_signal(self, signal):
        """
        Estructura típica de signal desde DB:

        {
            "id": 12,
            "symbol": "BTCUSDT",
            "direction": "short",
            "entry": 42500.0,
            "status": "pending",
            ...
        }
        """

        signal_id = signal["id"]
        symbol = signal["symbol"]
        direction = signal["direction"]

        logger.info(f"♻️ Revisando señal pendiente #{signal_id}: {symbol} ({direction})")

        # Ejecutar motor técnico
        try:
            analysis = await analyze_signal(symbol, direction)
        except Exception as e:
            logger.error(f"❌ Error en motor técnico: {e}")
            return

        decision = analysis.get("decision")
        match_ratio = analysis.get("match_ratio")
        grade = analysis.get("grade")

        # Guardar log técnico
        db_service.add_analysis_log(
            signal_id=signal_id,
            match_ratio=match_ratio,
            recommendation=decision,
            details=f"[REACTIVATION] grade={grade}, decision={decision}"
        )

        # ======================================================
        # 🔥 CASO 1 — ENTRADA INMEDIATA (MATCH FUERTE)
        # ======================================================
        if decision == "enter":
            await send_message(
                f"🟢 **Reactivación: Entrada viable ahora mismo**\n\n"
                f"Par: {symbol}\n"
                f"Dirección: {direction}\n"
                f"Match Ratio: {match_ratio}%\n"
                f"Grado: {grade}\n\n"
                f"✔ La señal cumple condiciones óptimas para entrada.\n"
                f"✔ Tendencias alineadas.\n"
            )
            db_service.set_signal_reactivated(signal_id)
            logger.info(f"♻️ Señal #{signal_id} REACTIVADA exitosamente.")
            return

        # ======================================================
        # 🔶 CASO 2 — AÚN NO ES VIABLE
        # ======================================================
        if decision in ("wait", "skip"):
            logger.info(f"⏳ Señal #{signal_id}: condiciones insuficientes.")
            return

        # ======================================================
        # 🔴 CASO 3 — RIESGO DE REVERSIÓN
        # ======================================================
        if decision in ("reversal-risk", "close"):
            await send_message(
                f"🔴 **Reactivación anulada por riesgo de reversión**\n\n"
                f"Par: {symbol}\n"
                f"Dirección original: {direction}\n"
                f"Match Ratio: {match_ratio}%\n"
                f"Grado: {grade}\n\n"
                f"⚠ Tendencia en contra. No se recomienda entrar."
            )
            db_service.set_signal_ignored(signal_id)
            logger.info(f"🔴 Señal #{signal_id} marcada como ignorada.")
            return

        # fallback
        logger.error(f"⚠ Decisión inesperada: {decision}")


# ============================================================
# 🔵 INSTANCIA GLOBAL
# ============================================================
reactivation_monitor = ReactivationMonitor()
