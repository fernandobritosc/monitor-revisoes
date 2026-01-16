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

# 2. Segurança: Import de Versão Blindado
try:
    import version
except ImportError:
    class version:
        VERSION = "19.0.0-MASTER"
        STATUS = "Sistema Unificado"

# 3. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS ---

@st.cache_data(ttl=300)
def db_get_estudos(usuario, concurso=None):
    query = supabase.table("registros_estudos").select("*").eq("usuario", usuario)
    if concurso:
        query = query.eq("concurso", concurso)
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
        t_log, t_cad = st.tabs(["Acessar", "Novo Guerreiro"])
        with t_log:
            with st.form("login"):
                u = st.selectbox("Guerreiro", list(users.keys()) if users else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users and p == users[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("Acesso Negado")
        with t_cad:
            with st.form("cad"):
                tk = st.text_input("Token de Convite")
                n = st.text_input("Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n, "pin": pi}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                        st.success("Conta criada! Vá em Acessar.")
                    else: st.error("Token Inválido")
    st.stop()

# --- SELETOR DE MISSÃO (NOVA LÓGICA) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()

if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Guerreiro {usuario_atual}, selecione sua missão:")
    if not editais:
        if st.button("➕ Criar Primeiro Edital"):
            st.session_state.concurso_ativo = "Novo Edital"
            st.rerun()
    else:
        cols = st.columns(2)
        for i, conc in enumerate(editais.keys()):
            with cols[i % 2]:
                if st.button(f"🚀 {conc.upper()}", use_container_width=True):
                    st.session_state.concurso_ativo = conc
                    st.rerun()
    st.stop()

# --- AMBIENTE OPERACIONAL ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 **Missão Ativa:**\n{concurso_ativo}")
    if st.button("🔄 Trocar de Missão", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
    st.markdown("---")
    menus = ["Dashboard", "Novo Registro", "Gestão do Edital", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu Tático", menus, icons=["bar-chart", "plus-circle", "book-half", "table", "gear"], default_index=0)
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        if 'concurso_ativo' in st.session_state: del st.session_state.concurso_ativo
        st.rerun()

# --- NAVEGAÇÃO ---

if selected == "Dashboard":
    st.title(f"📊 Performance: {concurso_ativo}")
    if not df_missao.empty:
        c1, c2 = st.columns(2)
        tot = int(df_missao['total'].sum())
        c1.metric("Questões na Missão", tot, border=True)
        c2.metric("Precisão", f"{(df_missao['acertos'].sum()/tot*100):.1f}%", border=True)
        df_p = df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        st.plotly_chart(px.line(df_p, x='Data', y='total', markers=True, title="Evolução Diária"), use_container_width=True)
    else: st.info("Registre estudos para ver o gráfico.")

elif selected == "Novo Registro":
    st.title(f"📝 Registro: {concurso_ativo}")
    if concurso_ativo in editais:
        materias = list(editais[concurso_ativo]["materias"].keys())
        mat = st.selectbox("Matéria", materias)
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass_list = editais[concurso_ativo]["materias"].get(mat) or ["Geral"]
            ass = st.selectbox("Assunto", ass_list)
            a = st.number_input("Acertos", 0); t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR REGISTRO"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": concurso_ativo, "materia": mat, "assunto": ass, 
                    "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear(); st.success("Salvo com sucesso!")
    else: st.error("Edital não encontrado.")

elif selected == "Gestão do Edital":
    st.title(f"📑 Gestão: {concurso_ativo}")
    tab1, tab2 = st.tabs(["📚 Matérias e Assuntos", "➕ Novo Concurso Global"])
    
    with tab1:
        if concurso_ativo != "Novo Edital":
            st.subheader(f"Configurando matérias para {concurso_ativo}")
            m_n = st.text_input("Nome da Nova Matéria")
            if st.button("Adicionar Matéria"):
                supabase.table("editais_materias").insert({
                    "concurso": concurso_ativo, "materia": m_n, "topicos": [], 
                    "cargo": editais[concurso_ativo]['cargo'], "data_prova": editais[concurso_ativo]['data_iso']
                }).execute()
                st.cache_data.clear(); st.rerun()
            
            st.markdown("---")
            for m, t in editais[concurso_ativo]["materias"].items():
                with st.expander(f"📚 {m}"):
                    txt = st.text_area("Assuntos (separe por ;)", value="; ".join(t), key=f"t_{m}")
                    if st.button("Salvar Assuntos", key=f"bt_{m}"):
                        novos = [x.strip() for x in txt.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", concurso_ativo).eq("materia", m).execute()
                        st.cache_data.clear(); st.rerun()
                    if st.checkbox(f"Excluir {m}", key=f"c_{m}"):
                        if st.button(f"Confirmar exclusão de {m}", key=f"d_{m}"):
                            supabase.table("editais_materias").delete().eq("concurso", concurso_ativo).eq("materia", m).execute()
                            st.cache_data.clear(); st.rerun()

    with tab2:
        with st.form("novo_c"):
            st.write("Crie um novo edital que ficará disponível na tela inicial.")
            n = st.text_input("Nome do Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("CRIAR CONCURSO"):
                supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": []}).execute()
                st.cache_data.clear(); st.success("Concurso criado! Troque de missão para acessá-lo."); st.rerun()

elif selected == "Histórico":
    st.title(f"📜 Histórico: {concurso_ativo}")
    if not df_missao.empty:
        st.dataframe(df_missao[['Data', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema e Segurança")
    st.subheader("📥 Backup de Segurança (Snapshot)")
    st.write("Baixe uma cópia de todos os seus dados. Se algo sumir, você terá este arquivo.")
    if st.button("Gerar Backup JSON"):
        ed_b = supabase.table("editais_materias").select("*").execute().data
        re_b = supabase.table("registros_estudos").select("*").execute().data
        st.download_button("Clique para Baixar", json.dumps({"editais": ed_b, "registros": re_b}), "backup_squad.json")
    
    st.markdown("---")
    st.subheader("🎟️ Convites")
    if st.button("Gerar Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
