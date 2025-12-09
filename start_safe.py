# start_safe.py
#!/usr/bin/env python3
"""
Script de arranque seguro que asegura la carga de .env
antes de importar cualquier módulo.
"""
import os
import sys

# 1. Asegurar que estamos en el directorio correcto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
print(f"📂 Directorio de trabajo: {SCRIPT_DIR}")

# 2. Cargar .env PRIMERO, ANTES de cualquier import
from dotenv import load_dotenv
load_dotenv(override=True)

# 3. Verificar variables críticas
required_vars = ["BYBIT_API_KEY", "BYBIT_API_SECRET", "TELEGRAM_BOT_TOKEN"]
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ Variables faltantes: {missing}")
    print("   Verifica tu archivo .env")
    sys.exit(1)

print("✅ Todas las variables requeridas están configuradas")

# 4. AHORA importar y ejecutar main
print("🚀 Iniciando Trading AI Monitor v2...")
from main import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Detenido por usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()