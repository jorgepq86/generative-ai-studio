import base64
import json
import time

import botocore.exceptions


class BedrockError(Exception):
    """Error genérico al invocar un modelo de Bedrock."""


class ModelAccessError(BedrockError):
    """La cuenta/rol no tiene acceso al modelo solicitado."""


def get_client(region_name, aws_access_key_id=None, aws_secret_access_key=None):
    import boto3
    return boto3.client(
        "bedrock-runtime",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


def _call_with_retry(fn, model_id, max_retries=3, sleep_fn=time.sleep):
    """Ejecuta fn() reintentando solo en ThrottlingException; traduce otros errores de Bedrock."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return fn()
        except botocore.exceptions.ClientError as error:
            code = error.response["Error"]["Code"]
            if code == "AccessDeniedException":
                raise ModelAccessError(
                    f"Sin acceso al modelo '{model_id}'. Solicita acceso en la consola de Amazon Bedrock."
                ) from error
            if code == "ValidationException":
                raise BedrockError(
                    "La petición al modelo no es válida. Ajusta el contenido e inténtalo de nuevo."
                ) from error
            if code == "ThrottlingException":
                last_error = error
                sleep_fn(2 ** attempt)
                continue
            raise BedrockError(f"Error inesperado de Bedrock: {code}") from error
    raise BedrockError("Bedrock sigue limitando la tasa de peticiones tras varios reintentos.") from last_error


def _invoke_with_retry(client, model_id, body, guardrail_id=None, guardrail_version=None,
                        max_retries=3, sleep_fn=time.sleep):
    kwargs = dict(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    if guardrail_id:
        kwargs["guardrailIdentifier"] = guardrail_id
        kwargs["guardrailVersion"] = guardrail_version

    return _call_with_retry(lambda: client.invoke_model(**kwargs), model_id, max_retries, sleep_fn)


def invoke_claude(client, text, action, model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                   guardrail_id=None, guardrail_version=None, sleep_fn=time.sleep):
    if not guardrail_id:
        raise ValueError(
            "Se requiere un guardrail_id para invocar Claude: las peticiones sin "
            "guardrail no pasan por moderación de contenido."
        )
    action_prompts = {
        "resumir": "Resume el siguiente texto manteniendo las ideas clave:",
        "expandir": "Expande el siguiente texto añadiendo más detalle y contexto:",
        "corregir": "Corrige la gramática y el estilo del siguiente texto, sin cambiar su significado:",
        "variar": "Genera una variación del siguiente texto con un tono distinto:",
    }
    instruction = action_prompts[action]
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": f"{instruction}\n\n{text}"}],
    }
    response = _invoke_with_retry(
        client, model_id, body, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    payload = json.loads(response["body"].read())
    result_text = payload["content"][0]["text"]
    return result_text, response["ResponseMetadata"]


def invoke_image(client, prompt, style, model_id="amazon.nova-canvas-v1:0", sleep_fn=time.sleep):
    """Genera una imagen con Nova Canvas.

    Nova Canvas no acepta guardrailIdentifier/guardrailVersion en invoke_model
    (Bedrock devuelve ValidationException: "Guardrail is not supported with the
    chosen model") — a diferencia de los modelos de texto, los modelos de imagen
    de Bedrock no soportan guardrails inline. La imagen generada aquí debe pasar
    por apply_guardrail_image() por separado antes de mostrarse al usuario.
    """
    full_prompt = f"{prompt}, {style}" if style else prompt
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": full_prompt},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 6.5,
        },
    }
    response = _invoke_with_retry(client, model_id, body, sleep_fn=sleep_fn)
    payload = json.loads(response["body"].read())
    image_bytes = base64.b64decode(payload["images"][0])
    return image_bytes, response["ResponseMetadata"]


def apply_guardrail_image(client, image_bytes, guardrail_id, guardrail_version,
                           image_format="png", max_retries=3, sleep_fn=time.sleep):
    """Evalúa una imagen ya generada contra un guardrail vía la API ApplyGuardrail
    (independiente de invoke_model — es la vía soportada por AWS para moderar
    salidas de modelos de imagen, que no aceptan guardrails inline).

    Devuelve "NONE" (contenido limpio) o "INTERVENED" (el guardrail bloqueó el
    contenido), en el mismo vocabulario que usa el resto de la app.
    """
    if not guardrail_id:
        raise ValueError(
            "Se requiere un guardrail_id para evaluar la imagen: las imágenes sin "
            "guardrail no pasan por moderación de contenido."
        )

    def _call():
        return client.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="OUTPUT",
            content=[{"image": {"format": image_format, "source": {"bytes": image_bytes}}}],
        )

    response = _call_with_retry(_call, guardrail_id, max_retries, sleep_fn)
    return "INTERVENED" if response["action"] == "GUARDRAIL_INTERVENED" else "NONE"
