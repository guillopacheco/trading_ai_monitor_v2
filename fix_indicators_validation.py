"""
Corrige la validación demasiado estricta en indicators.py
"""
import re

def fix_indicators_validation():
    print("🔧 Corrigiendo validación en indicators.py...")
    
    try:
        with open('indicators.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y reemplazar la validación estricta
        old_validation = r'if len\(df\) < 30:'
        new_validation = 'if len(df) < 10:  # Reducido de 30 a 10'
        
        content = re.sub(old_validation, new_validation, content)
        
        # También mejorar el mensaje de log
        old_log = r'logger.warning\(f"Datos insuficientes para {symbol}: {len\(df\)} velas"\)'
        new_log = 'logger.warning(f"Datos insuficientes para {symbol}: {len(df)} velas (solicitadas: {limit})")'
        
        content = re.sub(old_log, new_log, content)
        
        with open('indicators.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ indicators.py corregido exitosamente!")
        print("📊 Cambios realizados:")
        print("   - Mínimo de velas requeridas: 30 → 10")
        print("   - Mensajes de log más informativos")
        
    except Exception as e:
        print(f"❌ Error corrigiendo indicators.py: {e}")

if __name__ == "__main__":
    fix_indicators_validation()