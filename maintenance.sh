#!/bin/bash
# ================================================================
# 🧠 Trading AI Monitor - Script de mantenimiento automático
# ---------------------------------------------------------------
# Funciones principales:
# 1️⃣ Verifica la presencia de .env y variables críticas.
# 2️⃣ Activa el entorno virtual del proyecto.
# 3️⃣ Lanza main.py en bucle continuo (reinicio automático si falla).
# 4️⃣ Registra logs rotativos y hora de reinicio.
# ================================================================

PROJECT_DIR="/root/trading_ai_monitor_v2"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/maintenance.log"
PYTHON_SCRIPT="$PROJECT_DIR/main.py"

# ================================================================
# 🕒 Timestamp para logs
# ================================================================
timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

# ================================================================
# 📋 Validar archivo .env
# ================================================================
check_env() {
  if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "$(timestamp) ❌ ERROR: No se encontró el archivo .env en $PROJECT_DIR" | tee -a "$LOG_FILE"
    exit 1
  fi

  echo "$(timestamp) 🧩 Verificando variables críticas..." | tee -a "$LOG_FILE"
  # Verifica variables esenciales
  REQUIRED_VARS=(TELEGRAM_API_ID TELEGRAM_API_HASH TELEGRAM_BOT_TOKEN TELEGRAM_USER_ID BYBIT_API_KEY BYBIT_API_SECRET)
  for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "$var" "$PROJECT_DIR/.env"; then
      echo "$(timestamp) ⚠️ Falta la variable: $var en .env" | tee -a "$LOG_FILE"
    fi
  done
  echo "$(timestamp) ✅ Validación de entorno completada." | tee -a "$LOG_FILE"
}

# ================================================================
# 🧠 Activar entorno virtual
# ================================================================
activate_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    echo "$(timestamp) ❌ ERROR: No se encontró el entorno virtual en $VENV_DIR" | tee -a "$LOG_FILE"
    exit 1
  fi

  # Activar el entorno virtual
  source "$VENV_DIR/bin/activate"
  echo "$(timestamp) 🧩 Entorno virtual activado correctamente." | tee -a "$LOG_FILE"
}

# ================================================================
# 🚀 Ejecutar main.py con reinicio automático
# ================================================================
run_app() {
  echo "$(timestamp) 🚀 Iniciando Trading AI Monitor..." | tee -a "$LOG_FILE"
  while true; do
    python "$PYTHON_SCRIPT"
    EXIT_CODE=$?
    echo "$(timestamp) ⚠️ main.py finalizó con código $EXIT_CODE. Reiniciando en 10s..." | tee -a "$LOG_FILE"
    sleep 10
  done
}

# ================================================================
# 📜 Iniciar
# ================================================================
mkdir -p "$PROJECT_DIR/logs"
check_env
activate_venv
run_app
