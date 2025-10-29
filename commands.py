# commands.py - VERSIÓN SIMPLIFICADA PARA COMPATIBILIDAD
import logging

logger = logging.getLogger(__name__)

# Este archivo ahora está mayormente obsoleto
# La funcionalidad se movió a command_bot.py
# Se mantiene por compatibilidad con imports existentes

class CommandHandler:
    def __init__(self):
        # Mantener estructura vacía para compatibilidad
        pass

# Instancia global del manejador de comandos (para compatibilidad)
command_handler = CommandHandler()

# Funciones de compatibilidad (pueden eliminarse gradualmente)
async def start_command(update, context):
    """Función de compatibilidad"""
    pass

async def status_command(update, context):
    """Función de compatibilidad"""
    pass

async def operations_command(update, context):
    """Función de compatibilidad"""
    pass

async def help_command(update, context):
    """Función de compatibilidad"""
    pass

async def review_command(update, context):
    """Función de compatibilidad"""
    pass

async def follow_command(update, context):
    """Función de compatibilidad"""
    pass