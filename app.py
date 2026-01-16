import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL PRO (CSS INJETADO) ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

# Estilo CSS para visual "Enterprise"
st.markdown("""
<style>
    /* Importando fonte Inter (padrão de apps modernos) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Cabeçalho limpo */
    header {visibility: hidden;}
    
    /* Botões com estilo Hover e Borda */
    .stButton button {
        background-color: #1E1E1E;
        color: #E0E0E0;
        border: 1px solid #333;
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
        transform: scale(1.02);
    }
    
    /* Cartões de Métricas */
    div[data-testid="stMetric"] {
        background-color: #111;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #222;
    }
    
    /* Sidebar mais escura */
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. FUNÇÕES DE DADOS (SIMPLIFICADAS PARA SINGLE PLAYER) ---

def get_data_br(data_iso):
    """Converte AAAA-MM-DD para DD/MM/AAAA"""
    if not data_iso: return "A definir"
    try:
        return datetime.datetime.strptime(data_iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return data_iso

def get_editais():
    # Traz tudo sem filtrar usuário (Single Player Mode)
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {
                    "cargo": row.get('cargo') or "Geral", 
                    "data_iso": row.get('data_prova'),
                    "materias": {}
                }
            if row.get('materia'):
                editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

def get_stats(concurso):
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- 4. FLUXO PRINCIPAL ---

# Inicializa estado de navegação
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# --- TELA 1: CENTRAL DE COMANDO (DASHBOARD GERAL) ---
if st.session_state.missao_ativa is None:
    st.markdown("## 💀 CENTRAL DE COMANDO")
    st.markdown("---")
    
    editais = get_editais()
    
    # Layout de 2 Colunas: Missões (Esquerda) e Gestão (Direita)
    col_cards, col_admin = st.columns([2, 1], gap="large")
    
    with col_cards:
        st.subheader("🚀 Missões Ativas")
        if not editais:
            st.info("Nenhuma missão ativa. Crie uma ao lado 👉")
        else:
            # Renderiza cartões visuais para cada concurso
            for nome, dados in editais.items():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1.5])
                    with c1:
                        st.markdown(f"### {nome}")
                        st.caption(f"🎯 {dados['cargo']}")
                    with c2:
                        dt_prova = get_data_br(dados['data_iso'])
                        st.markdown(f"📅 **Prova:** {dt_prova}")
                    with c3:
                        st.write("") # Espaço para alinhar botão
                        if st.button("ACESSAR", key=f"btn_{nome}", use_container_width=True):
                            st.session_state.missao_ativa = nome
                            st.rerun()

    with col_admin:
        st.subheader("🛠️ Gestão Rápida")
        
        # CARD DE CRIAÇÃO
        with st.container(border=True):
            st.markdown("**➕ Nova Missão**")
            with st.form("quick_create"):
                nm = st.text_input("Nome (Ex: PF, PC-GO)")
                cg = st.text_input("Cargo")
                # CORREÇÃO DA DATA: Input brasileiro
                dt = st.date_input("Data da Prova", format="DD/MM/YYYY")
                
                if st.form_submit_button("CRIAR MISSÃO", use_container_width=True):
                    if nm:
                        # Grava no banco como AAAA-MM-DD (Padrão ISO), mas input foi BR
                        supabase.table("editais_materias").insert({
                            "concurso": nm, "cargo": cg, 
                            "data_prova": dt.strftime('%Y-%m-%d'), # Converte para banco
                            "materia": "Geral", "topicos": [], "usuario": "Commander"
                        }).execute()
                        st.toast(f"Missão {nm} criada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Digite um nome para a missão.")

        st.write("") # Espaço
        
        # CARD DE EXCLUSÃO (ZONA DE PERIGO)
        with st.container(border=True):
            st.markdown("**🗑️ Zona de Perigo**")
            lista_del = ["Selecione..."] + list(editais.keys())
            alvo = st.selectbox("Apagar Missão:", lista_del)
            
            if alvo != "Selecione...":
                st.warning(f"Isso apagará TODO o histórico de '{alvo}'.")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                    # Delete em Cascata (Nuclear)
                    supabase.table("registros_estudos").delete().eq("concurso", alvo).execute()
                    supabase.table("editais_materias").delete().eq("concurso", alvo).execute()
                    st.success("Missão eliminada.")
                    time.sleep(1)
                    st.rerun()

# --- TELA 2: MODO OPERACIONAL (DENTRO DA MISSÃO) ---
else:
    missao = st.session_state.missao_ativa
    dados = get_editais().get(missao, {})
    df = get_stats(missao)
    
    # --- SIDEBAR DE NAVEGAÇÃO ---
    with st.sidebar:
        st.markdown(f"## 🎯 {missao}")
        if st.button("🔙 VOLTAR AO COMANDO", use_container_width=True):
            st.session_state.missao_ativa = None
            st.rerun()
            
        st.markdown("---")
        menu = option_menu(
            menu_title=None,
            options=["Dashboard", "Registrar", "Configurar", "Histórico"],
            icons=["bar-chart-fill", "pencil-square", "gear-fill", "clock-history"],
            default_index=0,
            styles={
                "nav-link-selected": {"background-color": "#FF4B4B"},
            }
        )

    # --- CONTEÚDO DAS ABAS ---
    
    if menu == "Dashboard":
        st.title("📊 Indicadores de Combate")
        if df.empty:
            st.info("Nenhum dado registrado. Vá em 'Registrar' para começar.")
        else:
            # Métricas
            c1, c2, c3 = st.columns(3)
            total = int(df['total'].sum())
            acertos = int(df['acertos'].sum())
            precisao = (acertos / total * 100) if total > 0 else 0
            
            c1.metric("Questões Totais", total, border=True)
            c2.metric("Acertos Totais", acertos, border=True)
            c3.metric("Precisão Geral", f"{precisao:.1f}%", border=True)
            
            # Gráfico de Evolução
            st.markdown("### 📈 Evolução Diária")
            df['Data'] = pd.to_datetime(df['data_estudo']).dt.strftime('%d/%m/%Y')
            df_chart = df.groupby('Data')[['total', 'acertos']].sum().reset_index()
            
            fig = px.area(df_chart, x='Data', y=['total', 'acertos'], 
                          color_discrete_sequence=['#333333', '#FF4B4B'], template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    elif menu == "Registrar":
        st.title("📝 Novo Registro")
        materias = list(dados.get('materias', {}).keys())
        
        if not materias:
            st.warning("⚠️ Você precisa adicionar matérias em 'Configurar' antes de registrar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    mat = st.selectbox("Matéria", materias)
                    topicos = dados['materias'].get(mat, []) or ["Geral"]
                    assunto = st.selectbox("Assunto", topicos)
                with c2:
                    # DATA CORRIGIDA NO INPUT
                    dt = st.date_input("Data do Estudo", format="DD/MM/YYYY")
                
                st.divider()
                c3, c4 = st.columns(2)
                acertos = c3.number_input("Acertos", min_value=0, step=1)
                total = c4.number_input("Total Resolvido", min_value=1, step=1)
                
                if st.button("SALVAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao,
                        "materia": mat,
                        "assunto": assunto,
                        "data_estudo": dt.strftime('%Y-%m-%d'), # Grava ISO
                        "acertos": acertos,
                        "total": total,
                        "taxa": (acertos/total)*100,
                        "usuario": "Commander"
                    }).execute()
                    st.toast("Registro salvo!", icon="🔥")
                    time.sleep(0.5)

    elif menu == "Configurar":
        st.title("⚙️ Configuração do Edital")
        
        c1, c2 = st.columns([1, 2], gap="medium")
        
        with c1:
            st.markdown("#### Nova Matéria")
            with st.form("add_mat"):
                nm = st.text_input("Nome da Matéria")
                if st.form_submit_button("ADICIONAR"):
                    supabase.table("editais_materias").insert({
                        "concurso": missao, "materia": nm, "topicos": [],
                        "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso'),
                        "usuario": "Commander"
                    }).execute()
                    st.rerun()
        
        with c2:
            st.markdown("#### Matérias e Tópicos")
            if not dados.get('materias'):
                st.info("Sem matérias cadastradas.")
            
            for m, t in dados.get('materias', {}).items():
                with st.expander(f"📚 {m}"):
                    current = "; ".join(t)
                    new_tops = st.text_area(f"Tópicos de {m} (separe por ;)", value=current)
                    
                    col_save, col_del = st.columns([4, 1])
                    if col_save.button("Salvar", key=f"s_{m}"):
                        l = [x.strip() for x in new_tops.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                        st.toast("Atualizado!")
                        time.sleep(0.5); st.rerun()
                    
                    if col_del.button("🗑️", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()

    elif menu == "Histórico":
        st.title("📜 Histórico Detalhado")
        if not df.empty:
            # Converte data para visualização
            df_view = df.copy()
            df_view['data_estudo'] = pd.to_datetime(df_view['data_estudo']).dt.strftime('%d/%m/%Y')
            
            st.dataframe(
                df_view[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem dados.")
