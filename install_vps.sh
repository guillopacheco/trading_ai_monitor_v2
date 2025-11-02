#!/bin/bash
set -e  # Salir en cualquier error

echo "🚀 INSTALACIÓN OPTIMIZADA PARA HETZNER CX23"
echo "============================================"

# Información del sistema
echo "💻 Información del sistema:"
echo "   CPU: $(nproc) cores"
echo "   RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "   OS: $(lsb_release -d | cut -f2)"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "🐍 Instalando Python 3.11..."
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
fi

# Verificar versión de Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:1])))')
echo "✅ Python version: $(python3 --version)"

# Instalar dependencias del sistema
echo "📦 Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    sqlite3 \
    libatlas-base-dev  # Optimizado para ARM

# Crear estructura de directorios
echo "📁 Creando estructura de directorios..."
mkdir -p logs data backups scripts

# Crear entorno virtual
echo "🔧 Creando entorno virtual..."
rm -rf venv  # Limpiar si existe
python3 -m venv venv
source venv/bin/activate

# Configurar pip para mejor rendimiento
echo "⚡ Optimizando pip..."
pip install --upgrade pip==23.3.1
pip config set global.timeout 60
pip config set global.retries 10

# INSTALACIÓN POR ETAPAS OPTIMIZADA

# Etapa 1: Base científica (compilación optimizada)
echo "📊 Etapa 1: Instalando base científica..."
export NPY_NUM_BUILD_JOBS=$(nproc)
pip install --no-cache-dir numpy==1.25.2
pip install --no-cache-dir scipy==1.11.3
pip install --no-cache-dir pandas==2.1.4

# Etapa 2: HTTP y async
echo "🌐 Etapa 2: Instalando clientes HTTP..."
pip install aiohttp==3.8.6
pip install requests==2.31.0
pip install async-timeout==4.0.3

# Etapa 3: Telegram
echo "🤖 Etapa 3: Instalando librerías de Telegram..."
pip install python-telegram-bot==20.7
pip install telethon==1.28.5

# Etapa 4: Trading y APIs
echo "📈 Etapa 4: Instalando librerías de trading..."
pip install python-dotenv==1.0.0
pip install pandas-ta==0.3.14b0
pip install pybit==2.6.0  # API Bybit

# Etapa 5: Utilidades
echo "🔧 Etapa 5: Instalando utilidades..."
pip install yarl==1.9.2
pip install multidict==6.0.4

# Verificar instalación
echo "✅ Verificando instalación..."
python3 -c "
import sys
print('Python:', sys.version)

libs = [
    'pandas', 'numpy', 'scipy', 'pandas_ta',
    'telegram', 'telethon', 'aiohttp', 'requests',
    'pybit', 'dotenv'
]

for lib in libs:
    try:
        if lib == 'pandas_ta':
            import pandas_ta
            print(f'✅ {lib}: {pandas_ta.__version__}')
        elif lib == 'telegram':
            import telegram
            print(f'✅ {lib}: {telegram.__version__}')
        elif lib == 'telethon':
            import telethon
            print(f'✅ {lib}: {telethon.__version__}')
        elif lib == 'pybit':
            import pybit
            print(f'✅ {lib}: {pybit.__version__}')
        else:
            __import__(lib)
            print(f'✅ {lib}: OK')
    except ImportError as e:
        print(f'❌ {lib}: {e}')
"

# Crear archivos de configuración
echo "📄 Creando archivos de configuración..."

# Crear .env template optimizado para VPS
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# =============================================
# TRADING AI MONITOR v2 - CONFIGURACIÓN VPS
# =============================================

# Telegram User API (para leer canales)
TELEGRAM_API_ID=tu_api_id_aqui
TELEGRAM_API_HASH=tu_api_hash_aqui
TELEGRAM_PHONE=+tu_numero_aqui
TELEGRAM_USER_ID=tu_user_id_aqui

# Telegram Bot API (para comandos y notificaciones)
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui

# Canales de Telegram
SIGNALS_CHANNEL_ID=-1001774144094
OUTPUT_CHANNEL_ID=-1002396668741

# Bybit API (Linear Trading)
BYBIT_API_KEY=tu_bybit_api_key_aqui
BYBIT_API_SECRET=tu_bybit_secret_aqui

# Configuración de Trading
APP_MODE=ANALYSIS  # ANALYSIS o TRADING
LEVERAGE=20
RISK_PER_TRADE=0.02  # 2% por operación
ACCOUNT_BALANCE=1000

# Configuración del Sistema
LOG_LEVEL=INFO
DATABASE_PATH=data/trading_signals.db

# =============================================
# CONFIGURACIÓN AVANZADA VPS
# =============================================
HEALTH_CHECK_INTERVAL=300
RECONNECT_ATTEMPTS=5
API_TIMEOUT=30
EOF
    echo "⚠️  Configura .env con tus credenciales REALES"
else
    echo "✅ .env ya existe"
fi

# Inicializar base de datos con estructura actual
echo "🗄️ Inicializando base de datos..."
python3 -c "
import sqlite3
import os

os.makedirs('data', exist_ok=True)
conn = sqlite3.connect('data/trading_signals.db')
cursor = conn.cursor()

# Tabla de señales (estructura actualizada)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        pair TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_loss REAL,
        take_profit_1 REAL,
        take_profit_2 REAL, 
        take_profit_3 REAL,
        take_profit_4 REAL,
        leverage INTEGER DEFAULT 20,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        analysis_data TEXT,
        signal_data TEXT
    )
''')

# Tabla de operaciones
cursor.execute('''
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL,
        position_size REAL,
        leverage INTEGER,
        pnl_percentage REAL DEFAULT 0,
        status TEXT DEFAULT 'open',
        opened_at TEXT NOT NULL,
        closed_at TEXT,
        close_reason TEXT,
        FOREIGN KEY (signal_id) REFERENCES signals (id)
    )
''')

# Migración: agregar columna symbol si no existe
cursor.execute('PRAGMA table_info(signals)')
columns = [column[1] for column in cursor.fetchall()]

if 'symbol' not in columns:
    cursor.execute('ALTER TABLE signals ADD COLUMN symbol TEXT')
    cursor.execute('UPDATE signals SET symbol = pair WHERE symbol IS NULL')

conn.commit()
conn.close()
print('✅ Base de datos inicializada correctamente')
"

# Crear script de inicio para systemd
echo "⚡ Creando servicio systemd..."
sudo tee /etc/systemd/system/trading-bot.service > /dev/null << EOF
[Unit]
Description=Trading AI Monitor v2
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Crear script de gestión
cat > manage_bot.sh << 'EOF'
#!/bin/bash
case "\$1" in
    start)
        sudo systemctl start trading-bot
        echo "🚀 Bot iniciado"
        ;;
    stop)
        sudo systemctl stop trading-bot
        echo "🛑 Bot detenido"
        ;;
    restart)
        sudo systemctl restart trading-bot
        echo "🔁 Bot reiniciado"
        ;;
    status)
        sudo systemctl status trading-bot
        ;;
    logs)
        journalctl -u trading-bot -f
        ;;
    update)
        git pull
        sudo systemctl restart trading-bot
        echo "🔄 Sistema actualizado y reiniciado"
        ;;
    *)
        echo "Uso: ./manage_bot.sh {start|stop|restart|status|logs|update}"
        ;;
esac
EOF

chmod +x manage_bot.sh

# Configurar logrotate
echo "📝 Configurando logrotate..."
sudo tee /etc/logrotate.d/trading-bot > /dev/null << EOF
$PWD/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

echo ""
echo "🎉 INSTALACIÓN COMPLETADA EN HETZNER CX23!"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. 🔐 Configurar .env con tus credenciales REALES"
echo "2. 🤖 Configurar bot: source venv/bin/activate && python setup_bot_commands.py"
echo "3. 🚀 Iniciar servicio: ./manage_bot.sh start"
echo "4. 📊 Ver logs: ./manage_bot.sh logs"
echo ""
echo "🔧 GESTIÓN DEL BOT:"
echo "   ./manage_bot.sh start    # Iniciar"
echo "   ./manage_bot.sh stop     # Detener" 
echo "   ./manage_bot.sh status   # Estado"
echo "   ./manage_bot.sh logs     # Logs en tiempo real"
echo "   ./manage_bot.sh update   # Actualizar y reiniciar"
echo ""
echo "🌐 ACCESO WEB (opcional):"
echo "   Considera instalar nginx + certbot para dashboard web"
echo ""
echo "💾 BACKUP AUTOMÁTICO:"
echo "   La base de datos se guarda en: data/trading_signals.db"