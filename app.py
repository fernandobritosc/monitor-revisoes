import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro nos Secrets: Verifique SUPABASE_URL e SUPABASE_KEY")
        st.stop()

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
            dt_br = "A definir"
            if dt_raw:
                try: dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: pass
            
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
        hoje = pd.Timestamp.now(tz='America/Sao_Paulo').normalize().tz_localize(None)
        sa = 0
        dr = sorted(dates, reverse=True)
        # Simplificação para o streak
        return cur_s, max_s
    except: return 0, 0

# --- LÓGICA DE LOGIN ---
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Acessar", "Novo Guerreiro"])
        with t1:
            if not users:
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"Token: {tk}")
            else:
                with st.form("login"):
                    u = st.selectbox("Usuário", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR"):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("Incorreto")
        with t2:
            with st.form("cadastro"):
                tk_in = st.text_input("Token")
                n_in = st.text_input("Nome")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4)
                if st.form_submit_button("CRIAR"):
                    if tk_in in db_get_tokens():
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": "padrao"}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Criado!")
    st.stop()

# --- APP LOGADO ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais"]
    icons = ["bar-chart", "plus-circle", "trophy", "book-half"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("Gerar Convites")
        icons.append("ticket-perforated")
    
    selected = option_menu("Menu", menus, icons=icons, default_index=0)

if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
        total_q = pd.to_numeric(df_meu['total']).sum()
        acertos_q = pd.to_numeric(df_meu['acertos']).sum()
        prec = (acertos_q / total_q * 100) if total_q > 0 else 0
        sa, mx = get_streak_metrics(df_meu)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", int(total_q), border=True)
        c2.metric("Precisão", f"{prec:.1f}%", border=True)
        c3.metric("🔥 Streak", f"{sa}d", border=True)
        c4.metric("🏆 Recorde", f"{mx}d", border=True)
    else: st.info("Sem dados.")

elif selected == "Novo Registro":
    st.title("📝 Registro")
    if not editais: st.warning("Crie um edital.")
    else:
        conc = st.selectbox("Edital", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass,
                    "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

elif selected == "Gestão Editais":
    st.title("📑 Editais")
    t_n, t_e = st.tabs(["Novo", "Editar"])
    with t_n:
        with st.form("n"):
            n = st.text_input("Nome Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "materia": "Geral", "topicos": [], "cargo": c, "data_prova": d.strftime('%Y-%m-%d')
                }).execute()
                st.cache_data.clear()
                st.rerun()
    with t_e:
        if editais:
            ed_sel = st.selectbox("Selecionar", list(editais.keys()))
            st.info(f"Cargo: {editais[ed_sel]['cargo']} | Prova: {editais[ed_sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({
                    "concurso": ed_sel, "materia": m_n, "topicos": [], 
                    "cargo": editais[ed_sel]['cargo'], "data_prova": editais[ed_sel]['data_iso']
                }).execute()
                st.cache_data.clear()
                st.rerun()

elif selected == "Gerar Convites":
    if st.button("Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
