# update_database.py
import sqlite3
import os
from config import DATABASE_PATH

def update_database():
    """Actualiza la base de datos con la nueva columna leverage"""
    try:
        print("🔄 Actualizando base de datos...")
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Verificar si la columna leverage existe
            cursor.execute("PRAGMA table_info(signals)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'leverage' not in columns:
                print("✅ Agregando columna 'leverage' a la tabla signals...")
                cursor.execute('''
                    ALTER TABLE signals ADD COLUMN leverage INTEGER DEFAULT 20
                ''')
                conn.commit()
                print("✅ Columna 'leverage' agregada correctamente")
            else:
                print("✅ Columna 'leverage' ya existe")
            
            # Verificar otras columnas necesarias
            required_columns = ['tp1', 'tp2', 'tp3', 'tp4']
            for col in required_columns:
                if col not in columns:
                    print(f"✅ Agregando columna '{col}'...")
                    cursor.execute(f'''
                        ALTER TABLE signals ADD COLUMN {col} REAL
                    ''')
            
            conn.commit()
            print("🎉 Base de datos actualizada correctamente")
            
    except Exception as e:
        print(f"❌ Error actualizando base de datos: {e}")

if __name__ == "__main__":
    update_database()