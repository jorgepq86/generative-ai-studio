from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


def test_page_shows_warning_when_not_authenticated():
    at = AppTest.from_file("pages/2_Editar_Contenido.py")
    at.run()
    assert len(at.warning) == 1


def test_page_renders_form_when_authenticated():
    at = AppTest.from_file("pages/2_Editar_Contenido.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()
    assert at.title[0].value == "Editar Contenido"
    assert len(at.text_area) == 1
    assert len(at.selectbox) == 1
    assert len(at.button) == 1


def test_aplicar_button_happy_path_does_not_raise():
    """Regression test for the widget-state crash (StreamlitWidgetAlreadyInstantiatedError)
    that happened when the Aplicar handler wrote directly to the text_area's session_state
    key after the widget had already been instantiated in the same run."""
    at = AppTest.from_file("pages/2_Editar_Contenido.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.secrets["guardrail_id"] = "gr-1"
    at.secrets["guardrail_version"] = "1"
    at.secrets["quota_per_hour"] = 20

    fake_table = MagicMock()
    fake_table.scan.return_value = {"Items": []}
    fake_table.get_item.return_value = {}
    fake_bedrock = MagicMock()

    with patch("lib.clients.get_history_table", return_value=fake_table), \
         patch("lib.clients.get_bedrock_client", return_value=fake_bedrock), \
         patch("lib.moderation.edit_text_moderated", return_value=("texto editado", "NONE")):
        at.run()
        at.text_area[0].set_value("Texto original a editar")
        at.button[0].click().run()

    assert at.exception == []
    assert at.session_state["draft_text"] == "texto editado"
