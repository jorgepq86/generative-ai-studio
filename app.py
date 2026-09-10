import streamlit as st

from lib import auth

st.set_page_config(page_title="Generative AI Studio", page_icon="🎨")

if not auth.is_authenticated():
    auth.login_form()
    st.stop()

st.title("Generative AI Studio")
st.write(f"Sesión iniciada como **{st.session_state['role']}**")
st.write("Usa el menú lateral para navegar entre Generar Imagen, Editar Contenido y Galería/Historial.")
