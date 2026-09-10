import streamlit as st

from lib import auth, clients, history, storage

st.set_page_config(page_title="Galería e Historial", page_icon="🗂️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Galería e Historial")

table = clients.get_history_table()
items = history.list_items(table)

tab_gallery, tab_history = st.tabs(["Galería de imágenes", "Historial de textos"])


def _comment_section(item):
    with st.expander("Comentarios"):
        for comentario in item.get("comentarios", []):
            st.write(f"**{comentario['usuario']}**: {comentario['comentario']}")
        new_comment = st.text_input("Añadir comentario", key=f"comment_{item['id']}")
        if st.button("Comentar", key=f"btn_comment_{item['id']}"):
            if new_comment.strip():
                history.add_comment(table, item["id"], st.session_state["user"], new_comment)
                st.rerun()


with tab_gallery:
    image_items = [item for item in items if item["tipo"] == "imagen"]
    if not image_items:
        st.info("Todavía no se han generado imágenes.")
    for item in image_items:
        s3_client = clients.get_s3_client()
        url = storage.get_image_url(s3_client, st.secrets["s3_bucket"], item["resultado"])
        st.image(url, caption=f"{item['prompt_o_texto_original']} ({item['estilo']}) — {item['usuario']}")
        _comment_section(item)

with tab_history:
    text_items = [item for item in items if item["tipo"] == "texto"]
    if not text_items:
        st.info("Todavía no se han editado textos.")
    for item in text_items:
        st.write(f"**{item['accion']}** por {item['usuario']} — {item['timestamp']}")
        st.caption(item["resultado"][:300])
        _comment_section(item)
