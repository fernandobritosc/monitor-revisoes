import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# Proteção para o import de versão
try:
    import version
except ImportError:
    class version:
        VERSION = "14.0.0-temp"
        STATUS = "Restaurando Funções"

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
            dt_br = "A definir"
            if dt_raw:
                try: dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: dt_br = "Erro na data"
            
            editais[conc] = {
                "cargo": row.get('cargo') or "Não informado", 
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        
        materia = row.get('materia')
        if materia:
            editais[conc]["materias"][materia] = row.get('topicos') or []
            
    return editais

def db_get_tokens():
    res = supabase.table("tokens_convite").select("*").eq("usado", False).execute()
    return [t['codigo'] for t in res.data]

# --- LOGIN E CADASTRO (RESTAURADO) ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        tab_login, tab_cad = st.tabs(["Acessar Base", "Novo Guerreiro"])
        
        with tab_login:
            with st.form("login_form"):
                u = st.selectbox("Guerreiro", list(users.keys()) if users else ["Nenhum cadastrado"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users and p == users[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("Acesso Negado.")
        
        with tab_cad:
            with st.form("cadastro_form"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Nome")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA", use_container_width=True):
                    tokens_ativos = db_get_tokens()
                    if tk_in in tokens_ativos:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Guerreiro Recrutado! Faça o login.")
                    else: st.error("Token Inválido ou já usado.")
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
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()
    if st.button("Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 1. DASHBOARD
if selected == "Dashboard":
    st.title("📊 Painel Analytics")
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

# 2. NOVO REGISTRO (RESTAURADO COM ASSUNTOS)
elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais: st.warning("Crie um edital primeiro.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            # Busca assuntos cadastrados ou coloca "Geral" se estiver vazio
            assuntos_cadastrados = editais[conc]["materias"].get(mat)
            ass = st.selectbox("Assunto/Tópico", assuntos_cadastrados if assuntos_cadastrados else ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

# 4. GESTÃO DE EDITAIS (RESTAURADO COM GESTÃO DE TÓPICOS)
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Matérias e Assuntos"])
    
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), 
                    "materia": "Geral", "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()

    with t2:
        if editais:
            sel = st.selectbox("Escolha o Edital", list(editais.keys()))
            st.success(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
            
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar Matéria"):
                try:
                    supabase.table("editais_materias").insert({
                        "concurso": sel, "materia": m_n, "topicos": [], 
                        "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                    }).execute()
                    st.cache_data.clear()
                    st.rerun()
                except: st.warning("Matéria já existe.")

            st.markdown("---")
            st.subheader("Editando Assuntos por Matéria")
            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    # Área para editar os tópicos separados por ponto e vírgula
                    txt_assuntos = st.text_area(f"Assuntos para {m} (separe por ;)", value="; ".join(t), key=f"txt_{m}")
                    if st.button(f"Atualizar {m}", key=f"btn_{m}"):
                        novos_t = [x.strip() for x in txt_assuntos.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos_t}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear()
                        st.rerun()

# 5. HISTÓRICO
elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        st.dataframe(df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']], 
                     use_container_width=True, hide_index=True)

# 6. GESTÃO DE SISTEMA (FERNANDO)
elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📥 Gerar Backup JSON"):
            ed = supabase.table("editais_materias").select("*").execute().data
            reg = supabase.table("registros_estudos").select("*").execute().data
            st.download_button("Baixar", json.dumps({"editais": ed, "registros": reg}), "backup.json")
    with c2:
        if st.button("🎟️ Novo Token Convite"):
            tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
            supabase.table("tokens_convite").insert({"codigo": tk}).execute()
            st.code(tk)
