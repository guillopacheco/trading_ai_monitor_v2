# fix_database.py
import sqlite3
from database import trading_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_metadata_column():
    """Agrega la columna metadata faltante a la tabla signals"""
    try:
        with sqlite3.connect(trading_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Verificar si la columna ya existe
            cursor.execute("PRAGMA table_info(signals)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'metadata' not in columns:
                # Agregar columna metadata
                cursor.execute('''
                    ALTER TABLE signals 
                    ADD COLUMN metadata TEXT
                ''')
                conn.commit()
                logger.info("✅ Columna 'metadata' agregada a la tabla signals")
            else:
                logger.info("✅ Columna 'metadata' ya existe")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Error agregando columna metadata: {e}")
        return False

def test_fix():
    """Prueba que el fix funcione"""
    print("🔧 APLICANDO FIX DE BASE DE DATOS")
    print("=" * 40)
    
    success = add_metadata_column()
    
    if success:
        print("✅ Base de datos corregida exitosamente")
        print("🗄️  Columna 'metadata' disponible para uso")
    else:
        print("❌ Error corrigiendo base de datos")
    
    return success

if __name__ == "__main__":
    test_fix()