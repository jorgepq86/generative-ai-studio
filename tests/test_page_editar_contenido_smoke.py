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
