import streamlit as st

from lib import bedrock_client, storage, history


@st.cache_resource
def get_bedrock_client():
    return bedrock_client.get_client(
        st.secrets["aws_region"],
        aws_access_key_id=st.secrets.get("aws_access_key_id"),
        aws_secret_access_key=st.secrets.get("aws_secret_access_key"),
    )


@st.cache_resource
def get_s3_client():
    return storage.get_client(
        st.secrets["aws_region"],
        aws_access_key_id=st.secrets.get("aws_access_key_id"),
        aws_secret_access_key=st.secrets.get("aws_secret_access_key"),
    )


@st.cache_resource
def get_history_table():
    return history.get_table(
        st.secrets["aws_region"],
        st.secrets["dynamodb_table"],
        aws_access_key_id=st.secrets.get("aws_access_key_id"),
        aws_secret_access_key=st.secrets.get("aws_secret_access_key"),
    )
