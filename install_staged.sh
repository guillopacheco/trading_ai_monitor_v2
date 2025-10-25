#!/bin/bash
echo "🔧 INSTALACIÓN POR ETAPAS - Python 3.12"

# Crear entorno
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Etapa 1: Base
echo "📦 Etapa 1: Instalando base..."
python -m pip install --upgrade pip==23.3.1
python -m pip install setuptools==68.2.2 wheel==0.41.3

# Etapa 2: NumPy y pandas (primero)
echo "📦 Etapa 2: Instalando numpy y pandas..."
python -m pip install numpy==1.25.2
python -m pip install pandas==2.1.4

# Etapa 3: Dependencias de Telegram
echo "📦 Etapa 3: Instalando Telegram..."
python -m pip install python-telegram-bot==20.7
python -m pip install telethon==1.28.5

# Etapa 4: Utilidades
echo "📦 Etapa 4: Instalando utilidades..."
python -m pip install python-dotenv==1.0.0
python -m pip install requests==2.31.0

# Etapa 5: SciPy
echo "📦 Etapa 5: Instalando SciPy..."
python -m pip install scipy==1.11.3

# Etapa 6: aiohttp y dependencias
echo "📦 Etapa 6: Instalando aiohttp..."
python -m pip install aiohttp==3.8.6
python -m pip install async-timeout==4.0.3
python -m pip install yarl==1.9.2
python -m pip install multidict==6.0.4
python -m pip install frozenlist==1.4.0
python -m pip install attrs==23.1.0
python -m pip install aiosignal==1.3.1

# Etapa 7: Indicadores técnicos (ALTERNATIVA)
echo "📦 Etapa 7: Instalando indicadores..."
python -m pip install pandas-ta==0.3.14b0

# Crear estructura
mkdir -p logs data
touch .env logs/trading_bot.log logs/error.log data/trading_signals.db

echo "✅ Instalación por etapas COMPLETADA!"
echo "💡 Usa: source venv/bin/activate"
