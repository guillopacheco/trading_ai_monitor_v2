import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("database")

DB_PATH = "trading_ai_monitor.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row


# ================================================================
# 🧱 Inicialización
# ================================================================
def init_database():
    """Crea las tablas necesarias y repara columnas faltantes."""
    try:
        # Tabla de señales analizadas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT,
                direction TEXT,
                leverage INTEGER DEFAULT 20,
                entry REAL,
                take_profits TEXT,
                match_ratio REAL,
                recommendation TEXT,
                consistency TEXT,
                divergences TEXT,
                timestamp TEXT
            )
        """)

        # Tabla de operaciones activas o evaluadas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                direction TEXT,
                entry_price REAL,
                current_price REAL,
                leverage INTEGER,
                roi REAL,
                status TEXT,
                last_update TEXT
            )
        """)

        # Tabla de alertas persistentes (para tracker)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_records (
                symbol TEXT PRIMARY KEY,
                last_alert_level INTEGER DEFAULT 0,
                last_alert_time TEXT
            )
        """)

        # Migraciones defensivas (por si vienes de versión anterior)
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(signals)")]
        if "consistency" not in columns:
            conn.execute("ALTER TABLE signals ADD COLUMN consistency TEXT")
        if "divergences" not in columns:
            conn.execute("ALTER TABLE signals ADD COLUMN divergences TEXT")

        conn.commit()
        logger.info("✅ Base de datos inicializada correctamente con todas las tablas.")

    except Exception as e:
        logger.error(f"❌ Error al inicializar la base de datos: {e}")


# ================================================================
# 🧾 Gestión de operaciones
# ================================================================
def update_operation_status(symbol, status, roi):
    """Actualiza el estado y ROI de una operación existente."""
    try:
        conn.execute("""
            INSERT INTO operations (symbol, status, roi, last_update)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(symbol) DO UPDATE SET
                status = excluded.status,
                roi = excluded.roi,
                last_update = datetime('now')
        """, (symbol, status, roi))
        conn.commit()
        logger.info(f"💾 Operación actualizada: {symbol} -> {status} ({roi:.2f}%)")
    except Exception as e:
        logger.error(f"❌ Error actualizando operación {symbol}: {e}")


# ================================================================
# ⚙️ Gestión de alertas persistentes
# ================================================================
def get_alert_record(symbol):
    """Obtiene el último nivel y tiempo de alerta registrado para un símbolo."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT last_alert_level, last_alert_time FROM alert_records WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
        if row:
            return {"last_alert_level": row["last_alert_level"], "last_alert_time": row["last_alert_time"]}
        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo registro de alerta {symbol}: {e}")
        return None


def update_alert_record(symbol, level, timestamp):
    """Actualiza o inserta el nivel y hora de la última alerta enviada para un símbolo."""
    try:
        conn.execute("""
            INSERT INTO alert_records (symbol, last_alert_level, last_alert_time)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                last_alert_level = excluded.last_alert_level,
                last_alert_time = excluded.last_alert_time
        """, (symbol, level, timestamp))
        conn.commit()
        logger.debug(f"💾 Registro de alerta actualizado: {symbol} nivel {level} en {timestamp}")
    except Exception as e:
        logger.error(f"❌ Error actualizando registro de alerta {symbol}: {e}")


# ================================================================
# 💾 Guardar señal
# ================================================================
def save_signal(signal: dict):
    """Guarda una señal analizada en la base de datos."""
    try:
        conn.execute("""
            INSERT INTO signals
            (pair, direction, leverage, entry, take_profits, match_ratio, recommendation, consistency, divergences, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("pair"),
            signal.get("direction"),
            signal.get("leverage", 20),
            signal.get("entry"),
            str(signal.get("take_profits", [])),
            signal.get("match_ratio"),
            signal.get("recommendation"),
            signal.get("consistency"),
            str(signal.get("divergences", [])),
            signal.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        ))
        conn.commit()
        logger.info(f"✅ Señal guardada: {signal.get('pair')} | {signal.get('recommendation')}")
    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ================================================================
# 📜 Consultar historial
# ================================================================
def get_signals(limit: int = 10):
    """Obtiene las señales más recientes."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT pair, direction, leverage, entry, take_profits, match_ratio, recommendation, consistency, divergences, timestamp
            FROM signals ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return [
            {
                "pair": row["pair"],
                "direction": row["direction"],
                "leverage": row["leverage"],
                "entry": row["entry"],
                "take_profits": eval(row["take_profits"]) if row["take_profits"] else [],
                "match_ratio": row["match_ratio"],
                "recommendation": row["recommendation"],
                "consistency": row["consistency"],
                "divergences": eval(row["divergences"]) if row["divergences"] else [],
                "timestamp": row["timestamp"],
            } for row in rows
        ]
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial de señales: {e}")
        return []


def get_signals_by_date(start_date: str, end_date: str):
    """Obtiene señales dentro de un rango de fechas."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT pair, direction, leverage, entry, take_profits, match_ratio, recommendation, consistency, divergences, timestamp
            FROM signals
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """, (start_date, end_date))
        rows = cur.fetchall()
        return [
            {
                "pair": row["pair"],
                "direction": row["direction"],
                "leverage": row["leverage"],
                "entry": row["entry"],
                "take_profits": eval(row["take_profits"]) if row["take_profits"] else [],
                "match_ratio": row["match_ratio"],
                "recommendation": row["recommendation"],
                "consistency": row["consistency"],
                "divergences": eval(row["divergences"]) if row["divergences"] else [],
                "timestamp": row["timestamp"],
            } for row in rows
        ]
    except Exception as e:
        logger.error(f"❌ Error consultando señales por fecha: {e}")
        return []


# ================================================================
# 🧹 Limpieza y mantenimiento
# ================================================================
def clear_old_records(days: int = 30):
    """Elimina señales más antiguas de N días."""
    try:
        conn.execute("""
            DELETE FROM signals
            WHERE julianday('now') - julianday(timestamp) > ?
        """, (days,))
        conn.commit()
        logger.info(f"🧹 Registros antiguos (>{days} días) eliminados correctamente.")
    except Exception as e:
        logger.error(f"❌ Error limpiando registros antiguos: {e}")
