from streamlit.testing.v1 import AppTest


def test_shows_login_form_when_not_authenticated():
    at = AppTest.from_file("app.py")
    at.run()
    assert at.title[0].value == "Acceso — Generative AI Studio"
    assert len(at.text_input) == 1


def test_disenador_lands_on_generar_imagen():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "diseñador"
    at.session_state["user"] = "diseñador"
    at.run()
    assert at.title[0].value == "Generar Imagen"


def test_redactor_lands_on_editar_contenido():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()
    assert at.title[0].value == "Editar Contenido"


def test_aprobador_lands_on_galeria_historial():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "aprobador"
    at.session_state["user"] = "aprobador"
    at.run()
    assert at.title[0].value == "Galería e Historial"


def test_login_with_correct_password_sets_role():
    at = AppTest.from_file("app.py")
    at.secrets["password_redactor"] = "clave123"
    at.run()
    at.text_input[0].input("clave123").run()
    at.button[0].click().run()
    assert at.session_state["role"] == "redactor"
    assert at.session_state["user"] == "redactor"


def test_login_with_wrong_password_shows_error():
    at = AppTest.from_file("app.py")
    at.secrets["password_redactor"] = "clave123"
    at.run()
    at.text_input[0].input("incorrecta").run()
    at.button[0].click().run()
    assert len(at.error) == 1


def test_logout_clears_session_and_shows_login_form_again():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()

    at.sidebar.button[0].click().run()

    assert "role" not in at.session_state
    assert "user" not in at.session_state
    assert at.title[0].value == "Acceso — Generative AI Studio"
