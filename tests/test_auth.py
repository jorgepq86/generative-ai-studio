from lib import auth


def test_check_password_returns_role_for_matching_password():
    secrets = {"password_redactor": "clave123", "password_disenador": "otra"}
    assert auth.check_password("clave123", secrets) == "redactor"


def test_check_password_returns_none_for_wrong_password():
    secrets = {"password_redactor": "clave123"}
    assert auth.check_password("incorrecta", secrets) is None


def test_check_password_returns_none_when_secret_missing():
    secrets = {}
    assert auth.check_password("cualquier", secrets) is None
