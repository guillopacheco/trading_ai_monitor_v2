import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from telegram_client import telegram_user_client
from notifier import telegram_notifier
from config import SIGNALS_CHANNEL_ID

async def test_telegram_setup():
    print("🧪 Probando configuración completa de Telegram...")
    
    # Probar cliente de usuario (LECTURA)
    print("1. Probando cliente de USUARIO (para leer señales)...")
    user_ok = await telegram_user_client.connect()
    if user_ok:
        print("   ✅ Cliente de usuario: CONECTADO")
        await telegram_user_client.disconnect()
    else:
        print("   ❌ Cliente de usuario: FALLÓ")
    
    # Probar bot (ESCRITURA)
    print("2. Probando BOT (para enviar resultados)...")
    bot_ok = await telegram_notifier.test_connection()
    if bot_ok:
        print("   ✅ Bot: CONECTADO")
    else:
        print("   ❌ Bot: FALLÓ")
    
    if user_ok and bot_ok:
        print("🎯 Sistema de Telegram COMPLETAMENTE OPERATIVO")
    elif bot_ok:
        print("⚠️  Sistema operativo en MODO SOLO ESCRITURA")
    else:
        print("❌ Sistema de Telegram NO OPERATIVO")

if __name__ == "__main__":
    asyncio.run(test_telegram_setup())
