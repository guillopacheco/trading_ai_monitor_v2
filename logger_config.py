"""
Configuración del sistema de logging para Trading AI Monitor v2
"""
import logging
import os
from logging.handlers import RotatingFileHandler
# Variable para controlar si ya se inicializó

_logging_initialized = False

def setup_logging():
    """Configura el sistema de logging con archivos rotativos"""
    global _logging_initialized
    
    # Evitar inicialización múltiple
    if _logging_initialized:
        return
    
    _logging_initialized = True
    
    # Crear directorio de logs si no existe
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar el logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Formato de los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo principal
    main_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "trading_bot.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setFormatter(formatter)
    main_handler.setLevel(logging.INFO)
    
    # Handler para errores
    error_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Handler para consola (solo INFO y superior)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Limpiar handlers existentes y agregar nuevos
    logger.handlers.clear()
    logger.addHandler(main_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    # Configurar loggers específicos para evitar propagación al root
    # y así prevenir duplicación de logs
    specific_loggers = ['telegram', 'analysis', 'database', 'telegram.ext']
    
    for logger_name in specific_loggers:
        specific_logger = logging.getLogger(logger_name)
        specific_logger.setLevel(logging.INFO)
        specific_logger.propagate = False  # Evitar que se propague al root
        # Agregar handlers directamente a estos loggers
        for handler in [main_handler, error_handler, console_handler]:
            specific_logger.addHandler(handler)
    
    logging.info("🚀 Sistema de logging inicializado correctamente")

def get_logger(name):
    """Obtiene un logger con el nombre especificado"""
    if not _logging_initialized:
        setup_logging()
    return logging.getLogger(name)

if __name__ == "__main__":
    # Test del sistema de logging
    setup_logging()  # ← Se inicializa explícitamente solo en testing
    logger = get_logger("logger_test")
    logger.info("✅ Test de logging - Mensaje informativo")
    logger.error("❌ Test de logging - Mensaje de error")
    print("Sistema de logging configurado correctamente")