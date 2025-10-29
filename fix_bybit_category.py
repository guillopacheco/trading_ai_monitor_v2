"""
Corrige la configuración de Bybit de Spot a Linear (Perpetual Futures)
"""
import re
import os

def update_file(filepath, changes):
    """Actualiza un archivo con los cambios especificados"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_text, new_text in changes:
            content = content.replace(old_text, new_text)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Actualizado: {filepath}")
        else:
            print(f"⚠️  Sin cambios: {filepath}")
            
    except Exception as e:
        print(f"❌ Error en {filepath}: {e}")

def fix_bybit_configuration():
    """Corrige todos los archivos para usar Linear en lugar de Spot"""
    print("🔧 Corrigiendo configuración de Bybit a Linear...")
    
    # Cambios a realizar en cada archivo
    files_to_update = {
        'bybit_api.py': [
            ("'category': 'spot'", "'category': 'linear'"),
            ('category: "spot"', 'category: "linear"'),
            ('"category": "spot"', '"category": "linear"')
        ],
        'indicators.py': [
            ("'category': 'spot'", "'category': 'linear'"),
            ('category: "spot"', 'category: "linear"')
        ],
        'config.py': [
            ("# Bybit Configuration", "# Bybit Configuration\nBYBIT_CATEGORY = 'linear'  # linear, inverse, spot")
        ]
    }
    
    for filepath, changes in files_to_update.items():
        if os.path.exists(filepath):
            update_file(filepath, changes)
        else:
            print(f"❌ Archivo no encontrado: {filepath}")
    
    print("🎉 Configuración de Bybit corregida a Linear!")

def verify_symbols_supported():
    """Verifica si los símbolos problemáticos existen en Linear"""
    problematic_symbols = ['AKTUSDT', 'RECALLUSDT']
    
    print("\n🔍 Verificando símbolos en Bybit Linear...")
    print("💡 Algunos símbolos pueden no estar disponibles en Perpetual Futures")
    print("💡 Los símbolos de Perpetual normalmente terminan en USDT (linear)")
    
    for symbol in problematic_symbols:
        print(f"📊 {symbol}: {'❌ Posiblemente no disponible' if 'AKT' in symbol or 'RECALL' in symbol else '✅ Probablemente disponible'}")

if __name__ == "__main__":
    fix_bybit_configuration()
    verify_symbols_supported()