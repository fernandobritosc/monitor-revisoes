import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. Configuração de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# 3. Funções com Tratamento de Data BR (DD/MM/YYYY)
@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        # CONVERSÃO CRÍTICA: Transforma o texto do banco em Data Real
        df['data_estudo'] = pd.to_datetime(df['data_estudo'])
    return df

@st.cache_data(ttl=600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            # FORMATAÇÃO BRASILEIRA PARA EXIBIÇÃO NA TELA
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br,
                "data_iso": dt_raw,
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- LOGIN (Simplificado para o seu acesso rápido) ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.selectbox("Guerreiro", list(users.keys()))
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                if p == users[u]['pin']:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else: st.error("Erro!")
    st.stop()

# --- APP LOGADO ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    selected = option_menu("Menu", ["Dashboard", "Novo Registro", "Histórico", "Gestão Editais"], 
                           icons=["bar-chart", "plus", "table", "book"], default_index=0)
    if st.button("Limpar Memória do App"): # BOTÃO PARA LIMPAR O CACHE SE A DATA TRAVAR
        st.cache_data.clear()
        st.rerun()
    if st.button("Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 4. DASHBOARD (DATA BR NO GRÁFICO)
if selected == "Dashboard":
    st.title("📊 Seu Progresso")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        total_q = int(df_meu['total'].sum())
        c1.metric("Questões", total_q, border=True)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum()/total_q*100):.1f}%", border=True)
        
        # Agrupamento por data
        df_evol = df_meu.groupby('data_estudo')['total'].sum().reset_index()
        fig = px.line(df_evol, x='data_estudo', y='total', title="Evolução Diária", markers=True)
        
        # AQUI É ONDE A MÁGICA ACONTECE NO GRÁFICO:
        fig.update_xaxes(
            tickformat="%d/%m/%Y", # DIA/MÊS/ANO
            dtick="D1",            # MOSTRAR TODOS OS DIAS
            title="Data do Estudo"
        )
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# 5. HISTÓRICO (DATA BR NA TABELA)
elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        # AQUI É ONDE A MÁGICA ACONTECE NA TABELA:
        st.dataframe(
            df_meu.sort_values('data_estudo', ascending=False),
            column_config={
                "data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "taxa": st.column_config.NumberColumn("Precisão", format="%.1f%%")
            },
            use_container_width=True, hide_index=True
        )

# 6. GESTÃO DE EDITAIS
elif selected == "Gestão Editais":
    st.title("📑 Editais")
    if editais:
        sel = st.selectbox("Escolha", list(editais.keys()))
        # MOSTRANDO A DATA BR NO PAINEL DE INFORMAÇÕES
        st.success(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
