import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Faca na Caveira", page_icon="💀", layout="wide")

# CONEXÃO SUPABASE
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Erro nos Secrets. Verifique o painel do Streamlit.")
        st.stop()

supabase: Client = init_connection()

# FUNÇÕES DE BANCO DE DADOS
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

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {"cargo": row['cargo'] or "Padrão", "data_br": dt_br, "data_iso": dt_raw, "materias": {}}
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# LOGIN
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Acessar", "Novo Guerreiro"])
        with t1:
            if not users:
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"TOKEN: {tk}")
            else:
                with st.form("l"):
                    u = st.selectbox("Usuário", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR"):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("Incorreto")
        with t2:
            with st.form("c"):
                tk_in = st.text_input("Token")
                n_in = st.text_input("Nome")
                p_in = st.text_input("PIN", max_chars=4, type="password")
                if st.form_submit_button("CRIAR"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk_in).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": "padrao"}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Criado!")
                    else: st.error("Token Inválido")
    st.stop()

# INTERFACE LOGADA
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.title(f"🥷 {usuario_atual}")
    selected = option_menu("Menu", ["Dashboard", "Novo Registro", "Ranking", "Gestão Editais", "Histórico"], 
                           icons=['house', 'plus', 'trophy', 'book', 'table'], default_index=0)
    if st.button("Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 1. DASHBOARD (DATA BRASILEIRA NO GRÁFICO)
if selected == "Dashboard":
    st.title("📊 Seu Progresso")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        total = int(df_meu['total'].sum())
        c1.metric("Questões", total)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum()/total*100):.1f}%")
        
        # Gráfico com Eixo X Formatado (DD/MM/YYYY)
        df_evol = df_meu.groupby('data_estudo')['total'].sum().reset_index()
        fig = px.line(df_evol, x='data_estudo', y='total', title="Evolução Diária", markers=True)
        fig.update_xaxes(tickformat="%d/%m/%Y", title="Data") # <--- AQUI CORRIGE O GRÁFICO
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

# 2. NOVO REGISTRO
elif selected == "Novo Registro":
    if not editais: st.warning("Cadastre um edital.")
    else:
        conc = st.selectbox("Edital", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("r"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Assunto", editais[conc]["materias"][mat] if editais[conc]["materias"][mat] else ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("Salvar"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": a, "total": t
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

# 3. GESTÃO DE EDITAIS (DATA BRASILEIRA NA INFO)
elif selected == "Gestão Editais":
    t1, t2 = st.tabs(["Novo", "Add Matéria/Tópicos"])
    with t1:
        with st.form("n"):
            nome = st.text_input("Concurso")
            carg = st.text_input("Cargo")
            data = st.date_input("Data da Prova")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({"concurso": nome, "cargo": carg, "data_prova": data.strftime('%Y-%m-%d'), "materia": "Geral"}).execute()
                st.cache_data.clear()
                st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Selecione", list(editais.keys()))
            st.info(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}") # <--- DATA BR AQUI
            m_n = st.text_input("Matéria")
            if st.button("Adicionar Matéria"):
                supabase.table("editais_materias").insert({"concurso": sel, "materia": m_n, "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']}).execute()
                st.cache_data.clear()
                st.rerun()

# 4. HISTÓRICO (TABELA COM DATA BRASILEIRA)
elif selected == "Histórico":
    if not df_meu.empty:
        st.dataframe(df_meu, column_config={"data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY")}, hide_index=True)

# 5. GERAR CONVITES (APENAS FERNANDO)
elif selected == "Ranking":
    df_g = db_get_estudos()
    if not df_g.empty:
        rank = df_g.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.bar_chart(rank, x="usuario", y="total")

if usuario_atual == "Fernando Pinheiro" and "Gerar Convites" in selected: # Lógica simplificada
    if st.button("Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
