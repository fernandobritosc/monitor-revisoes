import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNÇÕES COM TRATAMENTO DE DATA BRASILEIRA ---

@st.cache_data(ttl=600)
def db_get_usuarios():
    res = supabase.table("perfil_usuarios").select("*").execute()
    return {row['nome']: row for row in res.data}

@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario:
        query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        # Garante que a data do estudo seja tratada como data real
        df['data_estudo'] = pd.to_datetime(df['data_estudo'])
    return df

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            # CONVERSÃO PARA EXIBIÇÃO BRASILEIRA
            dt_br = "A definir"
            if dt_raw:
                try: dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: pass
            
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br,
                "data_iso": dt_raw, # Mantemos o ISO para cálculos e inputs
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- LOGIN E MENUS (OMITIDO PARA BREVIDADE, MAS MANTÉM A LÓGICA ANTERIOR) ---
# ... (Aqui vai a mesma lógica de login e menu lateral) ...

# --- DASHBOARD COM CONTAGEM REGRESSIVA ---
if 'usuario_logado' in st.session_state:
    usuario_atual = st.session_state.usuario_logado
    editais = db_get_editais()
    df_meu = db_get_estudos(usuario_atual)
    # Supondo que a seleção de menu seja feita aqui...
    
    # Exemplo na aba Gestão de Editais:
    # st.info(f"📍 Cargo: {editais[ed_sel]['cargo']} | 📅 Prova: {editais[ed_sel]['data_br']}")

# --- NOVO REGISTRO COM SALVAMENTO ISO ---
# Ao salvar:
# "data_estudo": dt_input.strftime('%Y-%m-%d') # Salva assim no banco
