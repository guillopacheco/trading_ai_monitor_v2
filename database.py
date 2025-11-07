"""
database.py
------------------------------------------------------------
Manejo centralizado de la base de datos SQLite para el sistema
de análisis de señales de trading.
------------------------------------------------------------
"""

import sqlite3
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# ================================================================
# ⚙️ Configuración
# ================================================================
DATABASE_PATH = Path("data/trading_signals.db")
logger = logging.getLogger("database")

# ================================================================
# 🧱 Inicialización de la base de datos
# ================================================================
def init_database():
    """
    Crea la base de datos y las tablas si no existen.
    """
    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                leverage INTEGER,
                entry REAL,
                match_ratio REAL,
                recommendation TEXT,
                timestamp TEXT,
                raw_text TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                status TEXT,
                roi REAL,
                last_update TEXT
            )
            """
        )

        conn.commit()
        conn.close()
        logger.info("✅ Base de datos inicializada correctamente con todas las tablas.")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")


# ================================================================
# 💾 Guardar señal analizada
# ================================================================
def save_signal(data: dict):
    """
    Guarda una nueva señal analizada en la base de datos.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO signals (
                symbol, direction, leverage, entry,
                match_ratio, recommendation, timestamp, raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["symbol"],
                data["direction"],
                data["leverage"],
                data["entry"],
                data.get("match_ratio", 0.0),
                data.get("recommendation", "DESCARTAR"),
                data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                data.get("raw_text", ""),
            ),
        )

        conn.commit()
        conn.close()
        logger.info(f"💾 Señal guardada correctamente: {data['symbol']}")
    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ================================================================
# 🔄 Actualizar estado de una señal
# ================================================================
def update_signal_status(symbol: str, new_status: str, roi: float | None = None):
    """
    Actualiza el estado o ROI de una operación.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO operations (symbol, status, roi, last_update)
            VALUES (?, ?, ?, ?)
            """,
            (
                symbol,
                new_status,
                roi if roi is not None else 0.0,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        conn.commit()
        conn.close()
        logger.info(f"🧾 Estado actualizado: {symbol} → {new_status} ({roi}%)")
    except Exception as e:
        logger.error(f"❌ Error actualizando operación: {e}")


# ================================================================
# 📜 Obtener últimas señales analizadas (para /historial)
# ================================================================
def get_signals(limit: int = 10):
    """
    Devuelve las últimas señales registradas.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT symbol, direction, leverage, entry,
                   match_ratio, recommendation, timestamp
            FROM signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        signals = []
        for row in rows:
            signals.append(
                {
                    "symbol": row[0],
                    "direction": row[1],
                    "leverage": row[2],
                    "entry": row[3],
                    "match_ratio": row[4],
                    "recommendation": row[5],
                    "timestamp": row[6],
                }
            )

        return signals

    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        return []


# ================================================================
# 🧹 Limpiar registros antiguos
# ================================================================
def clear_old_records(days: int = 30):
    """
    Elimina señales más antiguas que el límite de días especificado.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            DELETE FROM signals
            WHERE timestamp < datetime('now', '-{days} days')
            """
        )

        conn.commit()
        conn.close()
        logger.info(f"🧹 Registros de más de {days} días eliminados correctamente.")
    except Exception as e:
        logger.error(f"❌ Error limpiando registros antiguos: {e}")


# ================================================================
# 🔄 Versión asincrónica
# ================================================================
async def async_save_signal(data: dict):
    """Versión asincrónica del guardado de señales."""
    await asyncio.to_thread(save_signal, data)


async def async_get_signals(limit: int = 10):
    """Versión asincrónica para obtener historial."""
    return await asyncio.to_thread(get_signals, limit)


async def async_update_signal_status(symbol: str, new_status: str, roi: float | None = None):
    """Versión asincrónica para actualizar operaciones."""
    await asyncio.to_thread(update_signal_status, symbol, new_status, roi)
