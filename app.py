import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import secrets
import string

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNÇÕES COM CACHE (VELOCIDADE MÁXIMA) ---

@st.cache_data(ttl=600) # Cache de 10 min para usuários
def db_get_usuarios():
    res = supabase.table("perfil_usuarios").select("*").execute()
    return {row['nome']: row for row in res.data}

@st.cache_data(ttl=300) # Cache de 5 min para estudos
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario:
        query = query.eq("usuario", usuario)
    res = query.execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=3600) # Cache de 1 hora para editais
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            editais[conc] = {"cargo": row['cargo'], "data": str(row['data_prova']), "materias": {}}
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

def db_get_tokens():
    # Sem cache para convites (precisa ser em tempo real)
    res = supabase.table("tokens_convite").select("*").eq("usado", False).execute()
    return [t['codigo'] for t in res.data]

# --- LÓGICA DE STREAK ---
def get_streak_metrics(df):
    if df.empty or 'data_estudo' not in df.columns: return 0, 0
    try:
        dates = pd.to_datetime(df['data_estudo']).dt.normalize().dropna().unique()
        dates = sorted(dates)
        if not len(dates): return 0, 0
        max_s, cur_s = 1, 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1: cur_s += 1
            else: max_s = max(max_s, cur_s); cur_s = 1
        max_s = max(max_s, cur_s)
        hoje = pd.Timestamp.now().normalize()
        sa = 0
        dr = sorted(dates, reverse=True)
        if hoje in dr: sa = 1; ck = hoje - pd.Timedelta(days=1)
        elif (hoje - pd.Timedelta(days=1)) in dr: sa = 0; ck = hoje - pd.Timedelta(days=1)
        else: return 0, max_s
        for d in dr:
            if d == hoje: continue
            if d == ck: sa += 1; ck -= pd.Timedelta(days=1)
            else: break
        return sa, max_s
    except: return 0, 0

# --- LOGIN ---
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Acessar Base", "Novo Guerreiro", "Recuperar PIN"])
        
        with t1:
            if not users:
                st.info("Nenhum usuário. Gere um token inicial.")
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"Token: {tk}")
            else:
                with st.form("login_form"):
                    u = st.selectbox("Quem está acessando?", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("PIN incorreto.")

        with t2:
            with st.form("cadastro_form"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Nome do Guerreiro")
                p_in = st.text_input("PIN (4 dígitos)", type="password", max_chars=4)
                ch_in = st.text_input("Palavra-Chave (Reset)")
                if st.form_submit_button("CRIAR CONTA"):
                    ativos = db_get_tokens()
                    if tk_in in ativos:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": ch_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear() # Limpa cache para o novo usuário aparecer
                        st.success("Conta criada! Vá em 'Acessar Base'.")
                    else: st.error("Token inválido.")

    st.stop()

# --- APP LOGADO ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st
