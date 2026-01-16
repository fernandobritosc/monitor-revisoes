import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL PRO ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    header {visibility: hidden;}
    
    .stButton button {
        background-color: #1E1E1E;
        color: #E0E0E0;
        border: 1px solid #333;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    
    div[data-testid="stMetric"] {
        background-color: #0E0E0E;
        padding: 15px 20px;
        border-radius: 8px;
        border: 1px solid #222;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. FUNÇÕES DE DADOS ---

def get_data_countdown(data_iso):
    if not data_iso: return "A definir", None
    try:
        dt_prova = datetime.datetime.strptime(data_iso, '%Y-%m-%d').date()
        hoje = datetime.date.today()
        dias = (dt_prova - hoje).days
        data_fmt = dt_prova.strftime('%d/%m/%Y')

        if dias < 0: return data_fmt, "🏁 Concluída"
        if dias == 0: return data_fmt, "🚨 É HOJE!"
        if dias <= 30: return data_fmt, f"🔥 Reta Final: {dias} dias"
        return data_fmt, f"⏳ Faltam {dias} dias"
    except:
        return data_iso, None

def get_editais():
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
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).order("data_estudo", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def calcular_revisoes(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    revisoes = []
    # Conversão segura
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    
    for _, row in df.iterrows():
        delta = (hoje - row['dt_temp']).days
        motivo = None
        if delta == 1: motivo = "🔥 24 Horas"
        elif delta == 7: motivo = "📅 7 Dias"
        elif delta == 30: motivo = "🧠 30 Dias"
        if motivo:
            revisoes.append({
                "Matéria": row['materia'],
                "Assunto": row['assunto'],
                "Original": row['dt_temp'].strftime('%d/%m'),
                "Tipo": motivo
            })
    return pd.DataFrame(revisoes)

# --- 4. FLUXO PRINCIPAL ---

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# --- TELA 1: CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.markdown("## 💀 CENTRAL DE COMANDO")
    st.markdown("---")
    
    editais = get_editais()
    col_cards, col_admin = st.columns([2, 1], gap="large")
    
    with col_cards:
        st.subheader("🚀 Missões Ativas")
        if not editais:
            st.info("Nenhuma missão ativa.")
        else:
            for nome, dados in editais.items():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1.5])
                    with c1:
                        st.markdown(f"### {nome}")
                        st.caption(f"🎯 {dados['cargo']}")
                    with c2:
                        dt_str, status = get_data_countdown(dados['data_iso'])
                        st.markdown(f"📅 **Prova:** {dt_str}")
                        if status:
                            cor = "#FF4B4B" if "Reta Final" in status or "HOJE" in status else "#E0E0E0"
                            st.markdown(f"<span style='color:{cor}; font-weight:600; font-size:0.9em'>{status}</span>", unsafe_allow_html=True)
                    with c3:
                        st.write("") 
                        if st.button("ACESSAR", key=f"btn_{nome}", use_container_width=True):
                            st.session_state.missao_ativa = nome
                            st.rerun()

    with col_admin:
        st.subheader("🛠️ Gestão Rápida")
        with st.container(border=True):
            st.markdown("**➕ Nova Missão**")
            with st.form("quick_create"):
                nm = st.text_input("Nome (Ex: PF)")
                cg = st.text_input("Cargo")
                dt = st.date_input("Data da Prova", format="DD/MM/YYYY")
                if st.form_submit_button("CRIAR MISSÃO", use_container_width=True):
                    if nm:
                        try:
                            supabase.table("editais_materias").insert({
                                "concurso": nm, "cargo": cg, 
                                "data_prova": dt.strftime('%Y-%m-%d'),
                                "materia": "Geral", "topicos": [], "usuario": "Commander"
                            }).execute()
                        except:
                             supabase.table("editais_materias").insert({
                                "concurso": nm, "cargo": cg, 
                                "data_prova": dt.strftime('%Y-%m-%d'),
                                "materia": "Geral", "topicos": []
                            }).execute()
                        st.toast(f"Missão {nm} criada!")
                        time.sleep(1); st.rerun()

        st.write("") 
        with st.container(border=True):
            st.markdown("**🗑️ Zona de Perigo**")
            lista_del = ["Selecione..."] + list(editais.keys())
            alvo = st.selectbox("Apagar Missão:", lista_del)
            if alvo != "Selecione...":
                st.warning(f"Isso apaga TUDO de '{alvo}'!")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").delete().eq("concurso", alvo).execute()
                    supabase.table("editais_materias").delete().eq("concurso", alvo).execute()
                    st.success("Missão eliminada."); time.sleep(1); st.rerun()

# --- TELA 2: MODO OPERACIONAL ---
else:
    missao = st.session_state.missao_ativa
    dados = get_editais().get(missao, {})
    df = get_stats(missao)
    
    with st.sidebar:
        st.markdown(f"## 🎯 {missao}")
        dt_str, status = get_data_countdown(dados.get('data_iso'))
        if status: st.caption(f"{status}")

        if st.button("🔙 VOLTAR AO COMANDO", use_container_width=True):
            st.session_state.missao_ativa = None
            st.rerun()
            
        st.markdown("---")
        menu = option_menu(
            menu_title=None,
            options=["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"],
            icons=["bar-chart-fill", "repeat", "clock", "gear-fill", "table"],
            default_index=0,
            styles={"nav-link-selected": {"background-color": "#FF4B4B"}}
        )

    if menu == "Dashboard":
        st.title("📊 Painel Tático")
        if df.empty:
            st.info("Inicie os registros para ver estatísticas.")
        else:
            total = int(df['total'].sum())
            acertos = int(df['acertos'].sum())
            erros = total - acertos
            precisao = (acertos /
