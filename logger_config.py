# logger_config.py — configuración limpia y silenciosa
# ---------------------------------------------------

import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = "trading_ai_monitor.log"
LOG_MAX_MB = 5
LOG_BACKUP_COUNT = 3

def setup_logging():
    """
    Inicializa un sistema de logging silencioso y eficiente:
    - Guarda SOLO WARNING, ERROR y CRITICAL
    - Guarda INFO solamente de tus módulos (no de httpx)
    - Filtra spam repetitivo
    """

    # === Crear carpeta si no existe ===
    log_path = os.path.join(os.getcwd(), LOG_FILE)

    # === Formato del log ===
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # === Rotating file handler (para evitar que el archivo crezca infinito) ===
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)

    # Guardar WARNING+ en archivo (evita spam INFO)
    file_handler.setLevel(logging.WARNING)

    # === Consola: solo INFO+ (opcional) ===
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    # === Configurar logger raíz ===
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # ------------------------------------------------------------
    # 🔇 SILENCIAR módulos ruidosos (httpx, urllib3, asyncio, aiohttp)
    # ------------------------------------------------------------
    noisy_modules = [
        "httpx",
        "urllib3",
        "asyncio",
        "telegram",
        "apscheduler",
        "websockets",
    ]

    for module in noisy_modules:
        logging.getLogger(module).setLevel(logging.WARNING)

    # bybit_client genera spam cada 10s → lo dejamos en WARNING
    logging.getLogger("bybit_client").setLevel(logging.WARNING)

    # operation_tracker: solo registrar WARNING/ERROR para evitar spam
    logging.getLogger("operation_tracker").setLevel(logging.WARNING)

    # notifier: registrar INFO cuando envía alertas reales
    logging.getLogger("notifier").setLevel(logging.INFO)

    # signal_manager: eventos de señales sí son importantes
    logging.getLogger("signal_manager").setLevel(logging.INFO)

    # trend_system_final: eventos importantes, sin detalles debug
    logging.getLogger("trend_system_final").setLevel(logging.INFO)

    print("📘 Logging configurado correctamente (archivo y consola).")
