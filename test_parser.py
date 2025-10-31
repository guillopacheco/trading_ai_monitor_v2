# test_parser.py
import asyncio
from helpers import parse_signal_message

def test_parser():
    """Prueba el parser con diferentes formatos de señales"""
    
    test_signals = [
        # Formato 1
        """
🔥 **#BTCUSDT** (Long📈, x20) 🔥
**Entry** - 65000.50
**Stop-Loss** - 64500.25
**Take-Profit:** 65500.75, 66001.00, 66501.25
""",
        # Formato 2  
        """
🎯 **#ETHUSDT** SHORT 🎯
ENTRY: 3500.25
LEVERAGE: 15x
TP: 3450.20, 3400.15, 3350.10
SL: 3550.30
""",
        # Formato 3
        """
🚀 #ADAUSDT LONG
Entry: 0.45
Leverage: 25x
Take Profit: 0.46, 0.47, 0.48
Stop Loss: 0.44
"""
    ]
    
    for i, signal_text in enumerate(test_signals, 1):
        print(f"\n🔍 Probando señal {i}:")
        print("Texto:", signal_text[:100] + "...")
        
        result = parse_signal_message(signal_text)
        if result:
            print("✅ Parseada correctamente:")
            print(f"   Par: {result['pair']}")
            print(f"   Dirección: {result['direction']}") 
            print(f"   Entry: {result['entry']}")
            print(f"   Leverage: {result.get('leverage', 'N/A')}")
        else:
            print("❌ No se pudo parsear")

if __name__ == "__main__":
    test_parser()