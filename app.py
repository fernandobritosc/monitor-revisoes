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
        VERSION = "13.2.3-flex"
        STATUS = "Matérias Flexíveis"

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
                try:
                    dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except:
                    dt_br = "Erro na data"
            
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

# --- ACESSO ---
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
                else: st.error("Incorreto")
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

# 4. DASHBOARD
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

# 5. NOVO REGISTRO
elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais: st.warning("Crie um edital.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            topicos_lista = editais[conc]["materias"].get(mat) or ["Geral"]
            ass = st.selectbox("Tópico", topicos_lista)
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                taxa_calc = (a/t*100) if t > 0 else 0
                try:
                    supabase.table("registros_estudos").insert({
                        "data_estudo": dt.strftime('%Y-%m-%d'), 
                        "usuario": usuario_atual,
                        "concurso": conc, 
                        "materia": mat, 
                        "assunto": ass, 
                        "acertos": int(a), 
                        "total": int(t), 
                        "taxa": float(taxa_calc)
                    }).execute()
                    st.cache_data.clear()
                    st.success("Salvo!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {str(e)}")

# 6. GESTÃO DE EDITAIS
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Adicionar Matéria"])
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                if not n:
                    st.error("O nome do concurso é obrigatório.")
                else:
                    try:
                        # Blindagem apenas para o concurso principal
                        supabase.table("editais_materias").insert({
                            "concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), 
                            "materia": "Geral", "topicos": []
                        }).execute()
                        st.cache_data.clear()
                        st.success("Concurso criado!")
                        st.rerun()
                    except Exception as e:
                        if "23505" in str(e):
                            st.warning(f"O concurso '{n}' já existe.")
                        else:
                            st.error(f"Erro: {str(e)}")
                    
    with t2:
        if editais:
            sel = st.selectbox("Edital", list(editais.keys()))
            st.success(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Confirmar Adição"):
                if not m_n:
                    st.error("Informe o nome da matéria.")
                # Removida a trava de verificação local para permitir duplicidade se o banco permitir
                # ou apenas tratar o erro se o banco barrar.
                else:
                    try:
                        supabase.table("editais_materias").insert({
                            "concurso": sel, "materia": m_n, "topicos": [], 
                            "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                        }).execute()
                        st.cache_data.clear()
                        st.success("Matéria adicionada!")
                        st.rerun()
                    except Exception as e:
                        # Se o banco ainda tiver a restrição UNIQUE(concurso, materia), avisamos.
                        # Mas agora permitimos tentar a inserção livremente.
                        if "23505" in str(e):
                            st.warning(f"A matéria '{m_n}' já existe para este concurso específico.")
                        else:
                            st.error(f"Erro: {str(e)}")

# 7. HISTÓRICO
elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        st.dataframe(df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']], 
                     use_container_width=True, hide_index=True)

# 8. GESTÃO DE SISTEMA (SÓ FERNANDO)
elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    if st.button("📥 Gerar Snapshot (Backup)"):
        ed = supabase.table("editais_materias").select("*").execute().data
        reg = supabase.table("registros_estudos").select("*").execute().data
        st.download_button("Baixar JSON", json.dumps({"editais": ed, "registros": reg}), "backup.json")
    if st.button("🎟️ Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
