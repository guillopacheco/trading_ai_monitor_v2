import sys
print("🧪 Verificando instalación...")

try:
    import pandas
    print("✅ pandas - OK")
except ImportError as e:
    print(f"❌ pandas - FALLÓ: {e}")

try:
    import telegram
    print("✅ python-telegram-bot - OK")
except ImportError as e:
    print(f"❌ python-telegram-bot - FALLÓ: {e}")

try:
    import telethon
    print("✅ telethon - OK")
except ImportError as e:
    print(f"❌ telethon - FALLÓ: {e}")

try:
    import aiohttp
    print("✅ aiohttp - OK")
except ImportError as e:
    print(f"❌ aiohttp - FALLÓ: {e}")

try:
    import scipy
    print("✅ scipy - OK")
except ImportError as e:
    print(f"❌ scipy - FALLÓ: {e}")

print("🎯 Verificación completada!")
