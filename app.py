import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. CONEXÃO SEGURA COM SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro nos Secrets: Verifique as chaves no painel do Streamlit Cloud.")
        st.stop()

supabase: Client = init_connection()

# 3. FUNÇÕES COM CACHE E TRATAMENTO DE DATAS (PT-BR)
@st.cache_data(ttl=600)
def db_get_usuarios():
    res = supabase.table("perfil_usuarios").select("*").execute()
    return {row['nome']: row for row in res.data}

@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
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
            # CONVERSÃO PARA FORMATO BRASILEIRO NA EXIBIÇÃO
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br,
                "data_iso": dt_raw,
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

def db_get_tokens():
    res = supabase.table("tokens_convite").select("*").eq("usado", False).execute()
    return [t['codigo'] for t in res.data]

# --- LÓGICA DE ACESSO ---
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Acessar", "Novo Guerreiro"])
        with t1:
            if not users:
                if st.button("Gerar Token de Primeiro Acesso"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"Token: {tk}")
            else:
                with st.form("login"):
                    u = st.selectbox("Quem está acessando?", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("PIN incorreto.")
        with t2:
            with st.form("cadastro"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Nome Completo")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    if tk_in in db_get_tokens():
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": "padrao"}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Sucesso! Vá para a aba Acessar.")
                    else: st.error("Token inválido.")
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    selected = option_menu("Menu", ["Dashboard", "Novo Registro", "Ranking", "Gestão Editais", "Histórico"], 
                           icons=["bar-chart", "plus-circle", "trophy", "book-half", "table"], default_index=0)

# --- DASHBOARD (DATA BR NO GRÁFICO) ---
if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        total_q = df_meu['total'].sum()
        c1.metric("Questões Totais", int(total_q), border=True)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum() / total_q * 100):.1f}%", border=True)
        
        df_evol = df_meu.groupby('data_estudo')['total'].sum().reset_index()
        fig = px.line(df_evol, x='data_estudo', y='total', title="Evolução Diária", markers=True)
        fig.update_xaxes(tickformat="%d/%m/%Y", title="Data") # FORÇA DATA BR
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# --- NOVO REGISTRO ---
elif selected == "Novo Registro":
    st.title("📝 Novo Registro")
    if not editais: st.warning("Cadastre um edital primeiro.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("form_reg"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat] if editais[conc]["materias"][mat] else ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            # CORREÇÃO DA LINHA 128:
            if st.form_submit_button("SALVAR REGISTRO", use_container_width=True):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass,
                    "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo com sucesso!")

# --- GESTÃO DE EDITAIS (CORREÇÃO DO APIERROR) ---
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Adicionar Matéria"])
    
    with t1:
        with st.form("n_edital"):
            n = st.text_input("Nome do Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data da Prova")
            if st.form_submit_button("CRIAR"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "materia": "Geral", "topicos": [], 
                    "cargo": c, "data_prova": d.strftime('%Y-%m-%d')
                }).execute()
                st.cache_data.clear()
                st.success("Criado!")
                st.rerun()
    
    with t2:
        if editais:
            sel = st.selectbox("Escolha o Edital", list(editais.keys()))
            st.info(f"📍 Cargo: {editais[sel]['cargo']} | 📅 Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nome da Matéria")
            if st.button("ADICIONAR MATÉRIA"):
                # CORREÇÃO: Incluir cargo e data_prova para evitar erro de banco
                supabase.table("editais_materias").insert({
                    "concurso": sel, "materia": m_n, "topicos": [],
                    "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                }).execute()
                st.cache_data.clear()
                st.success(f"{m_n} adicionada!")
                st.rerun()

# --- HISTÓRICO ---
elif selected == "Histórico":
    if not df_meu.empty:
        st.dataframe(df_meu.sort_values('data_estudo', ascending=False), 
                     column_config={"data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
                     use_container_width=True, hide_index=True)
