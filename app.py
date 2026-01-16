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

# --- FUNÇÕES DE BANCO DE DADOS ---
def db_get_usuarios():
    res = supabase.table("perfil_usuarios").select("*").execute()
    return {row['nome']: row for row in res.data}

def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario:
        query = query.eq("usuario", usuario)
    res = query.execute()
    return pd.DataFrame(res.data)

def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    # Organiza em dicionário para compatibilidade
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            editais[conc] = {"cargo": row['cargo'], "data": str(row['data_prova']), "materias": {}}
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

def db_get_tokens():
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
        t1, t2, t3 = st.tabs(["Acessar", "Novo Guerreiro", "Reset"])
        
        with t1:
            if not users:
                st.info("Banco vazio. Gere um token inicial no Supabase ou via botão.")
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"Token: {tk}")
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
                n_in = st.text_input("Nome Completo")
                p_in = st.text_input("PIN (4 dígitos)", type="password", max_chars=4)
                ch_in = st.text_input("Palavra-Chave")
                if st.form_submit_button("CRIAR"):
                    ativos = db_get_tokens()
                    if tk_in in ativos:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": ch_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.success("Criado! Acesse agora.")
                    else: st.error("Token Inválido")
    st.stop()

# --- APP LOGADO ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("Gerar Convites")
    
    selected = option_menu("Menu", menus, default_index=0)

if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
        total_q = df_meu['total'].sum()
        prec = (df_meu['acertos'].sum() / total_q * 100) if total_q > 0 else 0
        sa, mx = get_streak_metrics(df_meu)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", int(total_q), border=True)
        c2.metric("Precisão", f"{prec:.1f}%", border=True)
        c3.metric("🔥 Streak", f"{sa}d", border=True)
        c4.metric("🏆 Recorde", f"{mx}d", border=True)
    else: st.info("Sem dados.")

elif selected == "Novo Registro":
    st.title("📝 Registro")
    if not editais: st.warning("Cadastre um edital.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        topicos = editais[conc]["materias"][mat]
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", topicos)
            ac, tot = st.columns(2)
            a_v = ac.number_input("Acertos", 0)
            t_v = tot.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                tx = (a_v/t_v*100)
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass,
                    "acertos": a_v, "total": t_v, "taxa": tx
                }).execute()
                st.success("Salvo no Banco!")

elif selected == "Ranking Squad":
    st.title("🏆 Ranking")
    df_g = db_get_estudos()
    if not df_g.empty:
        rank = df_g.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h', color="usuario"))

elif selected == "Gestão Editais":
    st.title("📑 Editais")
    with st.expander("Novo Concurso"):
        n = st.text_input("Nome")
        if st.button("Criar"):
            # Insere primeira matéria vazia para criar o registro
            supabase.table("editais_materias").insert({"concurso": n, "materia": "Geral", "topicos": []}).execute()
            st.rerun()
    if editais:
        ed_sel = st.selectbox("Editar", list(editais.keys()))
        m_nome = st.text_input("Nova Matéria")
        if st.button("Add Matéria"):
            supabase.table("editais_materias").insert({"concurso": ed_sel, "materia": m_nome, "topicos": []}).execute()
            st.rerun()
        
        for m, t in editais[ed_sel]["materias"].items():
            with st.expander(f"{m}"):
                txt = st.text_area(f"Tópicos para {m}", key=f"t_{m}")
                if st.button("Importar", key=f"b_{m}"):
                    novos = [x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", ed_sel).eq("materia", m).execute()
                    st.rerun()

elif selected == "Gerar Convites":
    st.title("🎟️ Convites")
    if st.button("Gerar Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
