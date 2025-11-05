#!/bin/bash
# ================================================================
# 🚀 Trading AI Monitor - Script de arranque automatizado
# Compatible con Linux / VPS (Ubuntu/Debian)
# ================================================================

APP_NAME="Trading AI Monitor"
VENV_DIR="venv"
LOG_FILE="trading_ai_monitor.log"
MAIN_FILE="main.py"

echo "=============================================================="
echo "🧠 Iniciando $APP_NAME"
echo "=============================================================="

# 1️⃣ Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 no está instalado. Instálalo con:"
    echo "   sudo apt update && sudo apt install python3 python3-venv -y"
    exit 1
fi

# 2️⃣ Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️ Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

# 3️⃣ Activar entorno virtual
source "$VENV_DIR/bin/activate"
echo "✅ Entorno virtual activado"

# 4️⃣ Instalar dependencias
if [ -f "requirements.txt" ]; then
    echo "📦 Instalando dependencias..."
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt >/dev/null
    echo "✅ Dependencias instaladas correctamente"
else
    echo "⚠️ No se encontró requirements.txt, omitiendo instalación"
fi

# 5️⃣ Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️ No se encontró el archivo .env"
    echo "   Crea uno a partir de .env.example antes de ejecutar el bot"
    deactivate
    exit 1
fi

# 6️⃣ Lanzar aplicación
echo "🚀 Ejecutando aplicación principal ($MAIN_FILE)"
nohup python3 "$MAIN_FILE" > "$LOG_FILE" 2>&1 &

APP_PID=$!
sleep 2

if ps -p $APP_PID > /dev/null; then
    echo "✅ $APP_NAME iniciado correctamente (PID: $APP_PID)"
    echo "📜 Logs: tail -f $LOG_FILE"
else
    echo "❌ Error iniciando $APP_NAME. Revisa los logs en $LOG_FILE"
fi

# 7️⃣ Información final
echo "=============================================================="
echo "🧾 Estado del sistema:"
echo " - Entorno: $(python3 --version)"
echo " - Modo: $(grep SIMULATION_MODE .env | cut -d'=' -f2)"
echo " - Fecha: $(date)"
echo "=============================================================="
