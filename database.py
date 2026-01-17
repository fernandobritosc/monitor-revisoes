import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    # Puxa as credenciais que já estão no seu Streamlit Secrets
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()
