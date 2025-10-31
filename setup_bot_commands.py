#!/usr/bin/env python3
"""
Configurar comandos del bot para funcionar en canales - VERSIÓN CORREGIDA
"""
import asyncio
from telegram import Bot
from telegram.constants import BotCommandScopeType
from config import TELEGRAM_BOT_TOKEN

async def setup_bot_commands():
    """Configurar los comandos del bot - VERSIÓN COMPATIBLE"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    commands = [
        ('start', 'Iniciar el bot'),
        ('estado', 'Estado del sistema'),
        ('operaciones', 'Operaciones activas'),
        ('estadisticas', 'Estadísticas de trading'),
        ('config', 'Configuración actual'),
        ('revisar', 'Revisar operaciones abiertas'),
        ('seguimiento', 'Seguimiento de operaciones'),
        ('help', 'Ayuda')
    ]
    
    # Configurar comandos para todos los chats
    await bot.set_my_commands(commands)
    
    print("✅ Comandos configurados:")
    for cmd, desc in commands:
        print(f"   /{cmd} - {desc}")
    
    print("\n🎯 Ahora puedes usar:")
    print("   • Comandos directos al bot: /estado")
    print("   • Comandos en canales: @gapcbot /estado")

if __name__ == "__main__":
    asyncio.run(setup_bot_commands())