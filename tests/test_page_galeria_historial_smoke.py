from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


def _run_as(role, scan_items=None):
    at = AppTest.from_file("pages/3_Galeria_Historial.py")
    at.session_state["role"] = role
    at.session_state["user"] = role
    at.secrets["s3_bucket"] = "test-bucket"

    fake_table = MagicMock()
    fake_table.scan.return_value = {"Items": scan_items or []}
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


def test_text_history_shows_full_original_and_result_in_expander():
    long_original = "Texto original " * 50
    long_result = "Texto resumido " * 50
    at = _run_as("redactor", scan_items=[{
        "id": "item-1",
        "tipo": "texto",
        "usuario": "redactor",
        "accion": "resumir",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "prompt_o_texto_original": long_original,
        "resultado": long_result,
        "comentarios": [],
    }])

    assert at.exception == []
    assert len(at.expander) >= 1
    markdown_texts = " ".join(md.value for md in at.markdown)
    assert long_original.strip() in markdown_texts
    assert long_result.strip() in markdown_texts
