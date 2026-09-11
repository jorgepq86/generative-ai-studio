import base64
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

_FAKE_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_page_shows_warning_when_not_authenticated():
    at = AppTest.from_file("pages/1_Generar_Imagen.py")
    at.run()
    assert len(at.warning) == 1


def test_page_renders_form_when_authenticated():
    at = AppTest.from_file("pages/1_Generar_Imagen.py")
    at.session_state["role"] = "diseñador"
    at.session_state["user"] = "diseñador"
    at.run()
    assert at.title[0].value == "Generar Imagen"
    assert len(at.text_area) == 1
    assert len(at.selectbox) == 1
    assert len(at.button) == 1


def test_generar_button_happy_path_does_not_raise():
    at = AppTest.from_file("pages/1_Generar_Imagen.py")
    at.session_state["role"] = "diseñador"
    at.session_state["user"] = "diseñador"
    at.secrets["guardrail_id"] = "gr-1"
    at.secrets["guardrail_version"] = "1"
    at.secrets["s3_bucket"] = "test-bucket"
    at.secrets["quota_per_hour"] = 20

    fake_table = MagicMock()
    fake_table.scan.return_value = {"Items": []}
    fake_bedrock = MagicMock()
    fake_s3 = MagicMock()

    with patch("lib.clients.get_history_table", return_value=fake_table), \
         patch("lib.clients.get_bedrock_client", return_value=fake_bedrock), \
         patch("lib.clients.get_s3_client", return_value=fake_s3), \
         patch("lib.moderation.generate_image_moderated", return_value=(_FAKE_PNG_BYTES, "NONE")):
        at.run()
        at.text_area[0].set_value("Un gato en el espacio")
        at.button[0].click().run()

    assert at.exception == []
