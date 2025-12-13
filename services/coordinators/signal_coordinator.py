# ======================================================================
# signal_coordinator.py — versión estabilizada 2025-12
# ======================================================================

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina TODA la lógica relacionada con señales:
    - Procesar señales nuevas (desde telegram_reader)
    - Ejecutar análisis técnico con AnalysisService/TechnicalEngine
    - Guardar logs de análisis en la base de datos
    - Determinar reactivaciones con ReactivationEngine
    - Auto-reanalizar señales pendientes cada X minutos
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
    async def process_new_signal(self, signal: Dict[str, Any]):
        """
        Procesa UNA nueva señal recibida desde Telegram.

        `signal` debe contener al menos:
            - id
            - symbol
            - direction
            - raw_text (opcional)
        """
        try:
            symbol = signal["symbol"]
            direction = signal["direction"]

            logger.info(f"📩 Nueva señal recibida — {symbol} {direction}")

            # Ejecutar análisis técnico (contexto = entrada)
            analysis = await self.analysis_service.analyze_symbol(
                symbol=symbol,
                direction=direction,
                context="entry",
            )

            # Guardar análisis en DB (si hay id)
            signal_id = signal.get("id")
            if signal_id is not None:
                try:
                    # usamos context="entry" como etiqueta
                    self.signal_service.save_analysis_log(
                        signal_id=signal_id,
                        context="entry",
                        analysis=analysis,
                    )
                except Exception as e:
                    logger.exception(
                        f"⚠️ No se pudo guardar log de análisis para señal {signal_id}: {e}"
                    )

            # Enviar mensaje formateado
            msg = self.analysis_service.format_for_telegram(
                symbol=symbol,
                direction=direction,
                result=analysis,
                context="entry",
            )
            await self.notifier.safe_send(msg)

        except Exception as e:
            logger.exception(f"❌ Error procesando nueva señal: {e}")
            await self.notifier.safe_send(
                f"❌ Error analizando {signal.get('symbol', 'N/D')}"
            )

    # ==================================================================
    # 2) MANUAL — /analizar SYMBOL DIRECTION
    # ==================================================================
    async def manual_analyze_request(self, symbol: str, direction: str):
        """
        Permite ejecutar un análisis manual con /analizar.
        """
        try:
            analysis = await self.analysis_service.analyze_symbol(
                symbol=symbol,
                direction=direction,
                context="entry",
            )
            txt = self.analysis_service.format_for_telegram(
                symbol=symbol,
                direction=direction,
                result=analysis,
                context="entry",
            )
            await self.notifier.safe_send(txt)
        except Exception as e:
            logger.exception(f"❌ Error en análisis manual: {e}")
            await self.notifier.safe_send(f"❌ Error analizando {symbol}")

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
                signal_id = sig["id"]
                symbol = sig["symbol"]
                direction = sig["direction"]

                logger.info(f"🔍 Reactivando {symbol} {direction} (ID={signal_id})")

                # 1) Análisis técnico en contexto "reactivation"
                analysis = await self.analysis_service.analyze_symbol(
                    symbol=symbol,
                    direction=direction,
                    context="reactivation",
                )

                # 2) Decisión táctica del motor de reactivación
                decision = await self.reactivation_engine.evaluate_signal(
                    symbol=symbol,
                    direction=direction,
                    analysis=analysis,
                )

                # decision esperado:
                # {
                #   "allowed": bool,
                #   "reason": str,
                #   "analysis": dict,
                # }

                if decision.get("allowed"):
                    # marcar como reactivada
                    self.signal_service.mark_reactivated(signal_id)
                    msg = (
                        f"⚡ *Reactivación permitida* para {symbol} "
                        f"({direction}) — {decision.get('reason')}"
                    )
                    await self.notifier.safe_send(msg)
                else:
                    logger.info(
                        f"⏳ Señal {signal_id} aún no apta para reactivación: "
                        f"{decision.get('reason')}"
                    )

            except Exception as e:
                logger.exception(
                    f"❌ Error evaluando reactivación ID={sig.get('id')}: {e}"
                )
