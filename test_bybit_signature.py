# test_bybit_signature.py
import asyncio
import hmac
import hashlib
import time
from urllib.parse import urlencode


async def test_bybit_signature():
    """Prueba específica de la firma de Bybit"""
    print("🔐 Probando firma de Bybit...")

    from config import BYBIT_API_KEY, BYBIT_API_SECRET

    api_key = BYBIT_API_KEY
    api_secret = BYBIT_API_SECRET

    # Parámetros de prueba
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    params = {"accountType": "UNIFIED", "coin": "USDT"}

    print(f"📋 Parámetros: {params}")
    print(f"🕒 Timestamp: {timestamp}")
    print(f"📊 Recv Window: {recv_window}")

    # Método CORREGIDO para generar firma
    def generate_correct_signature(params_dict):
        # Ordenar parámetros alfabéticamente
        sorted_params = sorted(params_dict.items())
        # Crear cadena en formato key=value&key=value
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Crear cadena para firma
        signature_payload = timestamp + api_key + recv_window + param_str
        print(f"📝 Payload para firma: {signature_payload}")

        # Generar firma
        signature = hmac.new(
            bytes(api_secret, "utf-8"),
            bytes(signature_payload, "utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    # Generar firma correcta
    correct_signature = generate_correct_signature(params)
    print(f"✅ Firma generada: {correct_signature}")

    # Probar con el cliente real
    from bybit_api import bybit_client

    print("\n🚀 Probando con cliente Bybit...")
    success = await bybit_client.initialize()
    if success:
        print("✅ Cliente inicializado")

        # Probar balance
        balance = await bybit_client.get_account_balance()
        if balance:
            print("✅ Balance obtenido correctamente")
            print(f"📊 Balance: {balance}")
        else:
            print("❌ Error obteniendo balance")

        # Probar posiciones
        positions = await bybit_client.get_open_positions()
        if positions is not None:
            print(f"✅ Posiciones: {len(positions)} encontradas")
            for pos in positions[:3]:  # Mostrar primeras 3
                print(f"  - {pos.get('symbol')}: {pos.get('side')} {pos.get('size')}")
        else:
            print("❌ Error obteniendo posiciones")
    else:
        print("❌ Error inicializando cliente")


if __name__ == "__main__":
    asyncio.run(test_bybit_signature())
