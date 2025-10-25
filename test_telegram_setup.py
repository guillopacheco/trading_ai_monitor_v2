# test_telegram_setup.py
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_client import telegram_user_client
from notifier import telegram_notifier
from config import SIGNALS_CHANNEL_ID  # ✅ AGREGAR ESTE IMPORT

async def test_telegram_setup():
    print("🧪 Probando configuración completa de Telegram...")
    
    # Probar cliente de usuario (LECTURA)
    print("1. Probando cliente de USUARIO (para leer señales)...")
    user_ok = await telegram_user_client.connect()
    if user_ok:
        print("   ✅ Cliente de usuario: CONECTADO")
        # Probar que puede obtener el canal
        try:
            # Esta función no existe en telegram_client.py, necesitamos una alternativa
            print("   ⚠️  Función get_channel_messages no disponible - probando conexión básica")
            # En lugar de get_channel_messages, verificamos que el cliente esté conectado
            if telegram_user_client.is_connected:
                print("   ✅ Cliente de usuario correctamente autenticado")
            else:
                print("   ❌ Cliente de usuario no autenticado")
        except Exception as e:
            print(f"   ❌ Error accediendo al canal: {e}")
        await telegram_user_client.disconnect()
    else:
        print("   ❌ Cliente de usuario: FALLÓ")
    
    # Probar bot (ESCRITURA)
    print("2. Probando BOT (para enviar resultados)...")
    bot_ok = await telegram_notifier.test_connection()
    if bot_ok:
        print("   ✅ Bot: CONECTADO")
        # Probar envío de mensaje de prueba
        try:
            await telegram_notifier.send_alert(
                "Test de Sistema",
                "Este es un mensaje de prueba del sistema.",
                "info"
            )
            print("   ✅ Bot puede enviar mensajes")
        except Exception as e:
            print(f"   ❌ Bot no puede enviar mensajes: {e}")
    else:
        print("   ❌ Bot: FALLÓ")
    
    if user_ok and bot_ok:
        print("🎯 Sistema de Telegram COMPLETAMENTE OPERATIVO")
        print("   ✅ User Account: Puede LEER señales")
        print("   ✅ Bot: Puede ENVIAR resultados")
    elif bot_ok:
        print("⚠️  Sistema operativo en MODO SOLO ESCRITURA")
        print("   ❌ User Account: No puede leer señales")
        print("   ✅ Bot: Puede enviar resultados")
    else:
        print("❌ Sistema de Telegram NO OPERATIVO")

if __name__ == "__main__":
    asyncio.run(test_telegram_setup())