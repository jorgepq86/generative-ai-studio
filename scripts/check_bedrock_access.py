"""Smoke test manual: confirma que Claude y Nova Canvas están accesibles en Bedrock.

Uso: python scripts/check_bedrock_access.py
Requiere credenciales AWS configuradas (variables de entorno o ~/.aws/credentials),
opcionalmente la variable AWS_REGION (por defecto: us-east-1), y GUARDRAIL_ID
(+ opcionalmente GUARDRAIL_VERSION, por defecto: "1").

GUARDRAIL_ID es obligatorio: la app en producción nunca invoca un modelo sin
guardrail (lib/bedrock_client.py lo exige), así que este script prueba
exactamente la misma ruta de código que usará la app. El script imprime la
cabecera de acción del guardrail para cada modelo para que puedas verlo
directamente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import bedrock_client


def _guardrail_action(response_metadata):
    return response_metadata.get("HTTPHeaders", {}).get("x-amzn-bedrock-guardrailaction", "(sin cabecera)")


def _detail(error):
    """Mensaje de diagnóstico real de AWS, no el mensaje genérico pensado para la UI."""
    cause = error.__cause__
    return f"\n  Detalle real de AWS: {cause}" if cause else ""


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    guardrail_id = os.environ.get("GUARDRAIL_ID")
    guardrail_version = os.environ.get("GUARDRAIL_VERSION", "1")

    if not guardrail_id:
        print(
            "ERROR: define la variable de entorno GUARDRAIL_ID antes de ejecutar este script.\n"
            "La app nunca invoca un modelo sin guardrail, así que este smoke test tampoco lo hace.\n"
            "Ejemplo: GUARDRAIL_ID=abc123 GUARDRAIL_VERSION=1 python scripts/check_bedrock_access.py"
        )
        sys.exit(1)

    client = bedrock_client.get_client(region)

    print(f"Región: {region}")
    print(f"Guardrail: {guardrail_id} (versión {guardrail_version})")

    print("\nProbando Claude...")
    try:
        text, metadata = bedrock_client.invoke_claude(
            client, "Hola, responde con una sola palabra.", "resumir",
            guardrail_id=guardrail_id, guardrail_version=guardrail_version,
        )
        print(f"OK — respuesta: {text[:100]}")
        print(f"Acción del guardrail: {_guardrail_action(metadata)}")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Claude: {error}{_detail(error)}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Claude: {error}{_detail(error)}")

    print("\nProbando Nova Canvas...")
    try:
        image_bytes, metadata = bedrock_client.invoke_image(
            client, "a red apple on a white table", "photorealistic, highly detailed",
            guardrail_id=guardrail_id, guardrail_version=guardrail_version,
        )
        print(f"OK — imagen recibida ({len(image_bytes)} bytes)")
        print(f"Acción del guardrail: {_guardrail_action(metadata)}")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Nova Canvas: {error}{_detail(error)}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Nova Canvas: {error}{_detail(error)}")


if __name__ == "__main__":
    main()
