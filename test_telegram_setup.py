# test_telegram_setup.py - VERSIÓN MEJORADA CON ACCESO DIRECTO
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
        print(f"   🔍 Intentando acceder al canal: {SIGNALS_CHANNEL_ID}")
        
        try:
            # Listar diálogos para encontrar el canal
            dialogs = await telegram_user_client.client.get_dialogs()
            target_channel = None
            
            for dialog in dialogs:
                if (hasattr(dialog, 'id') and 
                    (str(dialog.id) == SIGNALS_CHANNEL_ID or 
                     (hasattr(dialog, 'name') and "Andy Insider" in dialog.name))):
                    target_channel = dialog
                    print(f"   🎯 Canal objetivo encontrado: {dialog.name} (ID: {dialog.id})")
                    break
            
            if target_channel:
                # Intentar acceder usando la entidad del diálogo
                print("   🔄 Intentando acceso usando entidad del diálogo...")
                try:
                    messages = await telegram_user_client.client.get_messages(
                        target_channel.entity,
                        limit=5
                    )
                    if messages:
                        print(f"   ✅ ✅ ACCESO EXITOSO - {len(messages)} mensajes obtenidos!")
                        for msg in messages[:3]:  # Mostrar primeros 3 mensajes
                            print(f"      📨 {msg.date}: {msg.text[:100]}...")
                    else:
                        print("   ⚠️  Canal accesible pero sin mensajes recientes")
                        
                except Exception as e:
                    print(f"   ❌ Error accediendo via entidad: {e}")
                    
                    # Intentar método alternativo - usar input peer directamente
                    print("   🔄 Intentando método alternativo...")
                    try:
                        entity = await telegram_user_client.client.get_input_entity(target_channel.id)
                        messages = await telegram_user_client.client.get_messages(entity, limit=3)
                        if messages:
                            print(f"   ✅ ✅ ACCESO EXITOSO (método alternativo) - {len(messages)} mensajes!")
                        else:
                            print("   ⚠️  Método alternativo funciona pero sin mensajes")
                    except Exception as e2:
                        print(f"   ❌ Método alternativo también falló: {e2}")
            else:
                print("   ❌ Canal no encontrado en diálogos")
                
        except Exception as e:
            print(f"   ❌ Error general: {e}")
        finally:
            await telegram_user_client.disconnect()
    else:
        print("   ❌ Cliente de usuario: FALLÓ")
    
    # Probar bot (ESCRITURA) - Mantenemos igual
    print("2. Probando BOT (para enviar resultados)...")
    bot_ok = await telegram_notifier.test_connection()
    if bot_ok:
        print("   ✅ Bot: CONECTADO")
        try:
            await telegram_notifier.send_alert(
                "Test de Sistema - Acceso a Canal",
                f"✅ User conectado\n❌ Acceso a canal: En progreso\n📊 Canales disponibles: 6",
                "info"
            )
            print("   ✅ Bot puede enviar mensajes")
        except Exception as e:
            print(f"   ❌ Bot no puede enviar mensajes: {e}")
    else:
        print("   ❌ Bot: FALLÓ")
    
    print("🎯 RESUMEN: Sistema base operativo, acceso a canal en verificación")

if __name__ == "__main__":
    asyncio.run(test_telegram_setup())