import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
import time
import calendar
from supabase import create_client
from streamlit_option_menu import option_menu

# ============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & CONEXÃO
# ============================================================================
st.set_page_config(
    page_title="Monitor Pro | Neural Interface",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conexão com Supabase (Substituindo database.py)
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erro de Conexão com Supabase: {e}")
        st.stop()

supabase = init_connection()

# ============================================================================
# 2. DESIGN SYSTEM - CYBERPUNK / NEON / GLASSMORPHISM
# ============================================================================
COLORS = {
    "primary": "#8B5CF6",      # Roxo Neon
    "secondary": "#06B6D4",    # Ciano Neon
    "accent": "#EC4899",       # Rosa
    "success": "#10B981",      # Verde
    "warning": "#F59E0B",      # Laranja
    "danger": "#EF4444",       # Vermelho
    "bg_dark": "#0E1117",      # Fundo Profundo
    "bg_card": "rgba(14, 17, 23, 0.7)", 
    "text_primary": "#FFFFFF",
    "text_secondary": "#94A3B8",
    "border": "rgba(139, 92, 246, 0.2)",
}

st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Montserrat:wght@400;700;900&family=JetBrains+Mono:wght@400&display=swap');

    :root {
        --primary: #8B5CF6;
        --secondary: #06B6D4;
        --bg-deep: #050505;
        --glass-bg: rgba(20, 20, 35, 0.7);
        --neon-glow: 0 0 10px rgba(139, 92, 246, 0.5);
    }

    /* Base Styling */
    .stApp {
        background-color: var(--bg-deep);
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        color: white !important;
        text-transform: uppercase;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0A0A10;
        border-right: 1px solid rgba(139, 92, 246, 0.1);
    }

    /* Glassmorphism Cards */
    .modern-card {
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .modern-card:hover {
        border-color: var(--secondary);
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.15);
    }

    /* Inputs Modernos */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: var(--secondary) !important;
        box-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, var(--primary) 0%, #6d28d9 100%);
        color: white;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(139, 92, 246, 0.6);
    }
    .stButton button:active {
        transform: scale(0.98);
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0E1117; 
    }
    ::-webkit-scrollbar-thumb {
        background: #334155; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary); 
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-family: 'Montserrat', sans-serif !important;
        background: linear-gradient(90deg, #fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Badges */
    .badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        border: 1px solid transparent;
    }
    .badge-green { background: rgba(16, 185, 129, 0.1); color: #10B981; border-color: rgba(16, 185, 129, 0.2); }
    .badge-yellow { background: rgba(245, 158, 11, 0.1); color: #F59E0B; border-color: rgba(245, 158, 11, 0.2); }
    .badge-red { background: rgba(239, 68, 68, 0.1); color: #EF4444; border-color: rgba(239, 68, 68, 0.2); }
    .badge-gray { background: rgba(255, 255, 255, 0.05); color: #94A3B8; border-color: rgba(255, 255, 255, 0.1); }

    /* Progress Bar custom */
    .modern-progress-container {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        height: 8px;
        width: 100%;
        overflow: hidden;
    }
    .modern-progress-fill {
        background: linear-gradient(90deg, var(--secondary), var(--primary));
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    /* Table Styling */
    .stDataFrame {
        border: 1px solid rgba(139, 92, 246, 0.1) !important;
        border-radius: 10px;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. LÓGICA E FUNÇÕES AUXILIARES
# ============================================================================

def get_editais(client):
    """
    Busca e estrutura os editais do Supabase.
    Retorna: Dict { 'NomeConcurso': {'cargo': '...', 'materias': {...}} }
    """
    try:
        response = client.table("editais_materias").select("*").execute()
        data = response.data
        if not data:
            return {}
        
        editais = {}
        for item in data:
            concurso = item['concurso']
            if concurso not in editais:
                editais[concurso] = {
                    'cargo': item.get('cargo', 'Geral'),
                    'materias': {},
                    'data_prova': item.get('data_prova')
                }
            
            # Adiciona matéria e seus tópicos
            materia = item['materia']
            topicos = item.get('topicos', []) or []
            editais[concurso]['materias'][materia] = topicos
            
        return editais
    except Exception as e:
        st.error(f"Erro ao buscar editais: {e}")
        return {}

def excluir_concurso_completo(client, concurso_nome):
    """Remove todas as matérias e registros de um concurso."""
    try:
        # 1. Deletar registros de estudo
        client.table("registros_estudos").delete().eq("concurso", concurso_nome).execute()
        # 2. Deletar estrutura do edital
        client.table("editais_materias").delete().eq("concurso", concurso_nome).execute()
        return True
    except Exception as e:
        print(f"Erro ao excluir concurso: {e}")
        return False

def processar_assuntos_em_massa(texto, separador=";"):
    """
    Processa um texto com múltiplos assuntos separados por um separador.
    Retorna uma lista limpa de assuntos.
    """
    if not texto:
        return []
    
    texto = texto.strip()
    
    if separador == ";":
        assuntos = texto.split(";")
    elif separador == ",":
        assuntos = texto.split(",")
    elif separador == "linha":
        assuntos = texto.split("\n")
    elif separador == "ponto":
        assuntos = texto.split(".")
    else:
        assuntos = [texto]
    
    assuntos_limpos = []
    for assunto in assuntos:
        assunto = assunto.strip()
        assunto = re.sub(r'^[^a-zA-Z0-9]*|[^a-zA-Z0-9]*$', '', assunto)
        if assunto:
            assuntos_limpos.append(assunto)
    
    return assuntos_limpos

# --- UI Helpers ---

def render_circular_progress(percentage, label, value, color_start=None, color_end=None, size=120, icon=""):
    """Renderiza anel de progresso SVG"""
    if color_start is None: color_start = COLORS["primary"]
    if color_end is None: color_end = COLORS["secondary"]
    
    circumference = 283
    offset = circumference - (percentage / 100 * circumference)
    gradient_id = f"grad_{label.replace(' ', '_')}_{int(time.time())}" # Unique ID
    
    st.markdown(f"""
        <div class="modern-card" style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:180px; padding:20px;">
            <div style="position: relative; width: {size}px; height: {size}px; margin-bottom: 10px;">
                <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width: 100%; height: 100%;">
                    <defs>
                        <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:{color_start};stop-opacity:1" />
                            <stop offset="100%" style="stop-color:{color_end};stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <circle cx="50" cy="50" r="45" stroke="rgba(255,255,255,0.05)" stroke-width="8" fill="none"/>
                    <circle cx="50" cy="50" r="45" stroke="url(#{gradient_id})" stroke-width="8" 
                            fill="none" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
                            stroke-linecap="round" style="transition: stroke-dashoffset 1s ease;"/>
                </svg>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                    <div style="font-size: 1.1rem; margin-bottom: 2px;">{icon}</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #fff;">{value}</div>
                </div>
            </div>
            <div style="color: #94A3B8; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">{label}</div>
        </div>
    """, unsafe_allow_html=True)

def render_metric_card_modern(label, value, icon="📊", subtitle=None):
    st.markdown(f"""
        <div class="modern-card" style="text-align:center; min-height:140px; display:flex; flex-direction:column; justify-content:center;">
            <div style="font-size: 2rem; margin-bottom: 8px;">{icon}</div>
            <div style="color: #94A3B8; font-size: 0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">{label}</div>
            <div style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']}); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{value}</div>
            {f'<div style="color: #64748b; font-size: 0.7rem;">{subtitle}</div>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)

# --- Formatters & Calculators ---

def formatar_tempo_para_bigint(tempo_str):
    try:
        tempo_str = str(tempo_str).strip()
        if len(tempo_str) == 4:
            horas, minutos = int(tempo_str[:2]), int(tempo_str[2:])
            return horas * 60 + minutos
        elif len(tempo_str) == 3:
            horas, minutos = int(tempo_str[0]), int(tempo_str[1:])
            return horas * 60 + minutos
        else: return int(tempo_str)
    except: return 0

def formatar_minutos(minutos_totais):
    try:
        minutos = int(minutos_totais)
        return f"{minutos // 60}h{minutos % 60:02d}m"
    except: return "0h00m"

def calcular_streak(df):
    if df is None or df.empty or 'data_estudo' not in df.columns: return 0
    dates = sorted(pd.to_datetime(df['data_estudo']).dt.date.dropna().unique(), reverse=True)
    if not dates: return 0
    
    today = datetime.date.today()
    streak = 0
    current = today
    
    # Check if studied today to start count, else check yesterday
    if dates[0] == today:
        streak = 1
        current = today - timedelta(days=1)
    elif dates[0] == today - timedelta(days=1):
        streak = 0 # Will increment in loop
        current = today - timedelta(days=1)
    else:
        return 0

    for d in dates:
        if d == today: continue
        if d == current:
            streak += 1
            current -= timedelta(days=1)
        else:
            break
    return streak

def calcular_recorde_streak(df):
    if df is None or df.empty or 'data_estudo' not in df.columns: return 0
    dates = sorted(pd.to_datetime(df['data_estudo']).dt.date.dropna().unique())
    if not dates: return 0
    
    max_streak = 0
    current_streak = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current_streak += 1
        else:
            max_streak = max(max_streak, current_streak)
            current_streak = 1
    return max(max_streak, current_streak)

def tempo_recomendado_rev24h(dificuldade):
    tempos = {
        "🟢 Fácil": (2, "Leitura rápida"),
        "🟡 Médio": (8, "Grifos + 5 questões"),
        "🔴 Difícil": (18, "Active Recall + Questões")
    }
    return tempos.get(dificuldade, (5, "Padrão"))

# --- CORE LOGIC: REVISÕES ---

@st.cache_data(ttl=60)
def calcular_revisoes_pendentes(df, filtro_rev, filtro_dif):
    hoje = datetime.date.today()
    pend = []
    if df.empty: return pend

    for _, row in df.iterrows():
        try:
            dt_est = pd.to_datetime(row['data_estudo']).date()
            dif = row.get('dificuldade', '🟡 Médio')
            tx = row.get('taxa', 0)
            
            # Revisão 24h
            if not row.get('rev_24h'):
                dt_due = dt_est + timedelta(days=1)
                atraso = (hoje - dt_due).days
                if filtro_rev == "Todas (incluindo futuras)" or dt_due <= hoje:
                    pend.append({**row, "tipo": "Revisão 24h", "col": "rev_24h", "data_prevista": dt_due, "atraso": atraso})
            
            # Revisões de Ciclo (Espaçamento Dinâmico)
            else:
                intervalo = 7
                if dif == "🟢 Fácil": intervalo = 15 if tx > 80 else 7
                elif dif == "🔴 Difícil": intervalo = 3 if tx < 70 else 5
                
                col_target = "rev_07d" if intervalo <= 7 else "rev_15d"
                label = f"Revisão {intervalo}d"
                
                if not row.get(col_target):
                    dt_due = dt_est + timedelta(days=intervalo)
                    atraso = (hoje - dt_due).days
                    if filtro_rev == "Todas (incluindo futuras)" or dt_due <= hoje:
                        pend.append({**row, "tipo": label, "col": col_target, "data_prevista": dt_due, "atraso": atraso})
                        
        except Exception: continue # Skip corrupted rows

    if filtro_dif != "Todas":
        pend = [p for p in pend if p['dificuldade'] == filtro_dif]
        
    return pend

# ============================================================================
# 4. INICIALIZAÇÃO DE ESTADO
# ============================================================================

if 'missao_ativa' not in st.session_state:
    try:
        ed = get_editais(supabase)
        st.session_state.missao_ativa = list(ed.keys())[0] if ed else None
    except: st.session_state.missao_ativa = None

if 'meta_horas_semana' not in st.session_state: st.session_state.meta_horas_semana = 22
if 'meta_questoes_semana' not in st.session_state: st.session_state.meta_questoes_semana = 350
if 'editando_metas' not in st.session_state: st.session_state.editando_metas = False
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'renomear_materia' not in st.session_state: st.session_state.renomear_materia = {}

# ============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ============================================================================

# --- TELA DE SELEÇÃO INICIAL (Se nenhuma missão ativa) ---
if st.session_state.missao_ativa is None:
    st.markdown('<div style="text-align:center; padding:50px;"><h1 style="font-size:3rem;">🎯 MONITOR PRO</h1></div>', unsafe_allow_html=True)
    
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 Missões Ativas", "➕ Novo Cadastro"])
    
    with tabs[0]:
        if not ed:
            st.info("Nenhuma missão encontrada. Cadastre sua primeira missão!")
        else:
            cols = st.columns(2)
            for i, (nome, dados) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="modern-card">
                            <h3 style="color:#fff; margin-bottom:5px;">{nome}</h3>
                            <p style="color:#94a3b8;">{dados['cargo']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"ACESSAR", key=f"btn_{nome}", use_container_width=True, type="primary"):
                        st.session_state.missao_ativa = nome
                        st.rerun()

    with tabs[1]:
        with st.form("new_mission"):
            st.markdown("### 📝 Nova Missão")
            nome = st.text_input("Nome do Concurso", placeholder="Ex: Receita Federal")
            cargo = st.text_input("Cargo", placeholder="Ex: Auditor")
            data_prova = st.date_input("Data da Prova (Opcional)", value=None)
            
            if st.form_submit_button("INICIAR MISSÃO", use_container_width=True):
                if nome and cargo:
                    try:
                        payload = {"concurso": nome, "cargo": cargo, "materia": "Geral", "topicos": ["Introdução"]}
                        if data_prova: payload["data_prova"] = str(data_prova)
                        supabase.table("editais_materias").insert(payload).execute()
                        st.success(f"Missão {nome} criada!")
                        st.session_state.missao_ativa = nome
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                else:
                    st.warning("Preencha nome e cargo.")

# --- APLICAÇÃO PRINCIPAL ---
else:
    missao = st.session_state.missao_ativa
    
    # Busca dados principais
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()

    dados_edital = get_editais(supabase).get(missao, {})
    data_prova_str = dados_edital.get('data_prova')
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="background:rgba(139,92,246,0.1); width:60px; height:60px; border-radius:12px; margin:0 auto 10px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(139,92,246,0.3);">
                <span style="font-size:30px;">🧠</span>
            </div>
            <h2 style="margin:0; font-size:1.5rem;">MONITOR <span style="background:white; color:black; padding:2px 6px; border-radius:4px; font-size:1rem; vertical-align:middle;">PRO</span></h2>
        </div>
        """, unsafe_allow_html=True)
        
        menu_selecionado = option_menu(
            menu_title=None,
            options=["HOME", "REVISÕES", "REGISTRAR", "DASHBOARD", "HISTÓRICO", "CONFIGURAR"],
            icons=["house", "arrow-repeat", "pencil-square", "graph-up-arrow", "clock-history", "gear"],
            default_index=0,
            styles={
                "container": {"background-color": "transparent", "padding": "0"},
                "icon": {"color": "#94A3B8"}, 
                "nav-link": {"font-family": "Montserrat", "font-size": "14px", "margin": "5px", "--hover-color": "#1e1e2d"},
                "nav-link-selected": {"background-color": "rgba(139, 92, 246, 0.2)", "color": "#fff", "border-left": "4px solid #06B6D4"}
            }
        )
        
        st.divider()
        st.markdown(f"**Missão:** {missao}")
        if st.button("Sair / Trocar"):
            st.session_state.missao_ativa = None
            st.rerun()

    # --- PÁGINAS ---
    
    # 1. HOME
    if menu_selecionado == "HOME":
        st.markdown(f"## 🏠 Visão Geral: <span style='color:#06B6D4'>{missao}</span>", unsafe_allow_html=True)
        
        if df.empty:
            st.info("👋 Bem-vindo! Comece registrando seus estudos na aba 'REGISTRAR'.")
        else:
            # Métricas Topo
            total_mins = df['tempo'].sum() if 'tempo' in df.columns else 0
            total_q = df['total'].sum()
            acertos = df['acertos'].sum()
            precisao = (acertos / total_q * 100) if total_q > 0 else 0
            
            # Dias p/ Prova
            dias_restantes = None
            if data_prova_str:
                try:
                    dt_p = pd.to_datetime(data_prova_str).date()
                    dias_restantes = (dt_p - datetime.date.today()).days
                except: pass

            c1, c2, c3, c4 = st.columns(4)
            with c1: render_circular_progress(min(total_mins/6000*100, 100), "TEMPO TOTAL", formatar_minutos(total_mins), icon="⏱️")
            with c2: render_circular_progress(precisao, "PRECISÃO", f"{precisao:.0f}%", icon="🎯", color_start=COLORS['success'] if precisao>80 else COLORS['warning'])
            with c3: render_circular_progress(min(total_q/1000*100, 100), "QUESTÕES", str(int(total_q)), icon="📝", color_start=COLORS['accent'])
            with c4: 
                if dias_restantes is not None:
                     render_circular_progress(max(0, 100-dias_restantes), "DIAS P/ PROVA", str(dias_restantes), icon="📅", color_start=COLORS['danger'])
                else:
                    render_metric_card_modern("DIAS P/ PROVA", "—", icon="📅")

            st.markdown("### 🔥 Constância")
            streak = calcular_streak(df)
            recorde = calcular_recorde_streak(df)
            
            sc1, sc2, sc3 = st.columns(3)
            with sc1: render_metric_card_modern("STREAK ATUAL", f"{streak} dias", icon="🔥", subtitle="Mantenha o fogo aceso!")
            with sc2: render_metric_card_modern("RECORDE", f"{recorde} dias", icon="🏆", subtitle="Sua melhor marca")
            with sc3:
                hoje = datetime.date.today()
                mes_atual_count = len(df[pd.to_datetime(df['data_estudo']).dt.month == hoje.month]['data_estudo'].unique())
                render_metric_card_modern("ESTE MÊS", f"{mes_atual_count} dias", icon="📅", subtitle="Dias estudados no mês")

            st.markdown("### 📊 Desempenho por Matéria")
            if not df.empty:
                df_grp = df.groupby('materia').agg({'tempo': 'sum', 'acertos': 'sum', 'total': 'sum'}).reset_index()
                df_grp['taxa'] = (df_grp['acertos'] / df_grp['total'] * 100).fillna(0)
                df_grp = df_grp.sort_values('tempo', ascending=False)
                
                # Tabela estilizada
                st.dataframe(
                    df_grp[['materia', 'total', 'taxa']],
                    column_config={
                        "materia": "Disciplina",
                        "total": st.column_config.NumberColumn("Questões", format="%d"),
                        "taxa": st.column_config.ProgressColumn("Precisão", format="%.1f%%", min_value=0, max_value=100)
                    },
                    hide_index=True,
                    use_container_width=True
                )

    # 2. REVISÕES
    elif menu_selecionado == "REVISÕES":
        st.markdown("## 🔄 Radar de Revisões")
        
        c1, c2 = st.columns([2, 1])
        vis = c1.segmented_control("Filtro", ["Pendentes/Hoje", "Todas (incluindo futuras)"], default="Pendentes/Hoje")
        dif = c2.segmented_control("Dificuldade", ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"], default="Todas")
        
        pend = calcular_revisoes_pendentes(df, vis, dif)
        
        if not pend:
            st.success("🎉 Tudo limpo! Você está em dia com as revisões.")
        else:
            # Ordenar por atraso
            pend = sorted(pend, key=lambda x: x['atraso'], reverse=True)
            
            # Resumo de pendências
            st.markdown("##### 📊 Resumo de Pendências")
            r1, r2, r3 = st.columns(3)
            r1.metric("🔴 Difíceis", len([p for p in pend if p['dificuldade'] == "🔴 Difícil"]))
            r2.metric("🟡 Médias", len([p for p in pend if p['dificuldade'] == "🟡 Médio"]))
            r3.metric("🟢 Fáceis", len([p for p in pend if p['dificuldade'] == "🟢 Fácil"]))
            st.divider()

            for p in pend:
                with st.container():
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    ci, ca = st.columns([3, 1])
                    with ci:
                        cor_atraso = "#EF4444" if p['atraso'] > 0 else "#10B981" if p['atraso'] == 0 else "#3B82F6"
                        txt_atraso = f"{p['atraso']} dias atrasado" if p['atraso'] > 0 else "Vence Hoje" if p['atraso'] == 0 else f"Futuro ({abs(p['atraso'])}d)"
                        
                        # Tempo recomendado
                        tempo_rec, desc_rec = tempo_recomendado_rev24h(p['dificuldade'])
                        
                        st.markdown(f"""
                        <div style="display:flex; gap:10px; margin-bottom:5px;">
                            <span class="badge" style="background:{cor_atraso}20; color:{cor_atraso}; border:1px solid {cor_atraso}40;">{txt_atraso}</span>
                            <span class="badge badge-gray">{p['tipo']}</span>
                            <span class="badge badge-gray">{p['dificuldade']}</span>
                        </div>
                        <h3 style="margin:5px 0; color:white;">{p['materia']}</h3>
                        <p style="color:#94A3B8; font-size:0.9rem;">{p['assunto']}</p>
                        <p style="color:#FF8E8E; font-size:0.75rem; margin-top:5px;">⏱️ Recomendado: {tempo_rec}min ({desc_rec})</p>
                        """, unsafe_allow_html=True)
                        if p.get('comentarios'):
                            with st.expander("📝 Ver Anotações"):
                                st.info(f"{p['comentarios']}")
                            
                    with ca:
                        with st.form(key=f"rev_{p['id']}_{p['col']}"):
                            st.caption("Registrar Revisão")
                            n_ac = st.number_input("Acertos", min_value=0, key=f"nac_{p['id']}")
                            n_to = st.number_input("Total", min_value=1, value=10, key=f"nto_{p['id']}")
                            if st.form_submit_button("✅ CONCLUIR"):
                                try:
                                    # Update Supabase
                                    # Primeiro pegamos valores atuais para somar
                                    curr = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                                    if curr.data:
                                        new_ac = curr.data[0]['acertos'] + n_ac
                                        new_to = curr.data[0]['total'] + n_to
                                        new_tx = (new_ac / new_to * 100) if new_to > 0 else 0
                                        
                                        supabase.table("registros_estudos").update({
                                            p['col']: True,
                                            "acertos": new_ac,
                                            "total": new_to,
                                            "taxa": new_tx,
                                            "comentarios": f"{p.get('comentarios','')} | Rev: {n_ac}/{n_to}"
                                        }).eq("id", p['id']).execute()
                                        
                                        st.toast("Revisão registrada!")
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")

                    st.markdown('</div>', unsafe_allow_html=True)

    # 3. REGISTRAR
    elif menu_selecionado == "REGISTRAR":
        st.markdown("## 📝 Novo Registro")
        
        materias_disponiveis = list(dados_edital.get('materias', {}).keys())
        if not materias_disponiveis:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'CONFIGURAR' para adicionar.")
        else:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            with st.form("form_registro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                data = c1.date_input("Data", datetime.date.today())
                tempo_input = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30m")
                
                c3, c4 = st.columns(2)
                mat = c3.selectbox("Disciplina", materias_disponiveis)
                topicos = dados_edital['materias'].get(mat, [])
                ass = c4.selectbox("Assunto", topicos if topicos else ["Geral"])
                
                st.divider()
                
                c5, c6 = st.columns(2)
                acertos = c5.number_input("Acertos", min_value=0)
                total = c6.number_input("Total", min_value=1, value=10)
                
                # Classificação de Dificuldade
                st.markdown("##### 🎯 Como foi esse assunto?")
                dif = st.segmented_control("Classificação:", ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"], default="🟡 Médio")
                
                tempo_rec, desc_rec = tempo_recomendado_rev24h(dif)
                st.info(f"💡 **{dif}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                
                obs = st.text_area("Comentários")
                
                if st.form_submit_button("💾 SALVAR ESTUDO", use_container_width=True, type="primary"):
                    tempo_min = formatar_tempo_para_bigint(tempo_input)
                    taxa = (acertos/total*100)
                    payload = {
                        "concurso": missao, "materia": mat, "assunto": ass,
                        "data_estudo": str(data), "tempo": tempo_min,
                        "acertos": acertos, "total": total, "taxa": taxa,
                        "dificuldade": dif, "comentarios": obs,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }
                    if save_record(payload):
                        st.success("Registro Salvo!")
                        time.sleep(1)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # 4. DASHBOARD
    elif menu_selecionado == "DASHBOARD":
        st.markdown("## 📊 Analytics Avançado")
        if df.empty:
            st.warning("Sem dados.")
        else:
            # Evolução
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("### 📈 Evolução de Acertos")
            df['data_estudo'] = pd.to_datetime(df['data_estudo'])
            daily = df.groupby('data_estudo')[['acertos', 'total']].sum().reset_index().sort_values('data_estudo')
            
            fig = px.line(daily, x='data_estudo', y='acertos', markers=True, template='plotly_dark')
            fig.update_traces(line_color='#8B5CF6', line_width=3)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("### 🕸️ Distribuição")
                fig_pie = px.pie(df, values='total', names='materia', hole=0.5, template='plotly_dark')
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("### 🎯 Precisão Média")
                df_mean = df.groupby('data_estudo')['taxa'].mean().reset_index()
                fig_bar = px.bar(df_mean, x='data_estudo', y='taxa', template='plotly_dark')
                fig_bar.update_traces(marker_color='#06B6D4')
                fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # 5. HISTÓRICO
    elif menu_selecionado == "HISTÓRICO":
        st.markdown("## 📜 Log Completo")
        
        # Filtros
        cf1, cf2 = st.columns(2)
        with cf1: search_mat = st.selectbox("Filtrar Matéria", ["Todas"] + list(df['materia'].unique()) if not df.empty else [])
        with cf2: sort_by = st.selectbox("Ordenar", ["Data (Recente)", "Data (Antigo)", "Taxa (Alta)", "Taxa (Baixa)"])
        
        if not df.empty:
            df_view = df.copy()
            if search_mat != "Todas": df_view = df_view[df_view['materia'] == search_mat]
            
            if sort_by == "Data (Recente)": df_view = df_view.sort_values('data_estudo', ascending=False)
            elif sort_by == "Data (Antigo)": df_view = df_view.sort_values('data_estudo', ascending=True)
            elif sort_by == "Taxa (Alta)": df_view = df_view.sort_values('taxa', ascending=False)
            else: df_view = df_view.sort_values('taxa', ascending=True)

            # --- EDIÇÃO DE REGISTRO ---
            if st.session_state.edit_id:
                rec_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
                st.markdown('<div class="modern-card" style="border:1px solid #F59E0B;">', unsafe_allow_html=True)
                st.markdown("### ✏️ Editando Registro")
                with st.form("edit_form"):
                    ec1, ec2 = st.columns(2)
                    edt = ec1.date_input("Data", pd.to_datetime(rec_edit['data_estudo']).date())
                    etm = ec2.number_input("Tempo (min)", value=int(rec_edit['tempo']))
                    
                    ec3, ec4 = st.columns(2)
                    eac = ec3.number_input("Acertos", value=int(rec_edit['acertos']))
                    eto = ec4.number_input("Total", value=int(rec_edit['total']))
                    
                    eobs = st.text_area("Comentários", value=rec_edit['comentarios'] or "")
                    
                    if st.form_submit_button("💾 Salvar Alterações"):
                        ntaxa = (eac/eto*100) if eto > 0 else 0
                        supabase.table("registros_estudos").update({
                            "data_estudo": str(edt),
                            "tempo": etm,
                            "acertos": eac,
                            "total": eto,
                            "taxa": ntaxa,
                            "comentarios": eobs
                        }).eq("id", st.session_state.edit_id).execute()
                        st.success("Atualizado!")
                        st.session_state.edit_id = None
                        st.rerun()
                    
                    if st.form_submit_button("Cancelar"):
                        st.session_state.edit_id = None
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # --- LISTA DE REGISTROS ---
            for idx, row in df_view.iterrows():
                with st.container():
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([4, 2, 1])
                    
                    taxa = row.get('taxa', 0)
                    cor = "#10B981" if taxa >= 80 else "#F59E0B" if taxa >= 60 else "#EF4444"
                    
                    with c1:
                        st.markdown(f"**{row['materia']}**")
                        st.caption(f"{row['assunto']} | {row['data_estudo']}")
                        if row.get('comentarios'): st.write(f"_{row['comentarios']}_")
                    with c2:
                        st.markdown(f"<span style='color:{cor}; font-size:1.5rem; font-weight:bold;'>{taxa:.0f}%</span>", unsafe_allow_html=True)
                        st.caption(f"{row['acertos']}/{row['total']} acertos")
                    with c3:
                        cb1, cb2 = st.columns(2)
                        if cb1.button("✏️", key=f"ed_{row['id']}"):
                            st.session_state.edit_id = row['id']
                            st.rerun()
                        if cb2.button("🗑️", key=f"del_{row['id']}"):
                            # Dialog confirm simulates
                            supabase.table("registros_estudos").delete().eq("id", row['id']).execute()
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Nenhum registro encontrado.")

    # 6. CONFIGURAR
    elif menu_selecionado == "CONFIGURAR":
        st.markdown("## ⚙️ Configurações")
        
        # --- DADOS DO EDITAL ---
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### 📅 Dados da Missão")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            st.write(f"**Concurso:** {missao}")
            st.write(f"**Cargo:** {dados_edital.get('cargo', '-')}")
            st.write(f"**Data Prova:** {data_prova_str or 'Não definida'}")
        with col_ed2:
            with st.form("edit_date"):
                nova_data = st.date_input("Nova Data da Prova", value=None)
                if st.form_submit_button("Atualizar Data"):
                    supabase.table("editais_materias").update({"data_prova": str(nova_data)}).eq("concurso", missao).execute()
                    st.success("Atualizado!")
                    st.cache_data.clear()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- GERENCIAR MATÉRIAS ---
        st.markdown("### 📚 Gerenciar Matérias")
        
        materias_atuais = dados_edital.get('materias', {})

        # Listagem e Edição por Matéria
        if materias_atuais:
            for mat_nome, topicos in materias_atuais.items():
                with st.expander(f"📘 {mat_nome} ({len(topicos)} tópicos)"):
                    # Opção de renomear
                    if st.session_state.get(f"renomear_{mat_nome}", False):
                         with st.form(f"ren_form_{mat_nome}"):
                             nn = st.text_input("Novo Nome", value=mat_nome)
                             if st.form_submit_button("Salvar Nome"):
                                 # Update DB (Complex logic: update records and editais)
                                 supabase.table("editais_materias").update({"materia": nn}).eq("concurso", missao).eq("materia", mat_nome).execute()
                                 supabase.table("registros_estudos").update({"materia": nn}).eq("concurso", missao).eq("materia", mat_nome).execute()
                                 st.success("Renomeado!")
                                 st.session_state[f"renomear_{mat_nome}"] = False
                                 st.cache_data.clear()
                                 st.rerun()
                    else:
                        if st.button("✏️ Renomear Matéria", key=f"btn_ren_{mat_nome}"):
                            st.session_state[f"renomear_{mat_nome}"] = True
                            st.rerun()
                    
                    st.divider()
                    
                    # Adicionar Tópicos em Massa
                    st.markdown("##### Adicionar Tópicos")
                    with st.form(f"add_top_{mat_nome}"):
                        metodo = st.radio("Método", ["Separador (;)", "Linhas"], key=f"met_{mat_nome}", horizontal=True)
                        txt = st.text_area("Tópicos")
                        if st.form_submit_button("➕ Adicionar"):
                            novos = processar_assuntos_em_massa(txt, ";" if metodo == "Separador (;)" else "linha")
                            todos = list(set(topicos + novos))
                            # Need ID of materia entry to update
                            # Fetching ID logic omitted for brevity but assuming unique constraint on conc+mat
                            res = supabase.table("editais_materias").select("id").eq("concurso", missao).eq("materia", mat_nome).execute()
                            if res.data:
                                supabase.table("editais_materias").update({"topicos": todos}).eq("id", res.data[0]['id']).execute()
                                st.success(f"{len(novos)} tópicos adicionados!")
                                st.cache_data.clear()
                                st.rerun()
                    
                    st.divider()
                    st.write(f"**Tópicos Atuais:** {', '.join(topicos)}")


        st.divider()

        # Adicionar Nova Matéria
        st.markdown("#### ➕ Adicionar Nova Matéria")
        with st.form("add_mat_new"):
            nm = st.text_input("Nome da Matéria")
            metodo_ini = st.radio("Tópicos Iniciais", ["Nenhum", "Lista por Linhas"], horizontal=True)
            nt = st.text_area("Tópicos") if metodo_ini == "Lista por Linhas" else ""
            
            if st.form_submit_button("Salvar Matéria"):
                if nm:
                    tops = processar_assuntos_em_massa(nt, "linha") if nt else ["Geral"]
                    payload = {"concurso": missao, "cargo": dados_edital.get('cargo'), "materia": nm, "topicos": tops}
                    supabase.table("editais_materias").insert(payload).execute()
                    st.success("Matéria adicionada!")
                    st.cache_data.clear()
                    st.rerun()

        st.divider()

        # Exclusão em Massa
        st.markdown("#### 🗑️ Exclusão em Massa")
        with st.form("del_mass"):
            st.warning("⚠️ Selecione matérias para excluir (Cuidado: apaga registros também!)")
            if materias_atuais:
                selected = []
                for mat in materias_atuais.keys():
                    if st.checkbox(f"{mat}", key=f"chk_del_{mat}"):
                        selected.append(mat)
                
                chk_confirm = st.checkbox("Confirmo que entendo que é irreversível")
                
                if st.form_submit_button("🗑️ EXCLUIR SELECIONADAS"):
                    if chk_confirm and selected:
                        for m in selected:
                            supabase.table("registros_estudos").delete().eq("concurso", missao).eq("materia", m).execute()
                            supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.success("Matérias excluídas.")
                        st.cache_data.clear()
                        st.rerun()
                    elif not chk_confirm:
                        st.error("Marque a confirmação.")
            else:
                st.info("Nada para excluir.")

        st.divider()
        
        # --- ZONA DE PERIGO ---
        with st.expander("🚨 Zona de Perigo (Excluir Missão)"):
            st.error("Esta ação apagará TODOS os dados desta missão permanentemente.")
            confirma = st.checkbox("Tenho certeza que quero excluir esta missão")
            if confirma and st.button("EXCLUIR MISSÃO COMPLETA"):
                if excluir_concurso_completo(supabase, missao):
                    st.session_state.missao_ativa = None
                    st.rerun()
