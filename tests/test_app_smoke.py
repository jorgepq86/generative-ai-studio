from streamlit.testing.v1 import AppTest


def test_shows_login_form_when_not_authenticated():
    at = AppTest.from_file("app.py")
    at.run()
    assert at.title[0].value == "Acceso — Generative AI Studio"
    assert len(at.text_input) == 1


def test_shows_main_title_when_authenticated():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()
    assert at.title[0].value == "Generative AI Studio"


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
