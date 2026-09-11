import streamlit as st

from lib import auth

st.set_page_config(page_title="Generative AI Studio", page_icon="🎨")

if not auth.is_authenticated():
    auth.login_form()
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

st.caption(f"Sesión iniciada como **{st.session_state['role']}**")
pg = st.navigation(PAGES_BY_ROLE[st.session_state["role"]])
pg.run()
