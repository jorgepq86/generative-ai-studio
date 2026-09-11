from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


def _run_as(role):
    at = AppTest.from_file("pages/3_Galeria_Historial.py")
    at.session_state["role"] = role
    at.session_state["user"] = role
    at.secrets["s3_bucket"] = "test-bucket"

    fake_table = MagicMock()
    fake_table.scan.return_value = {"Items": []}
    fake_s3 = MagicMock()

    with patch("lib.clients.get_history_table", return_value=fake_table), \
         patch("lib.clients.get_s3_client", return_value=fake_s3):
        at.run()
    return at


def test_page_shows_warning_when_not_authenticated():
    at = AppTest.from_file("pages/3_Galeria_Historial.py")
    at.run()
    assert len(at.warning) == 1


def test_disenador_sees_only_gallery_no_tabs():
    at = _run_as("diseñador")
    assert at.exception == []
    assert len(at.tabs) == 0
    assert any("imágenes" in info.value for info in at.info)


def test_redactor_sees_only_history_no_tabs():
    at = _run_as("redactor")
    assert at.exception == []
    assert len(at.tabs) == 0
    assert any("textos" in info.value for info in at.info)


def test_aprobador_sees_both_sections_as_tabs():
    at = _run_as("aprobador")
    assert at.exception == []
    assert len(at.tabs) == 2
    assert [tab.label for tab in at.tabs] == ["Galería de imágenes", "Historial de textos"]
