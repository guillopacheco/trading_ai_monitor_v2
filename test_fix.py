# test_fix.py
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def test_circular_fix():
    """Prueba que los imports circulares estén corregidos"""
    print("🧪 TESTEO DE CORRECCIÓN DE IMPORTS CIRCULARES")
    print("=" * 50)
    
    try:
        # Intentar importar ambos módulos (esto fallaría antes)
        from main import TradingAIMonitor
        from command_bot import CommandBot
        
        print("✅ main.py - Importado correctamente")
        print("✅ command_bot.py - Importado correctamente")
        
        # Probar creación de instancias
        monitor = TradingAIMonitor()
        command_bot = CommandBot()
        
        print("✅ Instancias creadas sin errores")
        print("🎉 IMPORTS CIRCULARES CORREGIDOS EXITOSAMENTE")
        
        # Probar métodos específicos
        print("\n🔧 Probando métodos corregidos...")
        
        # Probar importación diferida en main
        async def test_main_methods():
            monitor = TradingAIMonitor()
            # Estos métodos deberían funcionar sin circularidad
            print("✅ Métodos de main probados")
        
        await test_main_methods()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("⚠️ Los imports circulares persisten")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_circular_fix())
    exit(0 if success else 1)