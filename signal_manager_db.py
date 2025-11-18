"""
signal_manager_db.py
------------------------------------------------------------
Capa de acceso a base de datos para:
- Señales almacenadas en la tabla `signals`
- Reactivación de señales (estado / filtros)

Usa:
- config.DATABASE_PATH
- Tabla `signals` creada en database.py:

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT,
    direction TEXT,
    leverage INTEGER,
    entry REAL,
    take_profits TEXT,
    match_ratio REAL,
    recommendation TEXT,
    timestamp TEXT,
    status TEXT DEFAULT 'pending'

------------------------------------------------------------
"""

import sqlite3
import logging
from typing import List, Dict, Any

from config import DATABASE_PATH
from database import save_signal


logger = logging.getLogger("signal_manager_db")


# ============================================================
# 🔌 Conexión básica
# ============================================================
def _connect():
    return sqlite3.connect(DATABASE_PATH)


# ============================================================
# 📥 Obtención de señales pendientes para reactivación
# ============================================================
def get_pending_signals_for_reactivation(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Devuelve una lista de señales pendientes de reactivación desde la tabla `signals`.

    Mapea columnas a claves usadas por signal_reactivation_sync:
      - symbol  ← pair
      - direction
      - leverage
      - entry_price ← entry
      - id
    """
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
                pair AS symbol,
                direction,
                leverage,
                entry AS entry_price,
                status
            FROM signals
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cur.fetchall()
        signals: List[Dict[str, Any]] = []

        for r in rows:
            signals.append(
                {
                    "id": r["id"],
                    "symbol": r["symbol"],
                    "direction": r["direction"],
                    "leverage": r["leverage"],
                    "entry_price": r["entry_price"],
                    "status": r["status"],
                }
            )

        logger.info(f"📡 {len(signals)} señales pendientes cargadas desde DB para reactivación.")
        return signals

    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes para reactivación: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ============================================================
# 🔄 Marcar una señal como reactivada
# ============================================================
def mark_signal_reactivated(signal_id: int) -> None:
    """
    Marca una señal como reactivada en la tabla `signals`.

    Usamos solo la columna `status` (no existen columnas extra como
    `reactivated`, `reactivated_at`, etc. en tu esquema actual).
    """
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE signals
            SET status = 'reactivated'
            WHERE id = ?
            """,
            (signal_id,),
        )
        conn.commit()

        logger.info(f"✅ Señal {signal_id} marcada como REACTIVATED en la DB.")

    except Exception as e:
        logger.error(f"❌ Error actualizando señal {signal_id} como reactivada: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
