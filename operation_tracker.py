"""
operation_tracker.py
------------------------------------------------------------
Monitor inteligente de operaciones abiertas en Bybit.

Funciones:
✔ Lee posiciones abiertas desde bybit_client.get_open_positions()
✔ Calcula ROI y PnL real
✔ Detecta pérdidas críticas por niveles
✔ Obtiene análisis técnico rápido en 5m–15m–1h
✔ Genera recomendación contextual inteligente
✔ Envía alerta mediante notifier.notify_operation_alert()

Este módulo NO toca la base de datos.
Es puramente operativo.
------------------------------------------------------------
"""

import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from indicators import get_technical_data
from notifier import notify_operation_alert

logger = logging.getLogger("operation_tracker")


# ============================================================
# 🔢 Cálculo de ROI y niveles de pérdida
# ============================================================

LOSS_LEVELS = [-3, -5, -10, -20, -30, -50, -70]


def compute_roi(entry: float, mark: float, leverage: int, direction: str) -> float:
    """Retorna ROI real considerando dirección y apalancamiento."""
    if entry <= 0:
        return 0.0

    roi = ((mark - entry) / entry) * 100
    if direction == "short":
        roi *= -1

    return roi * leverage


def compute_loss_level(roi: float) -> int | None:
    """Devuelve el nivel de pérdida alcanzado (-3, -5, etc)."""
    for level in LOSS_LEVELS:
        if roi <= level:
            return level
    return None



# ============================================================
# 🎯 Generador de recomendación
# ============================================================

def build_suggestion(direction: str, tech: Dict[str, Any], roi: float) -> str:
    """
    Genera recomendación en lenguaje natural:
    - Revisar
    - Cerrar
    - Revertir
    """

    trend_5m = (tech.get("5m", {}).get("trend") or "").lower()
    trend_15m = (tech.get("15m", {}).get("trend") or "").lower()
    trend_1h = (tech.get("1h", {}).get("trend") or "").lower()

    # Estado técnico
    short_tf = f"{trend_5m} / {trend_15m}"
    big_tf = trend_1h

    # Caso fuerte: todo contra la operación
    if direction == "long" and ("bear" in short_tf or "bear" in big_tf):
        if roi <= -20:
            return "Cerrar o revertir inmediatamente (tendencia fuertemente en contra)"
        return "Tendencia desfavorable: evaluar cierre"

    if direction == "short" and ("bull" in short_tf or "bull" in big_tf):
        if roi <= -20:
            return "Cerrar o revertir inmediatamente (tendencia fuertemente en contra)"
        return "Tendencia desfavorable: evaluar cierre"

    # Caso neutro
    if abs(roi) < 5:
        return "Movimiento neutro, continuar monitoreando"

    # Caso favorable
    if roi > 5:
        return "Operación saludable, mantener"

    return "Evaluación estándar"


# ============================================================
# 🚨 Monitor de operaciones
# ============================================================

def monitor_open_positions():
    """
    MONITOR PRINCIPAL
    Llamado por main.py como tarea periódica en segundo plano.

    Este módulo NO es async porque main lo ejecuta usando to_thread().
    """

    logger.info("📡 Iniciando evaluación de operaciones activas...")

    positions = get_open_positions()
    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for pos in positions:

        try:
            symbol = pos["symbol"].upper()
            side = pos.get("side", "").lower()

            direction = "long" if side == "buy" else "short"

            entry = float(pos.get("entryPrice") or 0)
            mark = float(pos.get("markPrice") or entry)
            leverage = int(float(pos.get("leverage") or 20))
            pnl = float(pos.get("unrealisedPnl") or 0)

            if entry <= 0:
                logger.warning(f"⚠️ Entrada inválida para posición: {pos}")
                continue

            # 1) ROI
            roi = compute_roi(entry, mark, leverage, direction)
            loss_level = compute_loss_level(roi)

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{leverage} | "
                f"Entry={entry:.6f} Mark={mark:.6f} ROI={roi:.2f}%"
            )

            # No alertar operaciones sanas
            if loss_level is None:
                continue

            # 2) Técnicos multi-TF
            tech = get_technical_data(symbol, intervals=["5m", "15m", "1h"])

            # 3) Recomendación
            suggestion = build_suggestion(direction, tech, roi)

            # 4) Enviar alerta al usuario
            notify_operation_alert(
                symbol=symbol,
                direction=direction,
                roi=roi,
                pnl=pnl,
                loss_level=loss_level,
                volatility="N/A",
                suggestion=suggestion
            )

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")

