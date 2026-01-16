import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. Configurações Iniciais
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# 3. Funções de Dados (Cache e Data BR)
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
            editais[conc] = {"cargo": row['cargo'] or "Não informado", "data_br": dt_br, "data_iso": dt_raw, "materias": {}}
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

def db_get_tokens():
    res = supabase.table("tokens_convite").select("*").eq("usado", False).execute()
    return [t['codigo'] for t in res.data]

# 4. Sistema de Login
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Acessar Base", "Novo Guerreiro"])
        with t1:
            if not users:
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"TOKEN: {tk}")
            else:
                with st.form("login_f"):
                    u = st.selectbox("Usuário", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("PIN Incorreto.")
        with t2:
            with st.form("cad_f"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Seu Nome")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    if tk_in in db_get_tokens():
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Criado! Vá em Acessar.")
                    else: st.error("Token Inválido.")
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    # MENU COMPLETO RESTAURADO
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    icons = ["bar-chart", "plus-circle", "trophy", "book-half", "table"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("Gerar Convites")
        icons.append("ticket-perforated")
    
    selected = option_menu("Menu Tático", menus, icons=icons, default_index=0)
    
    if st.button("🔄 Limpar Cache/Datas"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 5. DASHBOARD (DATA BR)
if selected == "Dashboard":
    st.title("📊 Painel de Performance")
    if not df_meu.empty:
        c1, c2, c3 = st.columns(3)
        total_q = int(df_meu['total'].sum())
        prec = (df_meu['acertos'].sum()/total_q*100) if total_q > 0 else 0
        c1.metric("Questões", total_q, border=True)
        c2.metric("Precisão", f"{prec:.1f}%", border=True)
        
        df_evol = df_meu.groupby('data_estudo')['total'].sum().reset_index()
        fig = px.line(df_evol, x='data_estudo', y='total', title="Evolução Diária", markers=True)
        fig.update_xaxes(tickformat="%d/%m/%Y") # DATA BR NO GRÁFICO
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados registrados.")

# 6. NOVO REGISTRO (RESTAURADO)
elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais: st.warning("Cadastre um edital primeiro.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg_s"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat] if editais[conc]["materias"][mat] else ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR REGISTRO"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

# 7. RANKING (RESTAURADO)
elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Squad")
    df_all = db_get_estudos()
    if not df_all.empty:
        rank = df_all.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h', title="Top Guerreiros"), use_container_width=True)

# 8. GESTÃO DE EDITAIS (RESTAURADO COMPLETO)
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Edital", "✏️ Editar/Add Matérias"])
    with t1:
        with st.form("n_ed"):
            n = st.text_input("Nome Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova")
            if st.form_submit_button("CRIAR"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "materia": "Geral", "topicos": [], "cargo": c, "data_prova": d.strftime('%Y-%m-%d')
                }).execute()
                st.cache_data.clear()
                st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Edital", list(editais.keys()))
            st.info(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar Matéria"):
                supabase.table("editais_materias").insert({
                    "concurso": sel, "materia": m_n, "topicos": [], 
                    "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                }).execute()
                st.cache_data.clear()
                st.rerun()
            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    txt = st.text_area(f"Tópicos para {m}", value="; ".join(t), key=f"t_{m}")
                    if st.button("Atualizar", key=f"b_{m}"):
                        novos = [x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear()
                        st.rerun()

# 9. HISTÓRICO (DATA BR RESTAURADO)
elif selected == "Histórico":
    st.title("📜 Histórico Detalhado")
    if not df_meu.empty:
        st.dataframe(df_meu.sort_values('data_estudo', ascending=False),
            column_config={"data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY")},
            use_container_width=True, hide_index=True)

# 10. CONVITES (SÓ ADM)
elif selected == "Gerar Convites":
    st.title("🎟️ Gerador de Tokens")
    if st.button("Gerar Novo"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
