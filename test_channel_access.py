# test_channel_access.py - TEST ESPECÍFICO PARA ACCESO A CANALES
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_channel_access():
    print("🔍 DIAGNÓSTICO COMPLETO DE ACCESO A CANALES")
    print("=" * 60)
    
    from telegram_client import telegram_user_client
    from config import SIGNALS_CHANNEL_ID
    
    # Conectar cliente
    print("1. Conectando cliente...")
    if not await telegram_user_client.connect():
        print("   ❌ No se pudo conectar")
        return
    
    print("   ✅ Cliente conectado")
    
    # Listar canales disponibles
    print("\n2. Canales disponibles:")
    available_channels = await telegram_user_client.get_available_channels()
    for i, channel in enumerate(available_channels[:10], 1):  # Mostrar primeros 10
        print(f"   {i}. {channel['name']} (ID: {channel['id']})")
    
    if len(available_channels) > 10:
        print(f"   ... y {len(available_channels) - 10} más")
    
    # Testear acceso al canal específico
    print(f"\n3. Testeando acceso a canal objetivo: {SIGNALS_CHANNEL_ID}")
    access_test = await telegram_user_client.test_channel_access(SIGNALS_CHANNEL_ID)
    
    if access_test['accessible']:
        print("   ✅ ✅ ACCESO EXITOSO!")
        print(f"      Canal: {access_test['channel_info']['name']}")
        print(f"      Mensajes obtenidos: {access_test['message_count']}")
        
        # Mostrar mensajes recientes
        messages = await telegram_user_client.get_channel_messages(SIGNALS_CHANNEL_ID, limit=3)
        print(f"\n4. Mensajes recientes:")
        for i, msg in enumerate(messages, 1):
            print(f"   {i}. {msg.date}: {msg.text[:100]}...")
            
    else:
        print("   ❌ ACCESO FALLIDO")
        print(f"      Error: {access_test['error']}")
        
        # Sugerencias
        print(f"\n💡 SUGERENCIAS:")
        print("   • Verifica que el usuario esté agregado al canal")
        print("   • Prueba con el nombre del canal en lugar del ID")
        print("   • Usa uno de los canales disponibles de la lista arriba")
        
        # Mostrar canales que contengan "Andy"
        andy_channels = [c for c in available_channels if 'andy' in c['name'].lower()]
        if andy_channels:
            print(f"\n   Canales con 'Andy' encontrados:")
            for channel in andy_channels:
                print(f"      • {channel['name']} (ID: {channel['id']})")
                print(f"        💡 Usa este ID en config.py: {channel['id']}")

    await telegram_user_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_channel_access())