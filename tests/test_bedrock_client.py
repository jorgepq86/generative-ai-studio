import json

import botocore.exceptions
import pytest
from unittest.mock import MagicMock

from lib import bedrock_client


class FakeStreamingBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data


def _claude_response(text):
    return {
        "body": FakeStreamingBody(json.dumps({"content": [{"type": "text", "text": text}]}).encode()),
        "ResponseMetadata": {"HTTPHeaders": {}},
    }


def _sd_response(b64_image):
    return {
        "body": FakeStreamingBody(json.dumps({"artifacts": [{"base64": b64_image}]}).encode()),
        "ResponseMetadata": {"HTTPHeaders": {}},
    }


def test_invoke_claude_returns_edited_text():
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _claude_response("Texto resumido")

    text, metadata = bedrock_client.invoke_claude(fake_client, "Texto largo original", "resumir", sleep_fn=lambda s: None)

    assert text == "Texto resumido"
    assert metadata == {"HTTPHeaders": {}}
    fake_client.invoke_model.assert_called_once()


def test_invoke_claude_retries_on_throttling_then_succeeds():
    fake_client = MagicMock()
    throttle_error = botocore.exceptions.ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Too many requests"}}, "InvokeModel"
    )
    fake_client.invoke_model.side_effect = [throttle_error, _claude_response("ok")]
    sleeps = []

    text, _ = bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=sleeps.append)

    assert text == "ok"
    assert sleeps == [1]
    assert fake_client.invoke_model.call_count == 2


def test_invoke_claude_raises_model_access_error_without_retry():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "no access"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.ModelAccessError):
        bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=lambda s: None)

    assert fake_client.invoke_model.call_count == 1


def test_invoke_claude_raises_bedrock_error_on_validation_exception():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "ValidationException", "Message": "bad payload"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.BedrockError):
        bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=lambda s: None)

    assert fake_client.invoke_model.call_count == 1


def test_invoke_stable_diffusion_returns_decoded_image_bytes():
    import base64

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _sd_response(base64.b64encode(b"fake-png-bytes").decode())

    image_bytes, _ = bedrock_client.invoke_stable_diffusion(fake_client, "a red apple", "anime", sleep_fn=lambda s: None)

    assert image_bytes == b"fake-png-bytes"


def test_invoke_passes_guardrail_params_to_invoke_model():
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _claude_response("ok")

    bedrock_client.invoke_claude(
        fake_client, "hola", "resumir",
        guardrail_id="gr-123", guardrail_version="1", sleep_fn=lambda s: None,
    )

    _, kwargs = fake_client.invoke_model.call_args
    assert kwargs["guardrailIdentifier"] == "gr-123"
    assert kwargs["guardrailVersion"] == "1"
