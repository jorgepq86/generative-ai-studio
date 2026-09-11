import streamlit as st

ROLE_SECRET_KEYS = {
    "diseñador": "password_disenador",
    "redactor": "password_redactor",
    "aprobador": "password_aprobador",
}


def check_password(password, secrets):
    for role, secret_key in ROLE_SECRET_KEYS.items():
        expected = secrets.get(secret_key)
        if expected and password == expected:
            return role
    return None


def is_authenticated():
    return "role" in st.session_state


def logout():
    st.session_state.pop("role", None)
    st.session_state.pop("user", None)


def login_form():
    st.title("Acceso — Generative AI Studio")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        role = check_password(password, st.secrets)
        if role:
            st.session_state["role"] = role
            st.session_state["user"] = role
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
