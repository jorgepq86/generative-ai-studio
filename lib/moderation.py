import time

from lib import bedrock_client


class ModerationBlocked(Exception):
    def __init__(self, message="El contenido fue bloqueado por las políticas de uso."):
        super().__init__(message)


def _guardrail_status(response_metadata):
    headers = response_metadata.get("HTTPHeaders", {})
    return headers.get("x-amzn-bedrock-guardrailaction", "NONE")


def generate_image_moderated(client, prompt, style, guardrail_id, guardrail_version, sleep_fn=time.sleep):
    image_bytes, metadata = bedrock_client.invoke_image(
        client, prompt, style, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    status = _guardrail_status(metadata)
    if status == "INTERVENED":
        raise ModerationBlocked()
    return image_bytes, status


def edit_text_moderated(client, text, action, guardrail_id, guardrail_version, sleep_fn=time.sleep):
    result_text, metadata = bedrock_client.invoke_claude(
        client, text, action, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    status = _guardrail_status(metadata)
    if status == "INTERVENED":
        raise ModerationBlocked()
    return result_text, status
