# check_bybit_config.py
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def check_bybit_config():
    """Verifica la configuración de Bybit"""
    print("🔍 Verificando configuración de Bybit...")

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    print(
        f"📋 BYBIT_API_KEY: {'✅ Configurada' if api_key and api_key != 'TU_API_KEY_AQUI' else '❌ NO CONFIGURADA'}"
    )
    print(
        f"📋 BYBIT_API_SECRET: {'✅ Configurada' if api_secret and api_secret != 'TU_API_SECRET_AQUI' else '❌ NO CONFIGURADA'}"
    )

    if (
        api_key
        and api_secret
        and api_key != "TU_API_KEY_AQUI"
        and api_secret != "TU_API_SECRET_AQUI"
    ):
        print("🚀 Probando conexión con Bybit...")
        from bybit_api import bybit_client

        # Inicializar cliente
        success = await bybit_client.initialize()
        if success:
            print("✅ Bybit conectado correctamente")

            # Probar endpoints
            ticker = await bybit_client.get_ticker("BTCUSDT")
            if ticker:
                print("✅ Ticker funcionando")
            else:
                print("❌ Error obteniendo ticker")

            balance = await bybit_client.get_account_balance()
            if balance:
                print("✅ Balance funcionando")
            else:
                print("❌ Error obteniendo balance")
        else:
            print("❌ Error inicializando Bybit")
    else:
        print("⚠️  Configura las credenciales de Bybit en el archivo .env")


if __name__ == "__main__":
    asyncio.run(check_bybit_config())
