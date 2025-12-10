"""
logger_config.py — Configuración de logging para toda la aplicación
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging():
    """
    Configura el logging global de la aplicación.
    Crea logs rotativos en /logs/app.log
    """

    # Crear carpeta logs si no existe
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configuración base
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            RotatingFileHandler(
                filename=f"{log_dir}/app.log",
                maxBytes=5 * 1024 * 1024,   # 5 MB por archivo
                backupCount=5,
                encoding="utf-8",
            ),
            logging.StreamHandler()  # muestra en consola
        ]
    )

    logger = logging.getLogger("LOGGER")
    logger.info("✔ Logging configurado correctamente.")

