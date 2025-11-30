from services.telegram_sender import safe_send
from core.signal_engine import analyze_reactivation
from services.db_service import get_pending_signals, set_signal_reactivated
import logging

logger = logging.getLogger("reactivation_controller")


async def run_reactivation_cycle():
    pendings = get_pending_signals()

    if not pendings:
        logger.info("📭 No hay señales pendientes para reactivar.")
        return

    for sig in pendings:
        decision = await analyze_reactivation(sig)
        if decision["reactivate"]:
            await safe_send(decision["msg"])
            set_signal_reactivated(sig["id"])
