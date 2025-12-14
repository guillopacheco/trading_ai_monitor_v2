# services/open_position_engine/position_monitor.py
import asyncio
import logging

logger = logging.getLogger("position_monitor")


async def start_open_position_monitor(app_layer, interval_sec: int = 60):
    """
    Monitor mínimo y estable:
    - No asume método exacto
    - Intenta varias firmas comunes
    - No rompe la app si falla una vez
    """
    logger.info("📌 Monitor de posiciones abiertas iniciado")

    while True:
        try:
            op = getattr(app_layer, "operation", None)
            if not op:
                logger.warning(
                    "⚠️ ApplicationLayer no tiene OperationService (app_layer.operation)"
                )
            else:
                # Intentos en orden (sin tocar tu lógica interna)
                if hasattr(op, "check_open_positions"):
                    res = op.check_open_positions()
                    if asyncio.iscoroutine(res):
                        await res

                elif hasattr(op, "monitor_open_positions"):
                    res = op.monitor_open_positions()
                    if asyncio.iscoroutine(res):
                        await res

                elif hasattr(op, "evaluate_open_positions"):
                    res = op.evaluate_open_positions()
                    if asyncio.iscoroutine(res):
                        await res

                else:
                    logger.warning(
                        "⚠️ OperationService no expone check/monitor/evaluate_open_positions()"
                    )

        except Exception as e:
            logger.exception(f"❌ Error en monitor de posiciones: {e}")

        await asyncio.sleep(interval_sec)
