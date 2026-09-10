import logging

import streamlit as st

from lib import auth, clients, diffing, history, moderation

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Editar Contenido", page_icon="✍️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Editar Contenido")

ACTIONS = {
    "resumir": "Resumir",
    "expandir": "Expandir",
    "corregir": "Corregir gramática y estilo",
    "variar": "Generar variación",
}

DRAFT_KEY = "draft_text"
if "pending_draft" in st.session_state:
    st.session_state[DRAFT_KEY] = st.session_state.pop("pending_draft")
if DRAFT_KEY not in st.session_state:
    st.session_state[DRAFT_KEY] = ""

st.text_area("Pega o escribe el texto a editar", height=200, key=DRAFT_KEY)
action_key = st.selectbox("Acción", list(ACTIONS.keys()), format_func=lambda k: ACTIONS[k])

if st.button("Aplicar"):
    current_text = st.session_state[DRAFT_KEY]
    if not current_text.strip():
        st.error("Escribe un texto antes de aplicar una acción.")
        st.stop()

    table = clients.get_history_table()
    quota_limit = st.secrets.get("quota_per_hour", 20)
    used = history.count_recent_generations(table, st.session_state["user"], history.hour_ago_iso())
    if used >= quota_limit:
        st.error(f"Has alcanzado el límite de {quota_limit} operaciones (imágenes + textos) por hora. Inténtalo más tarde.")
        st.stop()

    bedrock = clients.get_bedrock_client()
    try:
        with st.spinner("Aplicando edición..."):
            result_text, moderation_status = moderation.edit_text_moderated(
                bedrock, current_text, action_key,
                guardrail_id=st.secrets["guardrail_id"],
                guardrail_version=st.secrets["guardrail_version"],
            )
    except moderation.ModerationBlocked:
        st.error("El texto no se pudo procesar: el contenido incumple las políticas de uso.")
        st.stop()
    except Exception as error:
        logger.exception("Fallo al invocar Bedrock para editar texto")
        st.error(f"No se pudo aplicar la edición: {error}")
        st.stop()

    try:
        new_id = history.log_edit(
            table, st.session_state["user"], st.session_state["role"], action_key,
            current_text, result_text, st.session_state.get("last_edit_id"), moderation_status,
        )
        st.session_state["last_edit_id"] = new_id
    except Exception:
        logger.exception("No se pudo guardar la edición en el historial")
        st.warning("La edición se aplicó pero no se pudo guardar en el historial.")

    st.session_state["pending_draft"] = result_text
    st.rerun()

if st.session_state.get("last_edit_id"):
    table = clients.get_history_table()
    chain = history.get_version_chain(table, st.session_state["last_edit_id"])
    with st.expander("Historial de versiones"):
        for index, version in enumerate(chain):
            st.write(f"**{ACTIONS.get(version['accion'], version['accion'])}** — {version['timestamp']}")
            if index > 0:
                previous_version = chain[index - 1]
                diff_html = diffing.word_diff_html(previous_version["resultado"], version["resultado"])
                st.markdown(diff_html, unsafe_allow_html=True)
            st.caption(version["resultado"][:200])
            if st.button("Revertir a esta versión", key=f"revert_{version['id']}"):
                st.session_state["pending_draft"] = version["resultado"]
                st.session_state["last_edit_id"] = version["id"]
                st.rerun()
