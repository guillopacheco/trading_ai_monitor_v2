"""
Verifica y corrige la configuración de Bybit
"""
import os

def check_file_configuration():
    """Verifica la configuración actual de cada archivo"""
    print("🔍 Verificando configuración actual de Bybit...")
    
    files_to_check = ['bybit_api.py', 'indicators.py', 'config.py']
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            print(f"\n📁 {filepath}:")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Buscar patrones de category
                import re
                category_patterns = [
                    r"category.*=.*['\"](spot|linear|inverse)['\"]",
                    r"['\"](spot|linear|inverse)['\"].*category"
                ]
                
                for pattern in category_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            status = "✅ LINEAR" if match.lower() == "linear" else "❌ NEEDS FIX" if match.lower() == "spot" else "⚠️  CHECK"
                            print(f"   {status}: Encontrado '{match}'")
                
                # Si no se encontraron patrones, mostrar líneas con "category"
                if not any(matches for pattern in category_patterns for matches in [re.findall(pattern, content)]):
                    lines_with_category = [line.strip() for line in content.split('\n') if 'category' in line.lower()]
                    if lines_with_category:
                        print("   📝 Líneas con 'category':")
                        for line in lines_with_category[:3]:  # Mostrar máximo 3 líneas
                            print(f"      {line}")
                    
            except Exception as e:
                print(f"   ❌ Error leyendo archivo: {e}")
        else:
            print(f"❌ Archivo no encontrado: {filepath}")

def show_correction_instructions():
    """Muestra instrucciones específicas para corregir"""
    print("\n🎯 INSTRUCCIONES DE CORRECCIÓN:")
    print("1. En bybit_api.py:")
    print("   - Buscar todas las instancias de \"category\": \"spot\"")
    print("   - Cambiar por \"category\": \"linear\"")
    print("")
    print("2. En indicators.py:")
    print("   - Buscar 'category': 'spot'") 
    print("   - Cambiar por 'category': 'linear'")
    print("")
    print("3. Archivos corregidos:")
    print("   - ✅ config.py (ya corregido)")
    print("   - ❌ bybit_api.py (necesita corrección manual)")
    print("   - ❌ indicators.py (necesita corrección manual)")

if __name__ == "__main__":
    check_file_configuration()
    show_correction_instructions()