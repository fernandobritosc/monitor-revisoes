import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO PREMIUM ---
st.set_page_config(page_title="SQUAD PRO", page_icon="💀", layout="wide", initial_sidebar_state="expanded")

# --- 2. ESTILO CSS PROFISSIONAL (DARK UI) ---
st.markdown("""
<style>
    /* Fonte Moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Remoção de bordas padrão do Streamlit */
    header {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Cartões de Métricas e Missões */
    .stButton button {
        background-color: #1E1E1E;
        color: #FFFFFF;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        width: 100%;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #FF4B4B; /* Cor de Destaque */
        color: white;
        border-color: #FF4B4B;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
    }
    
    /* Inputs Estilizados */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #111;
        border-radius: 6px;
        border: 1px solid #333;
        color: white;
    }
    
    /* Títulos e Headers */
    h1, h2, h3 {
        color: #FAFAFA;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0E0E0E;
        border-right: 1px solid #222;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 4. FUNÇÕES CORE (Sem Cache Excessivo para evitar bugs) ---

def get_editais():
    try:
        # Traz tudo, simplificando a lógica
        res = supabase.table("editais_materias").select("*").execute()
        data = res.data
        editais = {}
        for row in data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {"id": c, "cargo": row.get('cargo'), "data": row.get('data_prova'), "materias": {}}
            if row.get('materia'):
                editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

def get_stats(concurso):
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- 5. TELA INICIAL: O "LOBBY" (ADMINISTRAÇÃO VISUAL) ---

if 'missao_ativa' not in st.session_state:
    st.markdown("# 💀 CENTRAL DE COMANDO")
    st.markdown("---")

    editais = get_editais()
    
    col_missues, col_admin = st.columns([1.5, 1], gap="large")

    # --- LADO ESQUERDO: SELEÇÃO DE MISSÃO (VISUAL) ---
    with col_missues:
        st.subheader("🚀 Missões Ativas")
        if not editais:
            st.info("Nenhuma missão cadastrada. Use o painel ao lado.")
        else:
            # Grid de Cartões
            for nome_concurso, dados in editais.items():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### {nome_concurso}")
                        st.caption(f"Cargo: {dados['cargo']} | Prova: {dados['data'] or 'A definir'}")
                    with c2:
                        st.write("") # Espaçamento
                        if st.button("ACESSAR", key=f"btn_{nome_concurso}"):
                            st.session_state.missao_ativa = nome_concurso
                            st.rerun()
                    st.divider()

    # --- LADO DIREITO: ADMINISTRAÇÃO RÁPIDA ---
    with col_admin:
        st.markdown("### 🛠️ Gestão Rápida")
        
        with st.container(border=True):
            st.markdown("**Novo Edital**")
            with st.form("quick_create"):
                nm = st.text_input("Nome (Ex: PF, Senado)")
                cg = st.text_input("Cargo")
                dt = st.date_input("Data Prova")
                if st.form_submit_button("CRIAR MISSÃO", use_container_width=True):
                    supabase.table("editais_materias").insert({
                        "concurso": nm, "cargo": cg, "data_prova": dt.strftime('%Y-%m-%d'),
                        "materia": "Geral", "topicos": [], "usuario": "Admin"
                    }).execute()
                    st.toast(f"Missão {nm} criada!")
                    time.sleep(1)
                    st.rerun()

        st.write("")
        with st.container(border=True):
            st.markdown("**Zona de Perigo**")
            opcoes_del = list(editais.keys())
            to_delete = st.selectbox("Apagar Missão:", ["Selecione..."] + opcoes_del)
            
            if to_delete != "Selecione...":
                st.warning(f"Isso apagará TUDO de '{to_delete}'")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                    # Delete Nuclear
                    supabase.table("registros_estudos").delete().eq("concurso", to_delete).execute()
                    supabase.table("editais_materias").delete().eq("concurso", to_delete).execute()
                    st.success("Missão eliminada.")
                    time.sleep(1)
                    st.rerun()
    st.stop()

# --- 6. MODO OPERACIONAL (DENTRO DA MISSÃO) ---

missao = st.session_state.missao_ativa
dados_missao = get_editais().get(missao, {})
df_estudos = get_stats(missao)

# --- SIDEBAR PROFISSIONAL ---
with st.sidebar:
    st.markdown(f"### 🎯 {missao}")
    st.caption("Modo Operacional Ativo")
    
    if st.button("🔙 VOLTAR AO COMANDO"):
        del st.session_state.missao_ativa
        st.rerun()
        
    st.markdown("---")
    
    menu = option_menu(
        menu_title=None,
        options=["Dashboard", "Registrar", "Configurar", "Dados"],
        icons=["bar-chart-fill", "plus-circle-fill", "gear-fill", "table"],
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#FF4B4B", "font-size": "16px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"5px", "--hover-color": "#333"},
            "nav-link-selected": {"background-color": "#1E1E1E", "border-left": "3px solid #FF4B4B"},
        }
    )

# --- LÓGICA DAS TELAS ---

if menu == "Dashboard":
    st.markdown(f"## 📊 Visão Geral: {missao}")
    
    if df_estudos.empty:
        st.info("Comece a registrar estudos para ver as métricas.")
    else:
        # Métricas Topo
        col1, col2, col3 = st.columns(3)
        total = int(df_estudos['total'].sum())
        acertos = int(df_estudos['acertos'].sum())
        taxa = (acertos/total*100) if total > 0 else 0
        
        col1.metric("Questões", total)
        col2.metric("Acertos", acertos)
        col3.metric("Precisão", f"{taxa:.1f}%", delta=f"{taxa-80:.1f}% vs Meta")

        # Gráfico
        st.markdown("### Evolução Temporal")
        df_chart = df_estudos.copy()
        df_chart['Data'] = pd.to_datetime(df_chart['data_estudo']).dt.strftime('%d/%m')
        grouped = df_chart.groupby('Data')[['total', 'acertos']].sum().reset_index()
        
        fig = px.area(grouped, x='Data', y=['total', 'acertos'], 
                      color_discrete_sequence=['#333', '#FF4B4B'],
                      template="plotly_dark")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "Registrar":
    st.markdown("## 📝 Novo Registro")
    
    mats = list(dados_missao.get('materias', {}).keys())
    
    if not mats:
        st.warning("⚠️ Configure as matérias no menu 'Configurar' antes de registrar.")
    else:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                mat = st.selectbox("Matéria", mats)
                topicos = dados_missao['materias'].get(mat, []) or ["Geral"]
                assunto = st.selectbox("Assunto", topicos)
            with c2:
                dt = st.date_input("Data", datetime.date.today())
            
            st.divider()
            
            c3, c4 = st.columns(2)
            acertos = c3.number_input("Acertos", min_value=0, step=1)
            total = c4.number_input("Total", min_value=1, step=1)
            
            if st.button("SALVAR REGISTRO", type="primary", use_container_width=True):
                supabase.table("registros_estudos").insert({
                    "concurso": missao, "materia": mat, "assunto": assunto,
                    "data_estudo": dt.strftime('%Y-%m-%d'),
                    "acertos": acertos, "total": total, "taxa": (acertos/total)*100,
                    "usuario": "Admin"
                }).execute()
                st.toast("Registro Salvo com Sucesso!", icon="✅")
                time.sleep(0.5)

elif menu == "Configurar":
    st.markdown("## ⚙️ Arquitetura do Edital")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("#### Adicionar Matéria")
        with st.form("add_mat"):
            nm_mat = st.text_input("Nome da Matéria")
            if st.form_submit_button("ADICIONAR"):
                # Garante que não duplica campos de edital, apenas add materia
                supabase.table("editais_materias").insert({
                    "concurso": missao, "materia": nm_mat, "topicos": [],
                    "cargo": dados_missao.get('cargo'), "data_prova": dados_missao.get('data_iso'),
                    "usuario": "Admin"
                }).execute()
                st.rerun()
                
    with c2:
        st.markdown("#### Tópicos por Matéria")
        materias = dados_missao.get('materias', {})
        if not materias:
            st.info("Nenhuma matéria cadastrada.")
        
        for m, t in materias.items():
            with st.expander(f"📚 {m}"):
                current_topics = "; ".join(t)
                new_topics = st.text_area(f"Tópicos de {m} (separe por ;)", value=current_topics, key=f"txt_{m}")
                
                col_save, col_del = st.columns([4, 1])
                if col_save.button("Salvar Tópicos", key=f"save_{m}"):
                    t_list = [x.strip() for x in new_topics.split(";") if x.strip()]
                    supabase.table("editais_materias").update({"topicos": t_list}).eq("concurso", missao).eq("materia", m).execute()
                    st.toast("Atualizado!")
                    time.sleep(0.5); st.rerun()
                
                if col_del.button("🗑️", key=f"del_{m}", help="Excluir Matéria"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()

elif menu == "Dados":
    st.markdown("## 📜 Histórico Completo")
    if not df_estudos.empty:
        st.dataframe(
            df_estudos[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']],
            use_container_width=True,
            hide_index=True
        )
        if st.button("Limpar Histórico Completo"):
             supabase.table("registros_estudos").delete().eq("concurso", missao).execute()
             st.rerun()
    else:
        st.info("Sem dados.")
