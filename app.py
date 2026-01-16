import streamlit as st
import pandas as pd
import datetime
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

# --- SOLUÇÃO DE ARQUITETURA: QUEBRA DE INFERÊNCIA ---
def formatar_data_br_blindada(data_string):
    """Converte ISO para BR e injeta caractere invisível para impedir inversão do UI engine"""
    if not data_string: return "A definir"
    try:
        dt = datetime.datetime.strptime(data_string, '%Y-%m-%d')
        # Injetamos o caractere \u200b (Zero Width Space)
        return dt.strftime('%d/%m/%Y') + "\u200b"
    except:
        return data_string

@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        # Criamos a coluna de ordenação oculta
        df['ordenacao_temporal'] = pd.to_datetime(df['data_estudo'])
        # Criamos a coluna visual BLINDADA
        df['Data'] = df['ordenacao_temporal'].dt.strftime('%d/%m/%Y').apply(lambda x: x + "\u200b")
    return df

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": formatar_data_br_blindada(row['data_prova']), 
                "data_iso": row['data_prova'], 
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- SISTEMA DE ACESSO ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        with st.form("login_f"):
            u = st.selectbox("Guerreiro", list(users.keys()))
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                if p == users[u]['pin']:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else: st.error("Acesso Negado.")
    st.stop()

# --- AMBIENTE OPERACIONAL (RESTAURADO) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    # MENU COMPLETO RESTAURADO
    selected = option_menu("Menu Tático", 
                           ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"], 
                           icons=["bar-chart", "plus-circle", "trophy", "book-half", "table"], 
                           default_index=0)
    
    st.markdown("---")
    if st.button("🔄 FORÇAR ATUALIZAÇÃO"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 1. DASHBOARD
if selected == "Dashboard":
    st.title("📊 Desempenho")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        tot = int(df_meu['total'].sum())
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum()/tot*100):.1f}%", border=True)
        
        # Gráfico ordenado pela data real, mas exibindo a blindada
        df_plot = df_meu.sort_values('ordenacao_temporal')
        fig = px.line(df_plot, x='Data', y='total', title="Evolução Diária", markers=True)
        fig.update_xaxes(type='category') # Trata a data como texto puro
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem registros no momento.")

# 2. NOVO REGISTRO
elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais: st.warning("Cadastre um edital.")
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
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Estudo registrado!")

# 3. RANKING SQUAD
elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Squad")
    res_all = supabase.table("registros_estudos").select("usuario, total").execute()
    df_all = pd.DataFrame(res_all.data)
    if not df_all.empty:
        df_all['total'] = pd.to_numeric(df_all['total'])
        rank = df_all.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h'), use_container_width=True)

# 4. GESTÃO DE EDITAIS (RESTAURADO COMPLETO)
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Edital", "📚 Matérias"])
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data da Prova")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Edital", list(editais.keys()))
            st.success(f"📍 Cargo: {editais[sel]['cargo']} | 📅 Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({
                    "concurso": sel, "materia": m_n, "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso'], "topicos": []
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

# 5. HISTÓRICO
elif selected == "Histórico":
    st.title("📜 Histórico de Atividades")
    if not df_meu.empty:
        # Exibimos a coluna BLINDADA 'Data'
        exibir = df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']].copy()
        exibir.columns = ['Data de Estudo', 'Concurso', 'Matéria', 'Assunto', 'Acertos', 'Total']
        st.dataframe(exibir.sort_values('Data de Estudo', ascending=False), use_container_width=True, hide_index=True)

# 6. GERAR CONVITES (SÓ PARA VOCÊ)
if usuario_atual == "Fernando Pinheiro":
    if st.sidebar.button("🎟️ Gerar Convite"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.sidebar.code(tk)
