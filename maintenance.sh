#!/bin/bash
# ================================================================
# 🧠 Trading AI Monitor - Mantenimiento automático con reporte Telegram
# ================================================================

APP_PATH="/home/usuario/trading_ai_monitor_v2"
LOG_PATH="$APP_PATH/logs"
DB_FILE="$APP_PATH/trading_ai_monitor.db"
SIGNAL_SERVICE="trading_ai_signals.service"
MONITOR_SERVICE="trading_ai_monitor.service"
MAX_LOG_SIZE=5242880  # 5 MB
ENV_FILE="$APP_PATH/.env"
REPORT_FILE="$LOG_PATH/maintenance_report.txt"

echo "=============================================================="
echo "🧾 Iniciando mantenimiento con reporte Telegram - $(date)"
echo "=============================================================="

# 1️⃣ Cargar variables de entorno (.env)
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "❌ No se encontró archivo .env"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_USER_ID" ]; then
    echo "⚠️ Variables de Telegram no configuradas en .env"
fi

mkdir -p "$LOG_PATH"

# 2️⃣ Verificar servicios
echo "🔍 Verificando servicios..." > "$REPORT_FILE"
for SERVICE in $SIGNAL_SERVICE $MONITOR_SERVICE; do
    STATUS=$(systemctl is-active $SERVICE)
    if [ "$STATUS" != "active" ]; then
        echo "⚠️ $SERVICE no activo → Reiniciando..." >> "$REPORT_FILE"
        sudo systemctl restart $SERVICE
        sleep 3
        NEW_STATUS=$(systemctl is-active $SERVICE)
        if [ "$NEW_STATUS" == "active" ]; then
            echo "✅ $SERVICE reiniciado correctamente." >> "$REPORT_FILE"
        else
            echo "❌ Falló el reinicio de $SERVICE." >> "$REPORT_FILE"
        fi
    else
        echo "🟢 $SERVICE funcionando correctamente." >> "$REPORT_FILE"
    fi
done

# 3️⃣ Limpiar logs pesados
echo -e "\n🧹 Limpieza de logs:" >> "$REPORT_FILE"
for LOGFILE in $LOG_PATH/*.log; do
    if [ -f "$LOGFILE" ]; then
        SIZE=$(stat -c%s "$LOGFILE")
        if [ "$SIZE" -gt "$MAX_LOG_SIZE" ]; then
            echo "🧽 $LOGFILE reducido (tamaño > 5MB)" >> "$REPORT_FILE"
            mv "$LOGFILE" "$LOGFILE.$(date +%Y%m%d_%H%M).bak"
            echo "" > "$LOGFILE"
        fi
    fi
done

# 4️⃣ Optimización de base de datos
echo -e "\n🗃️ Optimización de base de datos:" >> "$REPORT_FILE"
if [ -f "$DB_FILE" ]; then
    sqlite3 "$DB_FILE" "VACUUM;"
    sqlite3 "$DB_FILE" "ANALYZE;"
    echo "✅ Base de datos optimizada correctamente." >> "$REPORT_FILE"
else
    echo "⚠️ No se encontró la base de datos en $DB_FILE" >> "$REPORT_FILE"
fi

# 5️⃣ Estado del sistema
DISK=$(df -h / | awk 'NR==2 {print $5}')
RAM=$(free -m | awk '/Mem/ {printf "%.1f%%", $3/$2*100}')
echo -e "\n💽 Espacio usado: $DISK" >> "$REPORT_FILE"
echo "🧠 RAM usada: $RAM" >> "$REPORT_FILE"

# 6️⃣ Enviar reporte a Telegram
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_USER_ID" ]; then
    REPORT_CONTENT=$(cat "$REPORT_FILE")
    MESSAGE="🧾 *Reporte Diario - Trading AI Monitor*\n\n$REPORT_CONTENT"
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id="$TELEGRAM_USER_ID" \
        -d parse_mode="Markdown" \
        -d text="$MESSAGE" >/dev/null
    echo "📨 Reporte enviado a Telegram."
else
    echo "⚠️ No se envió el reporte: credenciales de Telegram faltantes."
fi

echo "=============================================================="
echo "✅ Mantenimiento y reporte completados: $(date)"
echo "=============================================================="
