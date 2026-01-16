import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# Tenta importar a versão. Se o arquivo não existir, usa valores padrão para não travar o app.
try:
    import version
except ImportError:
    class version:
        VERSION = "13.0.1-temp"
        STATUS = "Aguardando version.py"

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['dt_ordenacao'] = pd.to_datetime(df['data_estudo'])
        df['Data'] = df['dt_ordenacao'].dt.strftime('%d/%m/%Y')
        df = df.sort_values('dt_ordenacao', ascending=False)
    return df

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- LOGIN (Simplificado) ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.selectbox("Guerreiro", list(users.keys()))
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                if p == users[u]['pin']:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else: st.error("Acesso Negado.")
    st.stop()

# --- AMBIENTE OPERACIONAL ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("⚙️ Gestão de Sistema")
    
    selected = option_menu("Menu Tático", menus, default_index=0)
    
    st.markdown("---")
    st.caption(f"🚀 Versão: {version.VERSION}")
    if st.button("🔄 Sincronizar Tudo"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# --- DASHBOARD ---
if selected == "Dashboard":
    st.title("📊 Desempenho")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        tot = int(df_meu['total'].sum())
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum()/tot*100):.1f}%", border=True)
        
        df_p = df_meu.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        fig = px.line(df_p, x='Data', y='total', markers=True)
        fig.update_xaxes(type='category', title="Data") 
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- NOVO REGISTRO ---
elif selected == "Novo Registro":
    st.title("📝 Novo Registro")
    if not editais: st.warning("Cadastre um edital.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data do Estudo", datetime.date.today(), format="DD/MM/YYYY")
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat] or ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

# --- GESTÃO DE EDITAIS (Onde estava o erro da linha 161) ---
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Adicionar Matéria"])
    with t1:
        with st.form("n_ed"):
            n = st.text_input("Nome do Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data da Prova", datetime.date.today(), format="DD/MM/YYYY")
            if st.form_submit_button("CRIAR"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Selecionar Concurso", list(editais.keys()))
            st.success(f"📍 Cargo: {editais[sel]['cargo']} | 📅 Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                # CORREÇÃO DA LINHA 161: Puxando cargo e data_prova do edital selecionado
                supabase.table("editais_materias").insert({
                    "concurso": sel, "materia": m_n, "topicos": [],
                    "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                }).execute()
                st.cache_data.clear()
                st.success("Matéria adicionada!")
                st.rerun()

# --- HISTÓRICO ---
elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        st.dataframe(df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

# --- SISTEMA (FERNANDO) ---
elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    if st.button("🎟️ Gerar Token de Convite"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
