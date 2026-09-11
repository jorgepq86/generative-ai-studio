import pytest

from lib import moderation


def test_generate_image_moderated_returns_bytes_when_not_intervened(monkeypatch):
    def fake_invoke_image(client, prompt, style, sleep_fn=None):
        return b"image-bytes", {"HTTPHeaders": {}}

    def fake_apply_guardrail(client, image_bytes, guardrail_id, guardrail_version, sleep_fn=None):
        return "NONE"

    monkeypatch.setattr(moderation.bedrock_client, "invoke_image", fake_invoke_image)
    monkeypatch.setattr(moderation.bedrock_client, "apply_guardrail_image", fake_apply_guardrail)

    image_bytes, status = moderation.generate_image_moderated(
        client=object(), prompt="un gato", style="anime", guardrail_id="gr-1", guardrail_version="1"
    )

    assert image_bytes == b"image-bytes"
    assert status == "NONE"


def test_generate_image_moderated_raises_when_intervened(monkeypatch):
    def fake_invoke_image(client, prompt, style, sleep_fn=None):
        return b"image-bytes", {"HTTPHeaders": {}}

    def fake_apply_guardrail(client, image_bytes, guardrail_id, guardrail_version, sleep_fn=None):
        return "INTERVENED"

    monkeypatch.setattr(moderation.bedrock_client, "invoke_image", fake_invoke_image)
    monkeypatch.setattr(moderation.bedrock_client, "apply_guardrail_image", fake_apply_guardrail)

    with pytest.raises(moderation.ModerationBlocked):
        moderation.generate_image_moderated(
            client=object(), prompt="contenido prohibido", style="anime", guardrail_id="gr-1", guardrail_version="1"
        )


def test_generate_image_moderated_raises_when_stability_filter_rejects_prompt(monkeypatch):
    def fake_invoke_image(client, prompt, style, sleep_fn=None):
        raise moderation.bedrock_client.ContentFilteredError("El modelo de imagen rechazó la petición: Filter reason: prompt")

    monkeypatch.setattr(moderation.bedrock_client, "invoke_image", fake_invoke_image)

    with pytest.raises(moderation.ModerationBlocked):
        moderation.generate_image_moderated(
            client=object(), prompt="un paisaje", style="anime", guardrail_id="gr-1", guardrail_version="1"
        )


def test_edit_text_moderated_returns_text_when_not_intervened(monkeypatch):
    def fake_invoke(client, text, action, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return "texto editado", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "NONE"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_claude", fake_invoke)

    result_text, status = moderation.edit_text_moderated(
        client=object(), text="texto", action="resumir", guardrail_id="gr-1", guardrail_version="1"
    )

    assert result_text == "texto editado"
    assert status == "NONE"


def test_edit_text_moderated_raises_when_intervened(monkeypatch):
    def fake_invoke(client, text, action, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return "", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "INTERVENED"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_claude", fake_invoke)

    with pytest.raises(moderation.ModerationBlocked):
        moderation.edit_text_moderated(
            client=object(), text="texto prohibido", action="resumir", guardrail_id="gr-1", guardrail_version="1"
        )


def test_guardrail_status_defaults_to_none_when_header_missing():
    status = moderation._guardrail_status({"HTTPHeaders": {}})
    assert status == "NONE"
