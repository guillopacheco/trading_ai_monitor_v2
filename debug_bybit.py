"""
Debug para verificar el estado real de los pares en Bybit
"""
import asyncio
import requests
from indicators import indicators_calculator

def debug_symbol(symbol: str):
    """Debug individual de un símbolo"""
    print(f"\n🔍 Debugging {symbol}:")
    
    # 1. Probar endpoint directo de Bybit
    url = "https://api.bybit.com/v5/market/tickers"
    params = {
        "category": "linear",
        "symbol": symbol
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        print(f"📊 API Response - RetCode: {data.get('retCode')}")
        print(f"📝 API Message: {data.get('retMsg')}")
        
        if data['retCode'] == 0:
            ticker = data['result']['list'][0] if data['result']['list'] else None
            if ticker:
                print(f"✅ Ticker encontrado:")
                print(f"   Last Price: {ticker.get('lastPrice')}")
                print(f"   Volume: {ticker.get('volume24h')}")
                print(f"   Change: {ticker.get('price24hPcnt')}%")
            else:
                print("❌ No hay datos del ticker")
        else:
            print("❌ Error en API response")
            
    except Exception as e:
        print(f"💥 Error en API call: {e}")
    
    # 2. Probar con el indicador
    print(f"\n📈 Probando con indicators.py:")
    try:
        ohlcv_data = indicators_calculator.get_ohlcv_data(symbol, "1", 10)
        if ohlcv_data is not None:
            print(f"✅ OHLCV data obtenida - {len(ohlcv_data)} velas")
            print(f"   Último close: {ohlcv_data['close'].iloc[-1]}")
        else:
            print("❌ No se pudo obtener OHLCV data")
    except Exception as e:
        print(f"💥 Error en indicators: {e}")

async def main():
    print("🚀 Iniciando debug de pares Bybit...")
    
    # Pares problemáticos
    problematic_pairs = ['AKTUSDT', 'RECALLUSDT']
    
    # Pares de control (que sabemos que funcionan)
    control_pairs = ['BTCUSDT', 'ETHUSDT']
    
    print("=== PARES PROBLEMÁTICOS ===")
    for pair in problematic_pairs:
        debug_symbol(pair)
    
    print("\n=== PARES DE CONTROL ===")
    for pair in control_pairs:
        debug_symbol(pair)
    
    print("\n🎯 CONCLUSIÓN:")
    print("• Si los pares problemáticos fallan pero los de control funcionan:")
    print("  → Los pares pueden ser muy nuevos o tener problemas en la API")
    print("• Si todos fallan:")
    print("  → Problema de configuración general de Bybit")
    print("• Si todos funcionan:")
    print("  → El problema era temporal y ya está resuelto")

if __name__ == "__main__":
    asyncio.run(main())