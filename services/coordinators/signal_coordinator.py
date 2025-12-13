# ======================================================================
# signal_coordinator.py — versión GPT 2025-12 final
# ======================================================================

import logging
from typing import Optional

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina TODA la lógica relacionada con señales:
    - Procesar señales nuevas (desde telegram_reader)
    - Ejecutar análisis técnico con TechnicalEngine
    - Guardar logs de análisis en la base de datos
    - Determinar reactivaciones con ReactivationEngine
    - Auto-reanamizar señales pendientes cada X minutos
    - Enviar resultados por Telegram
    """

    def __init__(
        self,
        signal_service,
        analysis_service,
        technical_engine,
        reactivation_engine,
        notifier,
    ):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.technical_engine = technical_engine
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier

        logger.info("📡 SignalCoordinator inicializado correctamente.")

    # ==================================================================
    # 1) PROCESAR SEÑALES NUEVAS (desde telegram_reader)
    # ==================================================================
    async def process_new_signal(self, signal: dict):
        """
        Procesa UNA nueva señal recibida desde Telegram.
        """
        try:
            symbol = signal["symbol"]
            direction = signal["direction"]

            logger.info(f"📩 Nueva señal recibida — {symbol} {direction}")

            # Ejecutar análisis técnico
            analysis = await self.analysis_service.analyze_symbol(
                symbol=symbol, direction=direction
            )

            # Guardar análisis en DB
            self.signal_service.save_analysis_log(
                signal_id=signal["id"],
                result=analysis,
                status="processed",
            )

            # Enviar mensaje formateado
            msg = self._format_analysis(analysis, symbol)
            await self.notifier.send(msg)

        except Exception as e:
            logger.exception(f"❌ Error procesando nueva señal: {e}")
            await self.notifier.send(f"❌ Error analizando {signal.get('symbol')}")

    # ==================================================================
    # 2) MANUAL — /analizar SYMBOL DIRECTION
    # ==================================================================
    async def manual_analyze_request(self, symbol: str, direction: str):
        """
        Permite ejecutar un análisis manual con /analizar.
        """
        try:
            analysis = await self.analysis_service.analyze_symbol(symbol, direction)
            txt = self._format_analysis(analysis, symbol, include_context=True)
            await self.notifier.send(txt)
        except Exception as e:
            logger.exception(f"❌ Error en análisis manual: {e}")
            await self.notifier.send(f"❌ Error analizando {symbol}")

    # ==================================================================
    # 3) AUTO-REACTIVACIÓN (background)
    # ==================================================================
    async def auto_reactivate(self):
        """
        Ejecuta reactivación automática en señales pendientes.
        Llamado desde signal_reactivation_sync.py
        """
        pending = self.signal_service.get_pending_signals()

        if not pending:
            return

        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for sig in pending:
            try:
                symbol = sig["symbol"]
                direction = sig["direction"]

                logger.info(f"🔍 Reactivando {symbol} {direction} (ID={sig['id']})")

                analysis = await self.analysis_service.analyze_symbol(
                    symbol=symbol, direction=direction
                )

                decision = self.reactivation_engine.evaluate(
                    analysis=analysis, signal=sig
                )

                # Guardar resultado
                self.signal_service.save_reactivation_event(
                    signal_id=sig["id"],
                    status=decision["status"],
                    details=decision,
                )

                # Notificar si aplica
                if decision["should_notify"]:
                    await self.notifier.send(
                        f"📌 *Reactivación {symbol}:* {decision['message']}"
                    )

            except Exception as e:
                logger.exception(
                    f"❌ Error evaluando reactivación ID={sig.get('id')}: {e}"
                )

    # ==================================================================
    # 4) FORMATO MENSAJES TELEGRAM
    # ==================================================================
    def _format_analysis(
        self, result: dict, symbol: str, include_context: bool = False
    ) -> str:
        """
        Construye mensaje final para Telegram.
        """

        try:
            decision = result.get("decision", "-")
            score = result.get("technical_score", 0)
            match_ratio = result.get("match_ratio", 0)
            confidence = result.get("confidence", 0)
            grade = result.get("grade", "-")
            reasons = result.get("decision_reasons", [])

            msg = f"📊 *Análisis de {symbol}*\n"

            if include_context:
                msg += f"🧭 Contexto: *Entrada*\n\n"

            msg += (
                f"🔴 *Decisión:* `{decision}`\n"
                f"📈 *Score técnico:* {score}\n"
                f"🎯 *Match técnico:* {match_ratio} %\n"
                f"🔎 *Confianza:* {confidence * 100:.0f} %\n"
                f"🏅 *Grade:* {grade}\n\n"
            )

            msg += "📌 *Motivos:*\n"
            for r in reasons:
                msg += f"• {r}\n"

            return msg

        except Exception as e:
            logger.exception(f"❌ Error formateando mensaje: {e}")
            return "❌ Error generando mensaje."
