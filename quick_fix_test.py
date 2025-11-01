# quick_fix_test.py
import asyncio
import logging
from helpers import parse_signal_message

logging.basicConfig(level=logging.INFO)

def test_parser_fix():
    """Prueba que el parser genere símbolos correctos"""
    print("🔧 TEST DE CORRECCIÓN DEL PARSER")
    print("=" * 40)
    
    test_signals = [
        "🔥 #BTCUSDT LONG Entry: 50000",
        "🎯 #ETHUSDT SHORT Price: 3500", 
        "⚡ #ADA LONG 0.45",
        "📈 #SOLUSDT BUY 150.00"
    ]
    
    for signal in test_signals:
        parsed = parse_signal_message(signal)
        if parsed:
            symbol = parsed['pair']
            status = "✅" if symbol.endswith('USDT') and symbol.count('USDT') == 1 else "❌"
            print(f"{status} {signal[:30]:30} -> {symbol}")
        else:
            print(f"❌ {signal[:30]:30} -> No parseado")
    
    return True

if __name__ == "__main__":
    test_parser_fix()