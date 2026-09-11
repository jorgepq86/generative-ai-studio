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


def _image_response(b64_image):
    return {
        "body": FakeStreamingBody(json.dumps({"images": [b64_image]}).encode()),
        "ResponseMetadata": {"HTTPHeaders": {}},
    }


def test_invoke_claude_returns_edited_text():
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _claude_response("Texto resumido")

    text, metadata = bedrock_client.invoke_claude(
        fake_client, "Texto largo original", "resumir",
        guardrail_id="gr-1", guardrail_version="1", sleep_fn=lambda s: None,
    )

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

    text, _ = bedrock_client.invoke_claude(
        fake_client, "hola", "resumir", guardrail_id="gr-1", guardrail_version="1", sleep_fn=sleeps.append
    )

    assert text == "ok"
    assert sleeps == [1]
    assert fake_client.invoke_model.call_count == 2


def test_invoke_claude_raises_model_access_error_without_retry():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "no access"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.ModelAccessError):
        bedrock_client.invoke_claude(
            fake_client, "hola", "resumir", guardrail_id="gr-1", guardrail_version="1", sleep_fn=lambda s: None
        )

    assert fake_client.invoke_model.call_count == 1


def test_invoke_claude_raises_bedrock_error_on_validation_exception():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "ValidationException", "Message": "bad payload"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.BedrockError):
        bedrock_client.invoke_claude(
            fake_client, "hola", "resumir", guardrail_id="gr-1", guardrail_version="1", sleep_fn=lambda s: None
        )

    assert fake_client.invoke_model.call_count == 1


def test_invoke_image_returns_decoded_image_bytes():
    import base64

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _image_response(base64.b64encode(b"fake-png-bytes").decode())

    image_bytes, _ = bedrock_client.invoke_image(fake_client, "a red apple", "anime style", sleep_fn=lambda s: None)

    assert image_bytes == b"fake-png-bytes"


def test_invoke_image_builds_nova_canvas_request_body():
    import base64

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _image_response(base64.b64encode(b"x").decode())

    bedrock_client.invoke_image(fake_client, "a red apple", "anime style", sleep_fn=lambda s: None)

    _, kwargs = fake_client.invoke_model.call_args
    body = json.loads(kwargs["body"])
    assert body["taskType"] == "TEXT_IMAGE"
    assert body["textToImageParams"]["text"] == "a red apple, anime style"
    assert "imageGenerationConfig" in body


def test_invoke_image_does_not_pass_guardrail_params():
    import base64

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _image_response(base64.b64encode(b"x").decode())

    bedrock_client.invoke_image(fake_client, "a red apple", "anime style", sleep_fn=lambda s: None)

    _, kwargs = fake_client.invoke_model.call_args
    assert "guardrailIdentifier" not in kwargs
    assert "guardrailVersion" not in kwargs


def test_apply_guardrail_image_returns_none_when_not_intervened():
    fake_client = MagicMock()
    fake_client.apply_guardrail.return_value = {"action": "NONE"}

    status = bedrock_client.apply_guardrail_image(
        fake_client, b"fake-png-bytes", "gr-1", "1", sleep_fn=lambda s: None
    )

    assert status == "NONE"
    _, kwargs = fake_client.apply_guardrail.call_args
    assert kwargs["guardrailIdentifier"] == "gr-1"
    assert kwargs["guardrailVersion"] == "1"
    assert kwargs["source"] == "OUTPUT"
    assert kwargs["content"] == [{"image": {"format": "png", "source": {"bytes": b"fake-png-bytes"}}}]


def test_apply_guardrail_image_returns_intervened_when_blocked():
    fake_client = MagicMock()
    fake_client.apply_guardrail.return_value = {"action": "GUARDRAIL_INTERVENED"}

    status = bedrock_client.apply_guardrail_image(
        fake_client, b"fake-png-bytes", "gr-1", "1", sleep_fn=lambda s: None
    )

    assert status == "INTERVENED"


def test_apply_guardrail_image_raises_value_error_when_guardrail_id_missing():
    fake_client = MagicMock()

    with pytest.raises(ValueError):
        bedrock_client.apply_guardrail_image(fake_client, b"x", "", "1", sleep_fn=lambda s: None)

    fake_client.apply_guardrail.assert_not_called()


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


def test_invoke_claude_raises_value_error_when_guardrail_id_missing():
    fake_client = MagicMock()

    with pytest.raises(ValueError):
        bedrock_client.invoke_claude(fake_client, "hola", "resumir", guardrail_id="", sleep_fn=lambda s: None)

    fake_client.invoke_model.assert_not_called()
