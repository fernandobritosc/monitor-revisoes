import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# ======================================================
# 1. CONFIGURAÇÕES DE PÁGINA
# ======================================================
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# ======================================================
# 2. CONEXÃO SUPABASE
# ======================================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# ======================================================
# 3. FUNÇÕES DE DADOS
# ======================================================
@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario:
        query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['data_real'] = pd.to_datetime(df['data_estudo'])
        df['data_br'] = df['data_real'].dt.strftime('%d/%m/%Y')
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

# ======================================================
# 4. LOGIN / REGISTRO
# ======================================================
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
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
                with st.form("login_f"):
                    u = st.selectbox("Usuário", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else:
                            st.error("PIN Incorreto.")
        with t2:
            with st.form("cad_f"):
                tk_in = st.text_input("Token")
                n_in = st.text_input("Nome")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk_in).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Conta criada! Agora faça login.")
                    else:
                        st.error("Token Inválido.")
    st.stop()

# ======================================================
# 5. INTERFACE PRINCIPAL
# ======================================================
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    selected = option_menu("Menu Tático", 
                           ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"], 
                           icons=["bar-chart", "plus-circle", "trophy", "book-half", "table"], 
                           default_index=0)
    
    if usuario_atual == "Fernando Pinheiro":
        if st.button("🎟️ Gerar Token Convite"):
            tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
            supabase.table("tokens_convite").insert({"codigo": tk}).execute()
            st.code(tk)

    st.markdown("---")
    if st.button("🔄 RESET DE MEMÓRIA (Limpar Dados)"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# ======================================================
# 6. DASHBOARD
# ======================================================
if selected == "Dashboard":
    st.title("📊 Painel de Performance")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        tot = int(df_meu['total'].sum())
        c1.metric("Questões", tot)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum() / tot * 100):.1f}%")
        
        df_evol = df_meu.groupby('data_real')['total'].sum().reset_index()
        df_evol = df_evol.sort_values('data_real')
        fig = px.line(df_evol, x='data_real', y='total', title="Evolução Diária", markers=True)
        fig.update_xaxes(tickformat="%d/%m/%Y", title="Data")
        fig.update_yaxes(title="Questões Resolvidas")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados registrados ainda.")

# ======================================================
# 7. NOVO REGISTRO
# ======================================================
elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais:
        st.warning("Cadastre um edital primeiro.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat] if editais[conc]["materias"][mat] else ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'),
                    "usuario": usuario_atual,
                    "concurso": conc,
                    "materia": mat,
                    "assunto": ass,
                    "acertos": a,
                    "total": t,
                    "taxa": (a / t * 100)
                }).execute()
                st.cache_data.clear()
                st.success("Registro salvo com sucesso!")

# ======================================================
# 8. RANKING
# ======================================================
elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Squad")
    res_all = supabase.table("registros_estudos").select("*").execute()
    df_all = pd.DataFrame(res_all.data)
    if not df_all.empty:
        rank = df_all.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h', title="Ranking por Total de Questões"),
                        use_container_width=True)
    else:
        st.info("Sem registros no ranking ainda.")

# ======================================================
# 9. GESTÃO DE EDITAIS
# ======================================================
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    tab1, tab2 = st.tabs(["➕ Novo", "📚 Matérias"])
    
    with tab1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data da Prova")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({
                    "concurso": n,
                    "cargo": c,
                    "data_prova": d.strftime('%Y-%m-%d'),
                    "materia": "Geral",
                    "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()
    
    with tab2:
        if editais:
            sel = st.selectbox("Escolha o Edital", list(editais.keys()))
            st.success(f"📍 Cargo: {editais[sel]['cargo']} | 📅 Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({
                    "concurso": sel,
                    "materia": m_n,
                    "cargo": editais[sel]['cargo'],
                    "data_prova": editais[sel]['data_iso'],
                    "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()
            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    txt = st.text_area(f"Tópicos para {m} (;)", value="; ".join(t), key=f"t_{m}")
                    if st.button("Atualizar", key=f"b_{m}"):
                        novos = [x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear()
                        st.rerun()

# ======================================================
# 10. HISTÓRICO (AJUSTADO)
# ======================================================
elif selected == "Histórico":
    st.title("📜 Histórico de Estudos")
    if not df_meu.empty:
        exibir = df_meu[['data_real', 'data_br', 'concurso', 'materia', 'assunto', 'acertos', 'total']].copy()
        exibir.columns = ['Data Real', 'Data', 'Concurso', 'Matéria', 'Assunto', 'Acertos', 'Total']
        exibir = exibir.sort_values('Data Real', ascending=False)
        st.dataframe(exibir.drop(columns=['Data Real']), use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados registrados ainda. Adicione um novo registro para começar!")
