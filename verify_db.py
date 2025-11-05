import sqlite3
import os
import sys
import logging
from database import init_database

DB_PATH = "trading_ai_monitor.db"
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("verify_db")


def check_table_exists(conn, table_name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def get_table_columns(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name});")
    return [r[1] for r in cur.fetchall()]


def add_missing_column(conn, table_name, column_name, column_def):
    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};")
        logger.info(f"🧩 Añadida columna '{column_name}' en '{table_name}'.")
    except Exception as e:
        logger.error(f"❌ Error agregando columna '{column_name}' en '{table_name}': {e}")


def recreate_table(conn, table_name, ddl):
    try:
        conn.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.execute(ddl)
        conn.commit()
        logger.info(f"🧱 Tabla '{table_name}' recreada correctamente.")
    except Exception as e:
        logger.error(f"❌ Error recreando tabla '{table_name}': {e}")


def verify_database():
    if not os.path.exists(DB_PATH):
        logger.warning("⚠️ No se encontró la base de datos, se creará automáticamente.")
        init_database()
        return

    logger.info(f"🔍 Verificando estructura de '{DB_PATH}'...")
    conn = sqlite3.connect(DB_PATH)

    # Tablas esperadas
    required_tables = ["signals", "operations", "alert_records"]
    for table in required_tables:
        exists = check_table_exists(conn, table)
        logger.info(f"{'✅' if exists else '❌'} Tabla '{table}' {'existe' if exists else 'NO existe'}.")

    # Columna por tabla
    if check_table_exists(conn, "signals"):
        cols = get_table_columns(conn, "signals")
        required_cols = {
            "pair": "TEXT",
            "direction": "TEXT",
            "leverage": "INTEGER DEFAULT 20",
            "entry": "REAL",
            "take_profits": "TEXT",
            "match_ratio": "REAL",
            "recommendation": "TEXT",
            "consistency": "TEXT",
            "divergences": "TEXT",
            "timestamp": "TEXT"
        }
        for name, col_def in required_cols.items():
            if name not in cols:
                add_missing_column(conn, "signals", name, col_def)

    if check_table_exists(conn, "operations"):
        cols = get_table_columns(conn, "operations")
        if "symbol" not in cols:
            logger.error("❌ Falta columna 'symbol' en 'operations'.")

    if check_table_exists(conn, "alert_records"):
        cols = get_table_columns(conn, "alert_records")
        if "symbol" not in cols or "last_alert_level" not in cols:
            logger.error("❌ 'alert_records' incompleta.")
        else:
            logger.info("✅ Tabla 'alert_records' correcta.")

    conn.close()
    logger.info("\n🧩 Verificación completada. Usa '--repair' si hay errores graves.")


def repair_database():
    """Elimina tablas dañadas y las recrea limpias."""
    logger.warning("⚠️ MODO REPARACIÓN ACTIVADO: se eliminarán y recrearán las tablas principales.")
    conn = sqlite3.connect(DB_PATH)

    recreate_table(conn, "signals", """
        CREATE TABLE signals (
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

    recreate_table(conn, "operations", """
        CREATE TABLE operations (
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

    recreate_table(conn, "alert_records", """
        CREATE TABLE alert_records (
            symbol TEXT PRIMARY KEY,
            last_alert_level INTEGER DEFAULT 0,
            last_alert_time TEXT
        )
    """)

    conn.close()
    logger.info("✅ Reparación completa: base de datos recreada sin errores.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--repair":
        repair_database()
    else:
        verify_database()
