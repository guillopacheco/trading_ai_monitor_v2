"""
utils/logger.py
----------------
Inicializa el sistema de logging centralizado para toda la aplicación.
"""

import logging
from logging.handlers import RotatingFileHandler


def setup_logging(log_file: str = "trading_ai.log"):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console output
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console.setFormatter(formatter)

    # File output
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=2, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    logger.info("📘 Logging inicializado correctamente.")
