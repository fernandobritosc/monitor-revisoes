import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS (CONTEXTUALIZADAS) ---

@st.cache_data(ttl=300)
def db_get_estudos(usuario, concurso):
    """Busca registros apenas do usuário e do concurso selecionado"""
    query = supabase.table("registros_estudos").select("*").eq("usuario", usuario).eq("concurso", concurso)
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
            dt_br = "A definir"
            if dt_raw:
                try: dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: dt_br = "Erro"
            editais[conc] = {
                "cargo": row.get('cargo') or "Não informado", 
                "data_br": dt_br, "data_iso": dt_raw, "materias": {}
            }
        materia = row.get('materia')
        if materia: editais[conc]["materias"][materia] = row.get('topicos') or []
    return editais

# --- LOGIN ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.selectbox("Guerreiro", list(users.keys()) if users else ["Nenhum"])
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                if u in users and p == users[u]['pin']:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else: st.error("Acesso Negado")
    st.stop()

# --- CENTRAL DE MISSÕES (O QUE VOCÊ PEDIU) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()

# Se não houver concurso selecionado, obriga a escolher um antes de entrar no ambiente
if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Bem-vindo, {usuario_atual}")
    st.markdown("### Selecione sua Missão Atual:")
    
    if not editais:
        st.warning("Nenhum edital cadastrado. Vá em 'Gestão' para criar um.")
        if st.button("Criar Primeiro Edital"):
            st.session_state.concurso_ativo = "Novo Edital" # Temporário para liberar o menu
            st.rerun()
    else:
        # Grade de botões para escolher o concurso
        for conc in editais.keys():
            if st.button(f"🚀 ENTRAR NO AMBIENTE: {conc.upper()}", use_container_width=True):
                st.session_state.concurso_ativo = conc
                st.rerun()
    st.stop()

# --- AMBIENTE OPERACIONAL (CONCURSO SELECIONADO) ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 Missão: **{concurso_ativo}**")
    
    if st.button("🔄 Trocar de Concurso", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
    
    st.markdown("---")
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu", menus, default_index=0)
    
    if st.button("🚪 Sair do Sistema"):
        del st.session_state.usuario_logado
        if 'concurso_ativo' in st.session_state: del st.session_state.concurso_ativo
        st.rerun()

# --- LÓGICA DE TELAS (TOTALMENTE ISOLADAS) ---

if selected == "Dashboard":
    st.title(f"📊 Performance: {concurso_ativo}")
    if not df_missao.empty:
        c1, c2 = st.columns(2)
        tot = int(df_missao['total'].sum())
        c1.metric("Questões Nesta Missão", tot, border=True)
        c2.metric("Precisão na Missão", f"{(df_missao['acertos'].sum()/tot*100):.1f}%", border=True)
        
        # Gráfico focado apenas no concurso ativo
        df_p = df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        fig = px.line(df_p, x='Data', y='total', markers=True, title=f"Evolução em {concurso_ativo}")
        st.plotly_chart(fig, use_container_width=True)
    else: 
        st.info(f"Você ainda não tem registros no concurso {concurso_ativo}.")

elif selected == "Novo Registro":
    st.title(f"📝 Registro: {concurso_ativo}")
    # Aqui a matéria já é filtrada pelo concurso ativo automaticamente
    if concurso_ativo not in editais:
        st.error("Configure as matérias deste edital na Gestão.")
    else:
        materias_missao = list(editais[concurso_ativo]["materias"].keys())
        mat = st.selectbox("Matéria", materias_missao)
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass_lista = editais[concurso_ativo]["materias"].get(mat) or ["Geral"]
            ass = st.selectbox("Assunto", ass_lista)
            a = st.number_input("Acertos", 0); t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR NA MISSÃO"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": concurso_ativo, "materia": mat, "assunto": ass, 
                    "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear(); st.success("Registrado!")

elif selected == "Histórico":
    st.title(f"📜 Diário de Bordo: {concurso_ativo}")
    if not df_missao.empty:
        st.dataframe(df_missao[['Data', 'materia', 'assunto', 'acertos', 'total']], 
                     use_container_width=True, hide_index=True)
    else: st.info("Nada registrado para esta missão.")

# (Os outros menus Ranking, Gestão e Sistema funcionam globalmente como antes)
