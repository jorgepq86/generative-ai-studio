from streamlit.testing.v1 import AppTest


def test_app_loads_and_shows_title():
    at = AppTest.from_file("app.py")
    at.run()
    assert at.title[0].value == "Generative AI Studio"
