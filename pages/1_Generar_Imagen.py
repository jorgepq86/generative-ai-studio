import streamlit as st

from lib import auth, clients, history, moderation, storage

st.set_page_config(page_title="Generar Imagen", page_icon="🖼️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Generar Imagen")

STYLE_PRESETS = {
    "Anime": "anime",
    "Pintura al óleo": "cinematic",
    "Realismo fotográfico": "photographic",
    "Boceto a lápiz": "line-art",
    "Cyberpunk": "neon-punk",
}

prompt = st.text_area("Describe la imagen que quieres generar")
style_label = st.selectbox("Estilo", list(STYLE_PRESETS.keys()))

if st.button("Generar"):
    if not prompt.strip():
        st.error("Escribe una descripción antes de generar.")
        st.stop()

    table = clients.get_history_table()
    quota_limit = st.secrets.get("quota_per_hour", 20)
    used = history.count_recent_generations(table, st.session_state["user"], history.hour_ago_iso())
    if used >= quota_limit:
        st.error(f"Has alcanzado el límite de {quota_limit} generaciones por hora. Inténtalo más tarde.")
        st.stop()

    bedrock = clients.get_bedrock_client()
    try:
        with st.spinner("Generando imagen..."):
            image_bytes, moderation_status = moderation.generate_image_moderated(
                bedrock, prompt, STYLE_PRESETS[style_label],
                guardrail_id=st.secrets["guardrail_id"],
                guardrail_version=st.secrets["guardrail_version"],
            )
    except moderation.ModerationBlocked:
        st.error("La imagen no se pudo generar: el contenido incumple las políticas de uso.")
        st.stop()
    except Exception as error:
        st.error(f"No se pudo generar la imagen: {error}")
        st.stop()

    s3_client = clients.get_s3_client()
    try:
        s3_key = storage.save_image(s3_client, st.secrets["s3_bucket"], st.session_state["user"], image_bytes)
        history.log_generation(
            table, st.session_state["user"], st.session_state["role"], prompt, style_label, s3_key, moderation_status
        )
    except Exception:
        st.warning("La imagen se generó pero no se pudo guardar en el historial.")

    st.image(image_bytes, caption=prompt)
    st.download_button("Descargar imagen", data=image_bytes, file_name="imagen_generada.png", mime="image/png")
