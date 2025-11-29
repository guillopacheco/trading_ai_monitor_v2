"""
utils/logger.py
----------------
Configuración central del sistema de logging.
Todos los módulos usan el logger configurado aquí.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


# ============================================================
# 🔵 CONFIGURAR LOGGING GLOBAL
# ============================================================

def configure_logging():
    """
    Configuración unificada del sistema de logs.
    Se invoca una vez desde main.py.
    """

    # Crear carpeta logs/ si no existe
    if not os.path.exists("logs"):
        os.makedirs("logs")

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Evitar múltiples configuraciones si ya existe un handler
    if logging.getLogger().hasHandlers():
        logging.getLogger().handlers.clear()

    # -----------------------------
    # Consola (stream handler)
    # -----------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))

    # -----------------------------
    # Archivo con rotación
    # -----------------------------
    file_handler = RotatingFileHandler(
        "logs/trading_bot.log",
        maxBytes=5_000_000,   # 5 MB
        backupCount=3
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))

    # -----------------------------
    # Logger global
    # -----------------------------
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )

    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)

    logging.info("📘 Logging configurado correctamente (archivo + consola).")
