"""Smoke test manual: confirma que Claude y Stable Diffusion están accesibles en Bedrock.

Uso: python scripts/check_bedrock_access.py
Requiere credenciales AWS configuradas (variables de entorno o ~/.aws/credentials)
y opcionalmente la variable AWS_REGION (por defecto: us-east-1).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import bedrock_client


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = bedrock_client.get_client(region)

    print(f"Región: {region}")

    print("\nProbando Claude...")
    try:
        text, _ = bedrock_client.invoke_claude(client, "Hola, responde con una sola palabra.", "resumir")
        print(f"OK — respuesta: {text[:100]}")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Claude: {error}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Claude: {error}")

    print("\nProbando Stable Diffusion...")
    try:
        image_bytes, _ = bedrock_client.invoke_stable_diffusion(client, "a red apple on a white table", "photographic")
        print(f"OK — imagen recibida ({len(image_bytes)} bytes)")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Stable Diffusion: {error}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Stable Diffusion: {error}")


if __name__ == "__main__":
    main()
