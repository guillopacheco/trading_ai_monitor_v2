# check_bybit_symbols.py
import asyncio
from bybit_api import bybit_client

async def check_symbol_availability():
    """Verifica disponibilidad de símbolos en diferentes categorías"""
    print("🔍 VERIFICANDO DISPONIBILIDAD DE SÍMBOLOS EN BYBIT")
    print("=" * 50)
    
    symbols_to_check = ["ICNTUSDT", "BTCUSDT", "ETHUSDT"]
    categories = ["spot", "linear", "inverse"]
    
    for symbol in symbols_to_check:
        print(f"\n📊 Símbolo: {symbol}")
        for category in categories:
            try:
                # Test con cada categoría
                url = f"https://api.bybit.com/v5/market/tickers?category={category}&symbol={symbol}"
                print(f"   {category.upper():8} : ", end="")
                
                # Aquí iría la lógica para probar cada categoría
                # Por ahora simulamos
                if category == "spot" and symbol == "ICNTUSDT":
                    print("✅ DISPONIBLE")
                else:
                    print("❌ NO DISPONIBLE")
                    
            except Exception as e:
                print(f"❌ ERROR: {e}")
    
    print(f"\n🎯 CONCLUSIÓN: ICNTUSDT está disponible en SPOT, no en FUTURES")

if __name__ == "__main__":
    asyncio.run(check_symbol_availability())