"""
signal_manager_db.py — Módulo oficial para gestionar señales en SQLite
-----------------------------------------------------------------------

Compatible con:
- telegram_reader.py (save_signal)
- signal_reactivation_sync.py
- database.py

Columnas usadas en tabla `signals`:
    id INTEGER PRIMARY KEY
    symbol TEXT
    direction TEXT
    leverage INTEGER
    entry_price REAL
    take_profits TEXT (csv)
    match_ratio REAL
    status TEXT ('pending', 'reactivated', 'ignored')
    created_at TEXT
    reactivated_at TEXT
"""

import sqlite3
import logging
from datetime import datetime
from database import get_connection
import json

logger = logging.getLogger("signal_manager_db")


# ------------------------------------------------------------
# 📌 Obtener señales pendientes para reactivación
# ------------------------------------------------------------
def get_pending_signals_for_reactivation():
    """
    Devuelve señales con:
    - status='pending'
    - entry_price != NULL
    """

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price,
                   take_profits, created_at
            FROM signals
            WHERE status = 'pending'
              AND entry_price IS NOT NULL
            ORDER BY created_at ASC
        """)

        rows = cur.fetchall()

        signals = []
        for r in rows:
            signals.append({
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "leverage": r[3],
                "entry_price": r[4],
                "take_profits": r[5].split(",") if r[5] else [],
                "created_at": r[6],
            })

        return signals

    except Exception as e:
        logger.error(f"❌ Error obteniendo señales pendientes: {e}")
        return []


# ------------------------------------------------------------
# 📌 Marcar señal como reactivada
# ------------------------------------------------------------
def mark_signal_reactivated(signal_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status = 'reactivated',
                reactivated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), signal_id))

        conn.commit()

        logger.info(f"♻️ Señal {signal_id} marcada como reactivada.")

    except Exception as e:
        logger.error(f"❌ Error en mark_signal_reactivated: {e}")


# ------------------------------------------------------------
# 📌 Marcar señal como NO reactivada
# ------------------------------------------------------------
def mark_signal_not_reactivated(signal_id: int, reason: str = "", extra: dict = None):
    """
    Cambia la señal a 'ignored' y registra un log opcional.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status = 'ignored'
            WHERE id = ?
        """, (signal_id,))
        conn.commit()

        # Log opcional
        try:
            details = ""
            if reason:
                details += f"reason={reason}; "
            if extra:
                details += f"extra={extra}; "

            cur.execute("""
                INSERT INTO signal_analysis_log (signal_id, match_ratio, recommendation, details)
                VALUES (?, ?, ?, ?)
            """, (signal_id, None, "ignored", details))
            conn.commit()

        except Exception as e2:
            logger.error(f"⚠️ Error guardando log de ignorar señal: {e2}")

        logger.info(f"⏳ Señal {signal_id} marcada como NO reactivada.")

    except Exception as e:
        logger.error(f"❌ Error en mark_signal_not_reactivated: {e}")


# ------------------------------------------------------------
# 📌 Actualizar match_ratio
# ------------------------------------------------------------
def update_signal_match_ratio(signal_id: int, match_ratio: float):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET match_ratio = ?
            WHERE id = ?
        """, (match_ratio, signal_id))

        conn.commit()

    except Exception as e:
        logger.error(f"❌ Error en update_signal_match_ratio: {e}")


# ------------------------------------------------------------
# 📌 Guardar log de análisis
# ------------------------------------------------------------

def save_analysis_log(signal_id: int, match_ratio: float, recommendation, details=None):
    """
    Guarda un registro del análisis técnico de una señal.
    - recommendation puede ser str o dict
    - details puede ser str, dict, list o None
    """

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Convertir recommendation si es dict
        if isinstance(recommendation, (dict, list)):
            rec_str = json.dumps(recommendation, ensure_ascii=False)
        else:
            rec_str = str(recommendation)

        # Convertir details si es dict/list
        if isinstance(details, (dict, list)):
            details_str = json.dumps(details, ensure_ascii=False)
        elif details is None:
            details_str = ""
        else:
            details_str = str(details)

        cur.execute("""
            INSERT INTO signal_analysis_log (signal_id, match_ratio, recommendation, details)
            VALUES (?, ?, ?, ?)
        """, (
            signal_id,
            match_ratio,
            rec_str,       # ✔ recommendation string
            details_str    # ✔ details string
        ))

        conn.commit()

    except Exception as e:
        logger.error(f"❌ Error guardando en signal_analysis_log: {e}")

# ------------------------------------------------------------
# 📌 Guardar una señal nueva (usado por telegram_reader)
# ------------------------------------------------------------
def save_signal(data: dict):
    """
    Inserta una nueva señal en la tabla 'signals'.
    data = {
        "symbol": str,
        "direction": str,
        "entry_price": float,
        "take_profits": list,
        "leverage": int,
        "recommendation": str,
        "match_ratio": float,
    }
    """

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals
            (symbol, direction, leverage, entry_price, take_profits, match_ratio, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            data["symbol"],
            data["direction"],
            data.get("leverage", 20),
            data["entry_price"],
            ",".join(str(tp) for tp in data.get("take_profits", []) if tp is not None),
            data.get("match_ratio", 0.0),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        logger.info(f"💾 Señal guardada: {data['symbol']} ({data['direction']})")

    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")
