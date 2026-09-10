from streamlit.testing.v1 import AppTest


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
