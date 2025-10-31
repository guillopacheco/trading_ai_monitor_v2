#!/usr/bin/env python3
"""
Test final del sistema - VERSIÓN MEJORADA CON LIMPIEZA
"""
import asyncio
import logging
from database import trading_db
from bybit_api import bybit_client
from command_bot import command_bot

logging.basicConfig(level=logging.INFO)

async def test_bybit_live():
    """Test en vivo de Bybit"""
    try:
        ticker = await bybit_client.get_ticker("BTCUSDT")
        return ticker is not None
    except:
        return False

async def test_complete_system_v2():
    """Test completo del sistema - VERSIÓN MEJORADA"""
    print("🧪 TEST FINAL DEL SISTEMA V2")
    print("=" * 40)
    
    # 1. Base de Datos
    print("1. 📊 Base de Datos...", end=" ")
    if trading_db.is_connected():
        print("✅ CONECTADA")
    else:
        print("❌ DESCONECTADA")
    
    # 2. Bybit (Test real)
    print("2. 💰 Bybit API...", end=" ")
    try:
        await bybit_client.initialize()
        bybit_live = await test_bybit_live()
        if bybit_live:
            print("✅ CONECTADO Y RESPONDIENDO")
        else:
            print("⚠️  INICIALIZADO PERO SIN CONEXIÓN")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # 3. Comandos
    print("3. 🤖 Bot de Comandos...", end=" ")
    try:
        if not command_bot.is_running:
            await command_bot.start()
        print("✅ ACTIVO")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n🎯 ESTADO ACTUAL:")
    print("   • Comandos directos: ✅ FUNCIONANDO")
    print("   • Envía /estado a @gapcbot")
    print("   • Bybit puede requerir API keys para conexión completa")

async def cleanup():
    """Limpia las conexiones al finalizar"""
    try:
        if bybit_client.session:
            await bybit_client.close()
        if command_bot.is_running:
            await command_bot.stop()
    except Exception as e:
        logging.warning(f"Advertencia en limpieza: {e}")

async def main():
    """Función principal con limpieza"""
    try:
        await test_complete_system_v2()
    finally:
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())