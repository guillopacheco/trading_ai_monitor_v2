"""
database.py — FASE 2 (2025)
Base de datos oficial del Trading AI Monitor.
Compatible con:
 - signal_service
 - signal_reactivation_sync
 - command_bot
 - application_layer
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("database")

DB_PATH = "trading_ai_monitor.db"


# ============================================================
# 🔧 Conexión segura
# ============================================================

def _conn():
    """Conexión segura con soporte multihilo."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ============================================================
# 🏗️ Inicializar DB
# ============================================================

def init_db():
    """Crea tablas necesarias."""

    try:
        conn = _conn()
        cur = conn.cursor()

        # Tabla de señales
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                leverage INTEGER DEFAULT 20,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reactivated_at TEXT,
                status TEXT DEFAULT 'pending'
            );
        """)

        # Historial de análisis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signal_analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                match_ratio REAL,
                recommendation TEXT,
                details TEXT
            );
        """)

        conn.commit()
        conn.close()

        logger.info("✅ Base de datos inicializada correctamente.")

    except Exception as e:
        logger.error(f"❌ Error inicializando DB: {e}")


# ============================================================
# 💾 Guardar señal nueva
# ============================================================

def db_insert_signal(symbol: str, direction: str, entry_price: float | None = None):
    """Guarda una señal recibida del canal VIP."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals (symbol, direction, entry_price)
            VALUES (?, ?, ?)
        """, (symbol, direction, entry_price))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error guardando señal nueva: {e}")


# ============================================================
# ♻️ Obtener señales pendientes
# ============================================================

def db_get_pending_signals():
    """Devuelve una lista de señales con estado = 'pending'."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, entry_price, status
            FROM signals
            WHERE status = 'pending'
        """)

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "entry_price": r[3],
                "status": r[4],
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return []


# ============================================================
# 🔄 Actualizar estado de señal
# ============================================================

def db_update_signal_status(symbol: str, status: str):
    """Actualiza estado: pending | reactivated."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status = ?, reactivated_at = ?
            WHERE symbol = ?
        """, (status, datetime.utcnow().isoformat(), symbol))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error actualizando estado de señal: {e}")


# ============================================================
# 📝 Guardar log detallado
# ============================================================

def db_save_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: str = ""):
    """Guarda un análisis técnico detallado."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signal_analysis_log (signal_id, match_ratio, recommendation, details)
            VALUES (?, ?, ?, ?)
        """, (signal_id, match_ratio, recommendation, details))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error guardando análisis detallado: {e}")


# ============================================================
# 📜 Obtener historial (/historial)
# ============================================================

def db_get_signals(limit: int = 50):
    """Devuelve las señales más recientes."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, entry_price,
                   leverage, status, created_at, reactivated_at
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "entry_price": r[3],
                "leverage": r[4],
                "status": r[5],
                "created_at": r[6],
                "reactivated_at": r[7],
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        return []


# ============================================================
# 🧹 Limpieza automática
# ============================================================

def db_clear_old(days: int = 30):
    """Elimina señales antiguas."""

    try:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM signals
            WHERE julianday('now') - julianday(created_at) > ?
        """, (days,))

        conn.commit()
        conn.close()

        logger.info(f"🧹 Limpieza realizada: señales > {days} días eliminadas.")

    except Exception as e:
        logger.error(f"❌ Error en limpieza automática: {e}")
