import streamlit as st

from lib import auth

st.set_page_config(page_title="Generative AI Studio", page_icon="🎨")

LOGIN_PAGE = st.Page(auth.login_form, title="Acceso", url_path="", default=True)

if not auth.is_authenticated():
    st.navigation([LOGIN_PAGE]).run()
    st.stop()

PAGES_BY_ROLE = {
    "diseñador": [
        st.Page("pages/1_Generar_Imagen.py", title="Generar Imagen", icon="🖼️"),
        st.Page("pages/3_Galeria_Historial.py", title="Galería e Historial", icon="🗂️"),
    ],
    "redactor": [
        st.Page("pages/2_Editar_Contenido.py", title="Editar Contenido", icon="✍️"),
        st.Page("pages/3_Galeria_Historial.py", title="Galería e Historial", icon="🗂️"),
    ],
    "aprobador": [
        st.Page("pages/3_Galeria_Historial.py", title="Galería e Historial", icon="🗂️"),
    ],
}

with st.sidebar:
    st.caption(f"Sesión iniciada como **{st.session_state['role']}**")
    if st.button("Cerrar sesión"):
        auth.logout()
        st.switch_page(LOGIN_PAGE)

pg = st.navigation(PAGES_BY_ROLE[st.session_state["role"]])
pg.run()
