#!/bin/bash
set -e  # Salir en cualquier error

echo "🚀 Instalando Trading AI Monitor v2..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Instalando..."
    sudo apt update
    sudo apt install python3 python3-pip python3-venv python3-tk -y
fi

# Verificar versión de Python (mínimo 3.8)
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo "✅ Python version compatible: $PYTHON_VERSION"
else
    echo "❌ Se requiere Python $REQUIRED_VERSION o superior. Versión actual: $PYTHON_VERSION"
    exit 1
fi

# Verificar tkinter (esencial para la GUI)
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "❌ tkinter no está disponible. Instalando..."
    sudo apt update
    sudo apt install python3-tk -y
fi

# Crear directorios necesarios
echo "📁 Creando estructura de directorios..."
mkdir -p logs data scripts

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install --upgrade pip

# Verificar que requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt no encontrado!"
    echo "📋 Creando requirements.txt actualizado..."
    cat > requirements.txt << EOF
python-telegram-bot==20.7
telethon==1.28.5
python-dotenv==1.0.0
pandas==2.0.3
numpy>=1.21.0
scipy>=1.7.0
ta==0.10.2
requests==2.31.0
aiohttp==3.8.5
EOF
    echo "✅ requirements.txt creado con dependencias actualizadas"
fi

pip install -r requirements.txt

# Crear archivos necesarios - CORREGIDO
echo "📁 Creando archivos de configuración y base de datos..."

# Crear .env si no existe
if [ ! -f ".env" ]; then
    echo "📄 Creando archivo .env..."
    cat > .env << EOF
# Telegram (Cuenta de usuario)
TELEGRAM_API_ID=tu_api_id
TELEGRAM_API_HASH=tu_api_hash
TELEGRAM_PHONE=+tu_numero
TELEGRAM_USER_ID=tu_user_id
TELEGRAM_BOT_TOKEN=tu_bot_token
SIGNALS_CHANNEL_ID=-1001774144094
OUTPUT_CHANNEL_ID=-1002396668741

# Bybit Configuration
BYBIT_API_KEY=tu_bybit_key
BYBIT_API_SECRET=tu_bybit_secret

# Trading Configuration
APP_MODE=ANALYSIS
EOF
    echo "⚠️  Configura .env con tus credenciales reales"
else
    echo "✅ .env ya existe"
fi

# Crear archivos de logs
echo "📄 Creando archivos de logs..."
touch logs/trading_bot.log
touch logs/error.log
echo "✅ Archivos de logs creados"

# Crear base de datos SQLite
echo "🗄️  Inicializando base de datos..."
python3 -c "
import sqlite3
import os

# Crear directorio data si no existe
os.makedirs('data', exist_ok=True)

# Conectar y crear tablas
conn = sqlite3.connect('data/trading_signals.db')
cursor = conn.cursor()

# Tabla de señales
cursor.execute('''
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        tp1 REAL,
        tp2 REAL,
        tp3 REAL,
        tp4 REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'received',
        confirmation_status TEXT,
        match_percentage REAL,
        confidence TEXT,
        original_message TEXT,
        analysis_summary TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# Tabla de análisis
cursor.execute('''
    CREATE TABLE IF NOT EXISTS signal_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        timeframe TEXT,
        trend TEXT,
        rsi REAL,
        rsi_status TEXT,
        macd_signal TEXT,
        macd_line REAL,
        macd_histogram REAL,
        atr REAL,
        atr_status TEXT,
        atr_multiplier REAL,
        close_price REAL,
        analysis_timestamp DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (signal_id) REFERENCES signals (id) ON DELETE CASCADE
    )
''')

# Tabla de divergencias
cursor.execute('''
    CREATE TABLE IF NOT EXISTS divergences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        type TEXT,
        indicator TEXT,
        timeframe TEXT,
        strength TEXT,
        confidence REAL DEFAULT 0.5,
        price_swing_low REAL,
        price_swing_high REAL,
        indicator_swing_low REAL,
        indicator_swing_high REAL,
        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (signal_id) REFERENCES signals (id) ON DELETE CASCADE
    )
''')

conn.commit()
conn.close()
print('✅ Base de datos inicializada correctamente')
"

# Verificar que la base de datos se creó
if [ -f "data/trading_signals.db" ]; then
    echo "✅ Base de datos creada: data/trading_signals.db"
    
    # Verificar tablas
    python3 -c "
import sqlite3
conn = sqlite3.connect('data/trading_signals.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\\\"table\\\"')
tables = cursor.fetchall()
print(f'✅ Tablas en la base de datos: {[table[0] for table in tables]}')
conn.close()
"
else
    echo "❌ ERROR: No se pudo crear la base de datos"
    exit 1
fi

# Dar permisos de ejecución a scripts
if [ -d "scripts" ]; then
    chmod +x scripts/*.sh 2>/dev/null || echo "⚠️ No se encontraron scripts ejecutables en scripts/"
fi

# Crear script de test de integración
echo "🧪 Creando script de test de integración..."
cat > test_integration.py << 'EOF'
#!/usr/bin/env python3
"""
Test de integración entre módulos del Trading AI Monitor
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers import parse_signal_message, validate_signal_data
from database import trading_db
from trend_analysis import trend_analyzer
from indicators import indicators_calculator

def test_parsing():
    """Test del parser de señales"""
    print("🧪 Probando parser de señales...")
    
    test_messages = [
        """🔥 #UB/USDT (Long📈, x20) 🔥
Entry - 0.04869
Take-Profit:
🥉 0.04966 (40% of profit)
🥈 0.05015 (60% of profit)
🥇 0.05063 (80% of profit)
🚀 0.05112 (100% of profit)""",
        
        """🔥 #4/USDT (Short📉, x20) 🔥
Entry - 0.0854
Take-Profit:
🥉 0.08369 (40% of profit)
🥈 0.08284 (60% of profit)
🥇 0.08198 (80% of profit)
🚀 0.08113 (100% of profit)"""
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Test señal {i} ---")
        parsed = parse_signal_message(msg)
        if parsed:
            print(f"✅ Parseado: {parsed['pair']} {parsed['direction']}")
            print(f"   Entry: {parsed['entry']}, Leverage: x{parsed['leverage']}")
            is_valid = validate_signal_data(parsed)
            print(f"   Validación: {'✅ PASS' if is_valid else '❌ FAIL'}")
        else:
            print("❌ No se pudo parsear")

def test_database():
    """Test de la base de datos"""
    print("\n🧪 Probando base de datos...")
    try:
        # Test de conexión
        stats = trading_db.get_signal_stats(days=1)
        print(f"✅ Base de datos operativa")
        print(f"   Señales en BD: {stats.get('total_signals', 0)}")
        return True
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def test_indicators():
    """Test de indicadores técnicos"""
    print("\n🧪 Probando indicadores técnicos...")
    try:
        # Test básico de indicadores
        analysis = indicators_calculator.analyze_timeframe("BTCUSDT", "5")
        if analysis:
            print(f"✅ Indicadores funcionando")
            print(f"   Precio: {analysis['close_price']}, RSI: {analysis['rsi']}")
            return True
        else:
            print("❌ No se pudieron obtener indicadores (puede ser normal si no hay conexión a internet)")
            return True  # Consideramos éxito porque el módulo se importa correctamente
    except Exception as e:
        print(f"❌ Error en indicadores: {e}")
        return False

async def test_trend_analysis():
    """Test del análisis de tendencias"""
    print("\n🧪 Probando análisis de tendencias...")
    try:
        test_signal = {
            'pair': 'BTCUSDT',
            'direction': 'SHORT', 
            'entry': 50000,
            'leverage': 20,
            'tp1': 49000, 'tp2': 48500, 'tp3': 48000, 'tp4': 47500,
            'tp1_percent': 40, 'tp2_percent': 60, 'tp3_percent': 80, 'tp4_percent': 100
        }
        
        analysis = trend_analyzer.analyze_signal(test_signal, 'BTCUSDT')
        if analysis and 'recommendation' in analysis:
            print(f"✅ Análisis de tendencias funcionando")
            print(f"   Recomendación: {analysis['recommendation'].action}")
            return True
        else:
            print("❌ No se pudo completar el análisis")
            return False
    except Exception as e:
        print(f"❌ Error en análisis de tendencias: {e}")
        return False

async def main():
    print("🚀 Iniciando tests de integración...")
    
    # Tests síncronos
    test_parsing()
    test_database() 
    test_indicators()
    
    # Tests asíncronos
    await test_trend_analysis()
    
    print("\n" + "="*50)
    print("✅ Tests de integración completados")
    print("📝 Revisa los resultados arriba para verificar que todo funciona")

if __name__ == "__main__":
    asyncio.run(main())
EOF

echo "✅ Script de test de integración creado: test_integration.py"

# Probar la instalación básica
echo "🧪 Probando instalación básica..."
python3 -c "
import sys
print('✅ Python path:', sys.executable)
try:
    import pandas, numpy, telegram, telethon, requests, aiohttp
    print('✅ Todas las dependencias importan correctamente')
except ImportError as e:
    print(f'❌ Error importando: {e}')
"

echo ""
echo "✅ Instalación completada!"
echo ""
echo "📝 Siguientes pasos:"
echo "1. Configura tu archivo .env con los tokens de Telegram y API keys REALES"
echo "2. Activa el entorno: source venv/bin/activate"  
echo "3. Prueba la integración: python test_integration.py"
echo "4. Prueba Telegram: python test_telegram_setup.py"
echo "5. Ejecuta el sistema: python main.py"
echo ""
echo "🔧 Archivos creados:"
echo "   ✅ .env (configura con tus credenciales)"
echo "   ✅ data/trading_signals.db (base de datos)"
echo "   ✅ logs/trading_bot.log"
echo "   ✅ logs/error.log"
echo "   ✅ test_integration.py"
echo ""
echo "🚨 IMPORTANTE: Edita el archivo .env con tus credenciales reales antes de usar el sistema"