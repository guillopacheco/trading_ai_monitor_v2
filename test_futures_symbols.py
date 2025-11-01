# test_futures_symbols.py
import asyncio
import aiohttp
import logging
from config import BYBIT_API_KEY, BYBIT_API_SECRET

logging.basicConfig(level=logging.INFO)

async def test_futures_symbols():
    """Test para verificar símbolos disponibles en LINEAR"""
    print("🎯 VERIFICANDO SÍMBOLOS EN BYBIT LINEAR (FUTURES)")
    print("=" * 50)
    
    # Símbolos comunes en futures
    test_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "MATICUSDT", "BNBUSDT", "AVAXUSDT", "DOTUSDT"
    ]
    
    async with aiohttp.ClientSession() as session:
        for symbol in test_symbols:
            try:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear", "symbol": symbol}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["retCode"] == 0 and data["result"]["list"]:
                            ticker = data["result"]["list"][0]
                            print(f"✅ {symbol:12} - Precio: {ticker.get('lastPrice', 'N/A')}")
                        else:
                            print(f"❌ {symbol:12} - No disponible en LINEAR")
                    else:
                        print(f"❌ {symbol:12} - Error HTTP: {response.status}")
                        
            except Exception as e:
                print(f"❌ {symbol:12} - Error: {e}")
    
    print(f"\n💡 CONCLUSIÓN: Usa estos símbolos para testing en LINEAR")

if __name__ == "__main__":
    asyncio.run(test_futures_symbols())