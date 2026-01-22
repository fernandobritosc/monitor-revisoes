# app.py (REDESIGN COMPLETO - Layout Premium - CORRIGIDO)

import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu
import calendar
import numpy as np

# ============================================================================
# 🎨 NOVO DESIGN SYSTEM - TEMA PREMIUM ROXO/CIANO 3D
# ============================================================================

# Paleta de cores premium
COLORS = {
    "primary": "#8B5CF6",      # Roxo elétrico
    "secondary": "#00FFFF",    # Ciano Neon
    "accent": "#EC4899",       # Rosa neon
    "success": "#10B981",      # Verde neon
    "warning": "#F59E0B",      # Âmbar
    "danger": "#FF4B4B",       # Vermelho vibrante
    "bg_dark": "#0A0B15",      # Fundo mais escuro
    "bg_card": "rgba(20, 22, 40, 0.7)",  # Cards - mais escuro para contraste
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0AEC0",
    "border": "rgba(0, 255, 255, 0.15)",
    "glow": "rgba(139, 92, 246, 0.3)",
}

# --- FUNÇÃO ADICIONADA: Conversor de tempo ---
def formatar_tempo_para_bigint(tempo_str):
    """Converte string HHMM para minutos inteiros."""
    try:
        tempo_str = str(tempo_str).strip()
        if len(tempo_str) == 4:
            horas = int(tempo_str[:2])
            minutos = int(tempo_str[2:])
            return horas * 60 + minutos
        elif len(tempo_str) == 3:
            horas = int(tempo_str[0])
            minutos = int(tempo_str[1:])
            return horas * 60 + minutos
        else:
            return int(tempo_str)  # Já em minutos
    except (ValueError, TypeError, AttributeError):
        return 0

# ============================================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================================

st.set_page_config(
    page_title="Monitor Pro Premium",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎯"
)

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'missao_ativa' not in st.session_state:
    try:
        ed = get_editais(supabase)
        if ed:
            st.session_state.missao_ativa = list(ed.keys())[0]
        else:
            st.session_state.missao_ativa = None
    except Exception:
        st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

if 'meta_horas_semana' not in st.session_state:
    st.session_state.meta_horas_semana = 22

if 'meta_questoes_semana' not in st.session_state:
    st.session_state.meta_questoes_semana = 350

if 'editando_metas' not in st.session_state:
    st.session_state.editando_metas = False

if 'renomear_materia' not in st.session_state:
    st.session_state.renomear_materia = {}

# Aplicar estilos base
apply_styles()

# --- CSS CUSTOMIZADO PREMIUM ---
st.markdown("""
    <style>
    /* RESET E CONFIGURAÇÕES GERAIS */
    :root {
        --primary: #8B5CF6;
        --secondary: #00FFFF;
        --accent: #EC4899;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #FF4B4B;
        --bg-primary: #0A0B15;
        --bg-secondary: #0E1117;
        --bg-card: rgba(20, 22, 40, 0.7);
        --text-primary: #FFFFFF;
        --text-secondary: #A0AEC0;
        --border: rgba(0, 255, 255, 0.15);
        --glow: rgba(139, 92, 246, 0.3);
    }
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* FUNDO PRINCIPAL COM GRADIENTE */
    .stApp {
        background: linear-gradient(135deg, #0A0B15 0%, #0E1117 100%) !important;
        background-attachment: fixed !important;
        min-height: 100vh !important;
    }
    
    /* REMOVER BACKGROUNDS PADRÃO DO STREAMLIT */
    .main .block-container {
        background: transparent !important;
    }
    
    /* SIDEBAR PREMIUM */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%) !important;
        border-right: 1px solid var(--border) !important;
        min-width: 280px !important;
        width: 280px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 5px 0 30px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(20px) !important;
    }
    
    /* CONTEÚDO PRINCIPAL */
    [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
        max-width: calc(100% - 280px) !important;
        margin-left: 280px !important;
        padding-left: 4rem !important;
        padding-right: 4rem !important;
        padding-top: 2rem !important;
        transition: all 0.3s ease !important;
    }
    
    /* TÍTULOS PREMIUM */
    .premium-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-shadow: 0 4px 20px var(--glow);
    }
    
    .section-title {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .section-title::before {
        content: '';
        width: 4px;
        height: 24px;
        background: linear-gradient(var(--primary), var(--secondary));
        border-radius: 2px;
    }
    
    /* CARDS PREMIUM */
    .premium-card {
        background: linear-gradient(145deg, var(--bg-card), rgba(10, 12, 28, 0.9));
        backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        box-shadow: 
            0 10px 40px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }
    
    .premium-card:hover {
        transform: translateY(-8px);
        box-shadow: 
            0 20px 60px rgba(139, 92, 246, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        border-color: rgba(0, 255, 255, 0.3);
    }
    
    /* GRID SYSTEM */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 25px;
        margin: 25px 0;
    }
    
    .grid-item {
        min-height: 200px;
    }
    
    /* BOTÕES PREMIUM */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        border: 1px solid var(--border) !important;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2)) !important;
        color: var(--text-primary) !important;
        backdrop-filter: blur(10px) !important;
        overflow: hidden !important;
        position: relative !important;
        padding: 12px 24px !important;
    }
    
    .stButton > button:hover {
        border-color: rgba(139, 92, 246, 0.6) !important;
        box-shadow: 0 0 25px rgba(139, 92, 246, 0.4) !important;
        transform: translateY(-2px) !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
        border: none !important;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3) !important;
    }
    
    /* INPUTS PREMIUM */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(20, 22, 40, 0.8) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 15px var(--glow) !important;
        outline: none !important;
    }
    
    /* TABS PREMIUM */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(20, 22, 40, 0.6) !important;
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 10px;
        border: 1px solid var(--border);
        margin-bottom: 25px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background: transparent;
        border-radius: 12px;
        color: var(--text-secondary);
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(139, 92, 246, 0.1);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
    }
    
    /* METRIC CARDS NATIVOS */
    [data-testid="metric-container"] {
        background: linear-gradient(145deg, var(--bg-card), rgba(10, 12, 28, 0.9)) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border) !important;
        border-radius: 20px !important;
        padding: 25px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 15px 40px rgba(139, 92, 246, 0.2);
        border-color: rgba(0, 255, 255, 0.3);
    }
    
    /* DATA FRAMES */
    .stDataFrame {
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        overflow: hidden !important;
        background: rgba(20, 22, 40, 0.6) !important;
    }
    
    /* EXPANDERS */
    .streamlit-expanderHeader {
        background: rgba(139, 92, 246, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(139, 92,246, 0.15) !important;
        border-color: var(--primary) !important;
    }
    
    /* SCROLLBAR PERSONALIZADA */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(20, 22, 40, 0.5);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        border-radius: 5px;
        border: 2px solid rgba(20, 22, 40, 0.5);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary);
    }
    
    /* ANIMAÇÕES */
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 10px var(--glow); }
        50% { box-shadow: 0 0 20px var(--glow); }
    }
    
    .floating {
        animation: float 3s ease-in-out infinite;
    }
    
    .pulse {
        animation: pulse 2s ease-in-out infinite;
    }
    
    .glow {
        animation: glow 2s ease-in-out infinite;
    }
    
    /* RESPONSIVIDADE */
    @media (max-width: 768px) {
        .premium-title {
            font-size: 2rem;
        }
        
        .grid-container {
            grid-template-columns: 1fr;
            gap: 15px;
        }
        
        [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    
    /* EFEITOS ESPECIAIS */
    .glass-effect {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .particle-bg {
        background-image: 
            radial-gradient(circle at 20% 80%, var(--primary)10 1px, transparent 1px),
            radial-gradient(circle at 80% 20%, var(--secondary)10 1px, transparent 1px);
        background-size: 50px 50px;
    }
    
    /* STATUS INDICATORS */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active {
        background: var(--success);
        box-shadow: 0 0 10px var(--success);
    }
    
    .status-inactive {
        background: var(--text-secondary);
    }
    
    .status-warning {
        background: var(--warning);
        box-shadow: 0 0 10px var(--warning);
    }
    
    /* LOADING SKELETON */
    .skeleton {
        background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
        border-radius: 8px;
    }
    
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES AUXILIARES (MANTIDAS DO ORIGINAL)
# ============================================================================

# Formata minutos em '2h 15m'
def formatar_minutos(minutos_totais):
    try:
        minutos = int(minutos_totais)
    except (ValueError, TypeError):
        return "0m"
    horas = minutos // 60
    minutos_rest = minutos % 60
    if horas > 0:
        return f"{horas}h{minutos_rest:02d}min"
    return f"{minutos_rest}min"

def formatar_horas_minutos(minutos_totais):
    """Formata minutos para 'Xh YYmin'"""
    try:
        minutos = int(minutos_totais)
    except (ValueError, TypeError):
        return "0h00min"
    horas = minutos // 60
    minutos_rest = minutos % 60
    return f"{horas}h{minutos_rest:02d}min"

def calcular_streak(df):
    """Calcula dias consecutivos até hoje baseado na coluna 'data_estudo'."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
    except (ValueError, TypeError, KeyError):
        return 0
    dias = set(datas)
    streak = 0
    hoje = datetime.date.today()
    alvo = hoje
    while alvo in dias:
        streak += 1
        alvo = alvo - datetime.timedelta(days=1)
    return streak

def calcular_recorde_streak(df):
    """Calcula o maior streak (record) já alcançado."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().sort_values().unique()
    except (ValueError, TypeError, KeyError):
        return 0
    
    if len(datas) == 0:
        return 0
    
    recorde = 0
    streak_atual = 1
    
    for i in range(1, len(datas)):
        diferenca = (datas[i] - datas[i-1]).days
        if diferenca == 1:
            streak_atual += 1
        else:
            recorde = max(recorde, streak_atual)
            streak_atual = 1
    
    return max(recorde, streak_atual)

def calcular_datas_streak(df):
    """Calcula as datas de início e fim do streak atual."""
    if df is None or df.empty:
        return None, None
    if 'data_estudo' not in df.columns:
        return None, None
    
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
        datas = sorted(datas, reverse=True)  # Mais recentes primeiro
    except (ValueError, TypeError, KeyError):
        return None, None
    
    if not datas:
        return None, None
    
    hoje = datetime.date.today()
    streak = calcular_streak(df)
    
    if streak == 0:
        return None, None
    
    fim_streak = hoje - datetime.timedelta(days=1)
    inicio_streak = fim_streak - datetime.timedelta(days=streak-1)
    
    return inicio_streak, fim_streak

def calcular_estudos_semana(df):
    """Calcula o total de horas e questões da semana atual."""
    if df is None or df.empty:
        return 0, 0
    
    hoje = datetime.date.today()
    inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())  # Segunda-feira
    fim_semana = inicio_semana + datetime.timedelta(days=6)  # Domingo
    
    try:
        df['data_estudo_date'] = pd.to_datetime(df['data_estudo']).dt.date
        df_semana = df[(df['data_estudo_date'] >= inicio_semana) & (df['data_estudo_date'] <= fim_semana)]
        
        horas_semana = df_semana['tempo'].sum() / 60
        questoes_semana = df_semana['total'].sum()
        
        return horas_semana, questoes_semana
    except (ValueError, TypeError, KeyError):
        return 0, 0

def calcular_proximo_intervalo(dificuldade, taxa_acerto):
    """
    Calcula o próximo intervalo de revisão baseado na dificuldade e desempenho.
    
    Fácil:   → 15 ou 20 dias (aproveita ciclos longos)
    Médio:   → 7 dias (padrão confiável)
    Difícil: → 3 dias se acerto < 70%, senão 5
    """
    if dificuldade == "🟢 Fácil":
        return 15 if taxa_acerto > 80 else 7
    elif dificuldade == "🟡 Médio":
        return 7
    else:  # 🔴 Difícil
        return 3 if taxa_acerto < 70 else 5

def tempo_recomendado_rev24h(dificuldade):
    """Retorna tempo sugerido para revisão de 24h (em minutos)."""
    tempos = {
        "🟢 Fácil": (2, "Apenas releitura rápida dos títulos"),
        "🟡 Médio": (8, "Revise seus grifos + 5 questões"),
        "🔴 Difícil": (18, "Active Recall completo + questões-chave")
    }
    return tempos.get(dificuldade, (5, "Padrão"))

# --- FUNÇÃO COM CACHE PARA PERFORMANCE ---
@st.cache_data(ttl=300)
def calcular_revisoes_pendentes(df, filtro_rev, filtro_dif):
    """Calcula revisões pendentes com cache para melhor performance."""
    hoje = datetime.date.today()
    pend = []
    
    if df.empty:
        return pend
        
    for _, row in df.iterrows():
        dt_est = pd.to_datetime(row['data_estudo']).date()
        dias = (hoje - dt_est).days
        tx = row.get('taxa', 0)
        dif = row.get('dificuldade', '🟡 Médio')
        
        # Lógica de Revisão 24h
        if not row.get('rev_24h', False):
            dt_prev = dt_est + timedelta(days=1)
            if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                atraso = (hoje - dt_prev).days
                pend.append({
                    "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                    "tipo": "Revisão 24h", "col": "rev_24h", "atraso": atraso, 
                    "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                    "dificuldade": dif, "taxa": tx
                })
        
        # Lógica de Ciclos Longos (ADAPTATIVA) - CORRIGIDA: remove o elif problemático
        else:  # rev_24h = True
            intervalo = calcular_proximo_intervalo(dif, tx)
            
            # Determinar qual coluna atualizar
            if intervalo <= 7:
                col_alv, lbl = "rev_07d", f"Revisão {intervalo}d"
            else:  # 15+ dias
                col_alv, lbl = "rev_15d", f"Revisão {intervalo}d"
            
            if not row.get(col_alv, False):
                dt_prev = dt_est + timedelta(days=intervalo)
                if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                    atraso = (hoje - dt_prev).days
                    pend.append({
                        "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                        "tipo": lbl, "col": col_alv, "atraso": atraso, 
                        "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                        "dificuldade": dif, "taxa": tx
                    })
    
    # Filtrar por dificuldade
    if filtro_dif != "Todas":
        pend = [p for p in pend if p['dificuldade'] == filtro_dif]
    
    return pend

# --- FUNÇÃO SIMPLIFICADA: Card de métrica ---
def render_metric_card(label, value, icon="📊", color=None, subtitle=None):
    """Renderiza cartões de métricas simplificados"""
    if color is None:
        color = COLORS["primary"]
    
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 25px 20px;
            background: linear-gradient(145deg, rgba(20, 22, 40, 0.9), rgba(10, 12, 28, 0.9));
            backdrop-filter: blur(20px);
            border: 1px solid {COLORS['border']};
            border-radius: 20px;
            min-height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        ">
            <div style="font-size: 2.5rem; margin-bottom: 15px; color: {color};">
                {icon}
            </div>
            <div style="
                color: {COLORS['text_secondary']};
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 10px;
                font-weight: 600;
            ">{label}</div>
            <div style="
                font-size: 2.2rem;
                font-weight: 800;
                background: linear-gradient(135deg, {color}, {COLORS['secondary']});
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.2;
                margin: 8px 0;
            ">{value}</div>
            {f'<div style="color: {COLORS["text_secondary"]}; font-size: 0.9rem; margin-top: 8px;">{subtitle}</div>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# LÓGICA DE NAVEGAÇÃO SIMPLIFICADA
# ============================================================================

if st.session_state.missao_ativa is None:
    # Tela inicial simplificada
    st.markdown('<h1 class="premium-title">🎯 CENTRAL DE COMANDO</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #94A3B8; font-size: 1.1rem; margin-bottom: 2rem;">Selecione sua missão ou inicie um novo ciclo</p>', unsafe_allow_html=True)
    
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 MISSÕES ATIVAS", "➕ NOVA MISSÃO"])
    
    with tabs[0]:
        if not ed: 
            st.markdown('<div class="premium-card"><p style="text-align: center; color: #94A3B8;">Nenhuma missão ativa no momento.</p></div>', unsafe_allow_html=True)
        else:
            cols = st.columns(2, gap="25px")
            for i, (nome, d_concurso) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="premium-card">
                            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                                <div style="
                                    width: 50px;
                                    height: 50px;
                                    background: linear-gradient(135deg, #8B5CF6, #06B6D4);
                                    border-radius: 12px;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    font-size: 1.5rem;
                                ">🎯</div>
                                <div>
                                    <h3 style="margin:0; background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{nome}</h3>
                                    <p style="color:#94A3B8; font-size:0.9rem; margin:5px 0 0 0;">{d_concurso['cargo']}</p>
                                </div>
                            </div>
                            <div style="margin-top: 20px;">
                                <button style="
                                    width: 100%;
                                    padding: 12px;
                                    background: linear-gradient(135deg, #8B5CF6, #06B6D4);
                                    border: none;
                                    border-radius: 12px;
                                    color: white;
                                    font-weight: 600;
                                    cursor: pointer;
                                " onclick="window.location.href='?mission={nome}'">
                                    ACESSAR MISSÃO
                                </button>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
    
    with tabs[1]:
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("##### 🚀 Cadastrar Nova Missão")
            
            with st.form("form_novo_concurso", clear_on_submit=True):
                col1, col2 = st.columns(2, gap="20px")
                with col1:
                    nome_concurso = st.text_input("Nome do Concurso", placeholder="Ex: Receita Federal, TJ-SP, etc.")
                with col2:
                    cargo_concurso = st.text_input("Cargo", placeholder="Ex: Auditor Fiscal, Escrevente, etc.")
                
                informar_data_prova = st.checkbox("📅 Informar data da prova (opcional)")
                if informar_data_prova:
                    data_prova_input = st.date_input("Data da Prova")
                else:
                    data_prova_input = None
                
                st.divider()
                
                btn_cadastrar = st.form_submit_button("🚀 INICIAR MISSÃO", use_container_width=True, type="primary")
                
                if btn_cadastrar:
                    if nome_concurso and cargo_concurso:
                        try:
                            payload = {
                                "concurso": nome_concurso,
                                "cargo": cargo_concurso,
                                "materia": "Geral",
                                "topicos": ["Introdução"]
                            }
                            if data_prova_input:
                                payload["data_prova"] = data_prova_input.strftime("%Y-%m-%d")
                            
                            res_ins = supabase.table("editais_materias").insert(payload).execute()
                            
                            if res_ins.data:
                                st.success(f"✅ Missão '{nome_concurso}' criada com sucesso!")
                                time.sleep(1)
                                st.session_state.missao_ativa = nome_concurso
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar: {e}")
                    else:
                        st.warning("⚠️ Por favor, preencha o nome e o cargo.")
            
            st.markdown('</div>', unsafe_allow_html=True)

else:
    missao = st.session_state.missao_ativa
    
    # Carregar dados
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar registros - {e}")
        df = pd.DataFrame()
    
    # Buscar data da prova
    try:
        res_data_prova = supabase.table("editais_materias").select("data_prova").eq("concurso", missao).limit(1).execute()
        data_prova_direta = res_data_prova.data[0].get('data_prova') if res_data_prova.data else None
    except Exception:
        data_prova_direta = None
    
    dados = get_editais(supabase).get(missao, {})

    # --- SIDEBAR SIMPLIFICADA ---
    with st.sidebar:
        # Logo premium
        st.markdown("""
            <div style='text-align: center; padding: 20px 0 30px 0;'>
                <div style='
                    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1));
                    width: 70px;
                    height: 70px;
                    border-radius: 18px;
                    margin: 0 auto 15px auto;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                    border: 1px solid rgba(0, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                '>
                    <span style='font-size: 35px;'>🎯</span>
                </div>
                <h1 style='color: white; font-family: "Montserrat", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0; letter-spacing: -0.5px; line-height: 1.2;'>
                    MONITOR<span style='color: #00FFFF; padding: 0 6px; border-radius: 6px; margin-left: 4px; font-size: 1.4rem; vertical-align: middle;'>PRO</span>
                </h1>
                <p style='color: rgba(255,255,255,0.7); font-size: 0.75rem; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px; font-weight: 500;'>
                    Premium Edition
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Menu premium
        menu_selecionado = option_menu(
            menu_title=None,
            options=["DASHBOARD", "REVISÕES", "REGISTRAR", "HISTÓRICO", "CONFIG"],
            icons=["speedometer2", "arrow-repeat", "plus-circle", "clock", "gear"],
            menu_icon="list",
            default_index=0,
            styles={
                "container": {
                    "padding": "0!important", 
                    "background-color": "rgba(20, 22, 40, 0.4)",
                    "backdrop-filter": "blur(10px)",
                    "border-radius": "16px",
                    "border": "1px solid rgba(0, 255, 255, 0.1)",
                },
                "icon": {"color": "#8B5CF6", "font-size": "16px", "margin-right": "12px"}, 
                "nav-link": {
                    "font-family": "Montserrat, sans-serif",
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "10px 12px",
                    "padding": "14px 20px",
                    "border-radius": "12px",
                    "color": "#94A3B8",
                    "transition": "all 0.3s ease",
                    "border": "1px solid transparent"
                },
                "nav-link-selected": {
                    "background": "linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.08))",
                    "color": "#fff",
                    "font-weight": "700",
                    "border-left": "4px solid #00FFFF",
                    "border-radius": "4px 12px 12px 4px",
                    "box-shadow": "0 4px 15px rgba(139, 92, 246, 0.2)",
                    "border": "1px solid rgba(139, 92, 246, 0.2)"
                },
            }
        )
        
        # Info da missão atual
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, rgba(20, 22, 40, 0.6), rgba(10, 12, 28, 0.8));
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 20px;
                margin: 20px 0;
                border: 1px solid rgba(0, 255, 255, 0.1);
            '>
                <p style='color: #8B5CF6; font-size: 0.8rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;'>Missão Ativa</p>
                <p style='color: #fff; font-weight: 700; font-size: 1.1rem; margin: 0 0 5px 0;'>{missao}</p>
                <p style='color: #94A3B8; font-size: 0.85rem; margin: 0;'>{dados.get('cargo', '')}</p>
                
                <div style='margin-top: 15px;'>
                    <button style='
                        width: 100%;
                        padding: 10px;
                        background: rgba(139, 92, 246, 0.1);
                        border: 1px solid rgba(139, 92, 246, 0.3);
                        border-radius: 10px;
                        color: #8B5CF6;
                        font-weight: 600;
                        cursor: pointer;
                        font-size: 0.85rem;
                    ' onclick="window.location.href='?change_mission=true'">
                        🔄 Trocar Missão
                    </button>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Stats rápidos
        if not df.empty:
            total_questoes = df['total'].sum()
            total_horas = df['tempo'].sum() / 60
            taxa_media = df['taxa'].mean() if not df.empty else 0
            
            st.markdown(f"""
                <div style='
                    background: linear-gradient(135deg, rgba(20, 22, 40, 0.6), rgba(10, 12, 28, 0.8));
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 20px;
                    margin: 15px 0;
                    border: 1px solid rgba(0, 255, 255, 0.1);
                '>
                    <p style='color: #8B5CF6; font-size: 0.8rem; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;'>Stats Rápidos</p>
                    
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
                        <div style='text-align: center;'>
                            <p style='color: #94A3B8; font-size: 0.75rem; margin: 0;'>Questões</p>
                            <p style='color: #fff; font-weight: 800; font-size: 1.2rem; margin: 5px 0 0 0;'>{int(total_questoes)}</p>
                        </div>
                        <div style='text-align: center;'>
                            <p style='color: #94A3B8; font-size: 0.75rem; margin: 0;'>Horas</p>
                            <p style='color: #fff; font-weight: 800; font-size: 1.2rem; margin: 5px 0 0 0;'>{total_horas:.1f}h</p>
                        </div>
                        <div style='text-align: center; grid-column: span 2;'>
                            <p style='color: #94A3B8; font-size: 0.75rem; margin: 0;'>Taxa Média</p>
                            <p style='color: #fff; font-weight: 800; font-size: 1.2rem; margin: 5px 0 0 0;'>{taxa_media:.1f}%</p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # ============================================================================
    # PÁGINAS SIMPLIFICADAS
    # ============================================================================
    
    # Mapeamento do menu
    menu_map = {
        "DASHBOARD": "Dashboard",
        "REVISÕES": "Revisões",
        "REGISTRAR": "Registrar",
        "HISTÓRICO": "Histórico",
        "CONFIG": "Configurações"
    }
    
    menu = menu_map.get(menu_selecionado, "Dashboard")
    
    # --- DASHBOARD SIMPLIFICADO ---
    if menu == "Dashboard":
        col_title, col_actions = st.columns([3, 1])
        
        with col_title:
            st.markdown(f'<h1 class="premium-title">{missao}</h1>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#94A3B8; font-size:1.1rem; margin-bottom:2rem;">{dados.get("cargo", "")}</p>', unsafe_allow_html=True)
        
        with col_actions:
            if st.button("🔄", help="Atualizar dashboard", use_container_width=True):
                st.rerun()
        
        if not df.empty:
            # Calcular métricas
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df['tempo'].sum())
            
            # Dias para a prova
            dias_restantes = None
            if data_prova_direta:
                try:
                    dt_prova = pd.to_datetime(data_prova_direta).date()
                    dias_restantes = (dt_prova - datetime.date.today()).days
                except Exception:
                    dias_restantes = None
            
            # Grid de métricas
            metrics_cols = st.columns(4, gap="25px")
            
            with metrics_cols[0]:
                render_metric_card(
                    "TEMPO TOTAL",
                    formatar_minutos(minutos_totais),
                    "⏱️",
                    COLORS["primary"]
                )
            
            with metrics_cols[1]:
                render_metric_card(
                    "PRECISÃO",
                    f"{precisao:.0f}%",
                    "🎯",
                    COLORS["success"] if precisao >= 70 else COLORS["warning"]
                )
            
            with metrics_cols[2]:
                render_metric_card(
                    "QUESTÕES",
                    f"{int(t_q)}",
                    "📝",
                    COLORS["accent"]
                )
            
            with metrics_cols[3]:
                if dias_restantes is not None:
                    render_metric_card(
                        "DIAS PROVA",
                        f"{dias_restantes}",
                        "📅",
                        COLORS["danger"] if dias_restantes <= 30 else COLORS["warning"]
                    )
                else:
                    render_metric_card("DIAS PROVA", "—", "📅")
            
            st.divider()
            
            # Seção de constância
            st.markdown('<div class="section-title">📊 Constância nos Estudos</div>', unsafe_allow_html=True)
            
            streak = calcular_streak(df)
            recorde = calcular_recorde_streak(df)
            inicio_streak, fim_streak = calcular_datas_streak(df)
            
            const_cols = st.columns(3, gap="25px")
            
            with const_cols[0]:
                render_metric_card(
                    "STREAK ATUAL",
                    f"{streak}",
                    "🔥",
                    COLORS["primary"],
                    "dias consecutivos"
                )
            
            with const_cols[1]:
                render_metric_card(
                    "SEU RECORDE",
                    f"{recorde}",
                    "🏆",
                    COLORS["success"],
                    "dias seguidos"
                )
            
            with const_cols[2]:
                hoje = datetime.date.today()
                dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
                dias_estudados_mes = len(set(pd.to_datetime(df['data_estudo']).dt.date.unique()))
                percentual_mes = (dias_estudados_mes / dias_no_mes) * 100
                
                render_metric_card(
                    "MÊS ATUAL",
                    f"{dias_estudados_mes}/{dias_no_mes}",
                    "📅",
                    COLORS["secondary"],
                    f"({percentual_mes:.0f}%)"
                )
            
            # Painel de desempenho
            st.markdown('<div class="section-title">📈 Desempenho por Disciplina</div>', unsafe_allow_html=True)
            
            if not df.empty:
                df_disciplinas = df.groupby('materia').agg({
                    'tempo': 'sum',
                    'acertos': 'sum',
                    'total': 'sum',
                    'taxa': 'mean'
                }).reset_index()
                
                df_disciplinas = df_disciplinas.sort_values('total', ascending=False)
                
                cols = st.columns(3, gap="25px")
                for idx, (_, row) in enumerate(df_disciplinas.iterrows()):
                    if idx < 6:  # Mostrar apenas 6 disciplinas
                        with cols[idx % 3]:
                            render_metric_card(
                                label=row['materia'][:20] + ("..." if len(row['materia']) > 20 else ""),
                                value=f"{row['taxa']:.0f}%",
                                icon="📚",
                                color=COLORS["accent"] if row['taxa'] >= 70 else COLORS["warning"],
                                subtitle=f"{int(row['acertos'])}/{int(row['total'])} questões"
                            )
            
            # Metas semanais
            st.markdown('<div class="section-title">🎯 Metas Semanais</div>', unsafe_allow_html=True)
            
            horas_semana, questoes_semana = calcular_estudos_semana(df)
            meta_horas = st.session_state.meta_horas_semana
            meta_questoes = st.session_state.meta_questoes_semana
            
            meta_cols = st.columns(2, gap="25px")
            
            with meta_cols[0]:
                progresso_horas = min((horas_semana / meta_horas) * 100, 100) if meta_horas > 0 else 0
                st.markdown(f"""
                    <div class="premium-card">
                        <h4 style="color: #fff; margin-bottom: 15px;">Horas de Estudo</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                                {horas_semana:.1f}h / {meta_horas}h
                            </div>
                            <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 5px;">{progresso_horas:.0f}% da meta</div>
                        </div>
                        <div style="
                            width: 100%;
                            height: 8px;
                            background: rgba(139, 92, 246, 0.1);
                            border-radius: 4px;
                            overflow: hidden;
                        ">
                            <div style="
                                height: 100%;
                                border-radius: 4px;
                                background: linear-gradient(90deg, #8B5CF6, #06B6D4);
                                width: {progresso_horas}%;
                                transition: width 1s ease;
                            "></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with meta_cols[1]:
                progresso_questoes = min((questoes_semana / meta_questoes) * 100, 100) if meta_questoes > 0 else 0
                st.markdown(f"""
                    <div class="premium-card">
                        <h4 style="color: #fff; margin-bottom: 15px;">Questões Resolvidas</h4>
                        <div style="margin: 20px 0;">
                            <div style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #EC4899, #8B5CF6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                                {int(questoes_semana)} / {meta_questoes}
                            </div>
                            <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 5px;">{progresso_questoes:.0f}% da meta</div>
                        </div>
                        <div style="
                            width: 100%;
                            height: 8px;
                            background: rgba(236, 72, 153, 0.1);
                            border-radius: 4px;
                            overflow: hidden;
                        ">
                            <div style="
                                height: 100%;
                                border-radius: 4px;
                                background: linear-gradient(90deg, #EC4899, #8B5CF6);
                                width: {progresso_questoes}%;
                                transition: width 1s ease;
                            "></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        
        else:
            st.markdown('<div class="premium-card"><p style="text-align: center; color: #94A3B8; font-size: 1.1rem;">Comece seus estudos para preencher o dashboard!</p></div>', unsafe_allow_html=True)
    
    # --- REVISÕES SIMPLIFICADAS ---
    elif menu == "Revisões":
        st.markdown('<h1 class="premium-title">🔄 Radar de Revisões</h1>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            
            col_f1, col_f2 = st.columns([2, 1], gap="20px")
            with col_f1:
                filtro_rev = st.selectbox(
                    "📊 Visualizar",
                    ["Pendentes/Hoje", "Todas (incluindo futuras)"],
                    key="filtro_rev_premium"
                )
            with col_f2:
                filtro_dif = st.selectbox(
                    "🎯 Dificuldade",
                    ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"],
                    key="filtro_dif_premium"
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        pend = calcular_revisoes_pendentes(df, filtro_rev, filtro_dif)
        
        if not pend: 
            st.markdown("""
                <div class="premium-card" style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 20px;">✨</div>
                    <h3 style="color: #fff; margin-bottom: 10px;">Tudo em dia!</h3>
                    <p style="color: #94A3B8;">Aproveite para avançar no conteúdo.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            pend = sorted(pend, key=lambda x: (x['dificuldade'] != "🔴 Difícil", x['data_prevista']))
            
            # Resumo
            dif_count = len([p for p in pend if p['dificuldade'] == "🔴 Difícil"])
            med_count = len([p for p in pend if p['dificuldade'] == "🟡 Médio"])
            fac_count = len([p for p in pend if p['dificuldade'] == "🟢 Fácil"])
            total_count = len(pend)
            
            resumo_cols = st.columns(4, gap="20px")
            with resumo_cols[0]:
                render_metric_card("TOTAL", total_count, "📋", COLORS["primary"])
            with resumo_cols[1]:
                render_metric_card("🔴 DIFÍCIL", dif_count, "🔴", COLORS["danger"])
            with resumo_cols[2]:
                render_metric_card("🟡 MÉDIO", med_count, "🟡", COLORS["warning"])
            with resumo_cols[3]:
                render_metric_card("🟢 FÁCIL", fac_count, "🟢", COLORS["success"])
            
            # Lista de revisões
            st.markdown('<div class="section-title">📋 Lista de Revisões Pendentes</div>', unsafe_allow_html=True)
            
            for p in pend:
                with st.container():
                    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                    
                    col_info, col_input, col_action = st.columns([2, 1.5, 1], gap="20px")
                    
                    with col_info:
                        status_color = COLORS["danger"] if p['atraso'] > 0 else COLORS["success"] if p['atraso'] == 0 else COLORS["warning"]
                        status_text = f"⚠️ {p['atraso']}d atraso" if p['atraso'] > 0 else "🎯 Vence hoje" if p['atraso'] == 0 else "📅 Futura"
                        
                        tempo_rec, desc = tempo_recomendado_rev24h(p['dificuldade'])
                        
                        st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                                <span style="
                                    background: {status_color}20;
                                    color: {status_color};
                                    padding: 4px 12px;
                                    border-radius: 20px;
                                    font-size: 0.75rem;
                                    font-weight: 600;
                                    border: 1px solid {status_color}40;
                                ">{status_text}</span>
                                <span style="
                                    background: rgba(139, 92, 246, 0.1);
                                    color: #8B5CF6;
                                    padding: 4px 12px;
                                    border-radius: 20px;
                                    font-size: 0.75rem;
                                    font-weight: 600;
                                ">{p['dificuldade']}</span>
                            </div>
                            <h3 style="color: #fff; margin: 0 0 5px 0;">{p['materia']}</h3>
                            <p style="color: #94A3B8; margin: 0 0 10px 0;">
                                {p['assunto']} • <strong>{p['tipo']}</strong>
                            </p>
                            <div style="
                                background: rgba(255, 142, 142, 0.1);
                                border-left: 3px solid #FF4B4B;
                                padding: 10px;
                                border-radius: 0 8px 8px 0;
                                margin-top: 10px;
                            ">
                                <p style="color: #FF8E8E; margin: 0; font-size: 0.85rem;">
                                    ⏱️ {desc} (~{tempo_rec}min)
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if p['coment']:
                            with st.expander("📝 Ver Anotações", expanded=False):
                                st.info(p['coment'])
                    
                    with col_input:
                        st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
                        st.markdown('<p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 10px;">Resultado da Revisão:</p>', unsafe_allow_html=True)
                        input_col1, input_col2 = st.columns(2, gap="10px")
                        acr_rev = input_col1.number_input(
                            "Acertos", 
                            0,
                            key=f"ac_{p['id']}_{p['col']}",
                            help="Acertos na revisão",
                            label_visibility="collapsed"
                        )
                        tor_rev = input_col2.number_input(
                            "Total", 
                            0,
                            key=f"to_{p['id']}_{p['col']}",
                            help="Total de questões na revisão",
                            label_visibility="collapsed"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col_action:
                        st.write("")  # Espaçamento
                        if st.button("✅ CONCLUIR", 
                                   key=f"btn_{p['id']}_{p['col']}", 
                                   use_container_width=True, 
                                   type="primary"):
                            try:
                                res_db = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                                if res_db.data:
                                    n_ac = res_db.data[0]['acertos'] + acr_rev
                                    n_to = res_db.data[0]['total'] + tor_rev
                                    supabase.table("registros_estudos").update({
                                        p['col']: True, 
                                        "comentarios": f"{p['coment']} | {p['tipo']}: {acr_rev}/{tor_rev}", 
                                        "acertos": n_ac, "total": n_to, 
                                        "taxa": (n_ac/n_to*100 if n_to > 0 else 0)
                                    }).eq("id", p['id']).execute()
                                    st.success("✅ Revisão concluída!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao buscar dados do registro.")
                            except Exception as e:
                                st.error(f"❌ Erro ao concluir revisão: {e}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- REGISTRAR SIMPLIFICADO ---
    elif menu == "Registrar":
        st.markdown('<h1 class="premium-title">📝 Novo Registro de Estudo</h1>', unsafe_allow_html=True)
        
        mats = list(dados.get('materias', {}).keys())
        
        if not mats:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'Config' para adicionar disciplinas.")
        else:
            with st.container():
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                
                with st.form("form_registro_premium", clear_on_submit=True):
                    col_dt, col_tm = st.columns([2, 1], gap="20px")
                    with col_dt:
                        dt_reg = st.date_input(
                            "📅 Data do Estudo", 
                            format="DD/MM/YYYY"
                        )
                    with col_tm:
                        tm_reg = st.text_input(
                            "⏱️ Tempo (HHMM)", 
                            value="0100",
                            help="Ex: 0130 para 1h30min"
                        )
                    
                    mat_reg = st.selectbox("📚 Disciplina", mats)
                    
                    assuntos_disponiveis = dados['materias'].get(mat_reg, ["Geral"])
                    ass_reg = st.selectbox(
                        "📖 Assunto", 
                        assuntos_disponiveis, 
                        key=f"assunto_select_premium_{mat_reg}"
                    )
                    
                    st.divider()
                    
                    st.markdown("##### 🎯 Desempenho e Dificuldade")
                    
                    col_ac, col_to = st.columns(2, gap="20px")
                    with col_ac:
                        ac_reg = st.number_input("✅ Questões Acertadas", 0)
                    with col_to:
                        to_reg = st.number_input("📝 Total de Questões", 1)
                    
                    st.markdown("##### 🎯 Como foi esse assunto?")
                    dif_reg = st.selectbox(
                        "Classificação de Dificuldade:",
                        ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                        index=1
                    )
                    
                    tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_reg)
                    st.info(f"💡 **{dif_reg}** - Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                    
                    st.divider()
                    
                    com_reg = st.text_area(
                        "📝 Anotações / Comentários", 
                        placeholder="O que você aprendeu? Onde sentiu dificuldade?",
                        height=120
                    )
                    
                    btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1], gap="10px")
                    with btn_col2:
                        btn_salvar = st.form_submit_button(
                            "💾 SALVAR REGISTRO", 
                            use_container_width=True, 
                            type="primary"
                        )
                    
                    if btn_salvar:
                        try:
                            t_b = formatar_tempo_para_bigint(tm_reg)
                            taxa = (ac_reg/to_reg*100 if to_reg > 0 else 0)
                            
                            payload = {
                                "concurso": missao, 
                                "materia": mat_reg, 
                                "assunto": ass_reg, 
                                "data_estudo": dt_reg.strftime('%Y-%m-%d'), 
                                "acertos": ac_reg, 
                                "total": to_reg, 
                                "taxa": taxa,
                                "dificuldade": dif_reg,
                                "comentarios": com_reg, 
                                "tempo": t_b, 
                                "rev_24h": False, 
                                "rev_07d": False, 
                                "rev_15d": False, 
                                "rev_30d": False
                            }
                            
                            supabase.table("registros_estudos").insert(payload).execute()
                            st.success("✅ Registro salvo com sucesso!")
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # --- HISTÓRICO SIMPLIFICADO ---
    elif menu == "Histórico":
        st.markdown('<h1 class="premium-title">📜 Histórico de Estudos</h1>', unsafe_allow_html=True)
        
        if not df.empty:
            df_h = df.copy()
            df_h['data_estudo_display'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            
            with st.container():
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                
                # Filtros
                col_f1, col_f2, col_f3 = st.columns(3, gap="20px")
                with col_f1:
                    mat_filter = st.selectbox(
                        "📚 Filtrar por Matéria:", 
                        ["Todas"] + list(df_h['materia'].unique()), 
                        key="mat_hist_filter_premium"
                    )
                with col_f2:
                    ordem = st.selectbox(
                        "📊 Ordenar por:", 
                        ["Mais Recente", "Mais Antigo", "Maior Taxa", "Menor Taxa"], 
                        key="ord_hist_premium"
                    )
                with col_f3:
                    periodo = st.selectbox(
                        "📅 Período:", 
                        ["Todos", "Últimos 7 dias", "Últimos 30 dias", "Este mês"], 
                        key="periodo_hist_premium"
                    )
                
                # Aplicar filtros
                df_filtered = df_h.copy()
                
                if mat_filter != "Todas":
                    df_filtered = df_filtered[df_filtered['materia'] == mat_filter]
                
                # Filtrar por período
                hoje = datetime.date.today()
                if periodo == "Últimos 7 dias":
                    data_limite = hoje - datetime.timedelta(days=7)
                    df_filtered = df_filtered[pd.to_datetime(df_filtered['data_estudo']).dt.date >= data_limite]
                elif periodo == "Últimos 30 dias":
                    data_limite = hoje - datetime.timedelta(days=30)
                    df_filtered = df_filtered[pd.to_datetime(df_filtered['data_estudo']).dt.date >= data_limite]
                elif periodo == "Este mês":
                    inicio_mes = datetime.date(hoje.year, hoje.month, 1)
                    df_filtered = df_filtered[pd.to_datetime(df_filtered['data_estudo']).dt.date >= inicio_mes]
                
                # Aplicar ordenação
                if ordem == "Mais Recente":
                    df_filtered = df_filtered.sort_values('data_estudo', ascending=False)
                elif ordem == "Mais Antigo":
                    df_filtered = df_filtered.sort_values('data_estudo', ascending=True)
                elif ordem == "Maior Taxa":
                    df_filtered = df_filtered.sort_values('taxa', ascending=False)
                else:  # Menor Taxa
                    df_filtered = df_filtered.sort_values('taxa', ascending=True)
                
                st.divider()
                
                # Resumo
                total_registros = len(df_filtered)
                taxa_media = df_filtered['taxa'].mean()
                tempo_total = df_filtered['tempo'].sum() / 60
                acertos_total = df_filtered['acertos'].sum()
                
                # Grid de resumo
                resumo_cols = st.columns(4, gap="20px")
                with resumo_cols[0]:
                    render_metric_card("Registros", total_registros, "📝", COLORS["primary"])
                with resumo_cols[1]:
                    render_metric_card("Taxa Média", f"{taxa_media:.1f}%", "🎯", 
                                     COLORS["success"] if taxa_media >= 70 else COLORS["warning"])
                with resumo_cols[2]:
                    render_metric_card("Tempo Total", f"{tempo_total:.1f}h", "⏱️", COLORS["secondary"])
                with resumo_cols[3]:
                    render_metric_card("Acertos", acertos_total, "✅", COLORS["accent"])
                
                st.divider()
                
                # Lista de registros
                st.markdown('<div class="section-title">📋 Registros de Estudo</div>', unsafe_allow_html=True)
                
                if len(df_filtered) == 0:
                    st.info("Nenhum registro encontrado com os filtros selecionados.")
                else:
                    for index, row in df_filtered.iterrows():
                        with st.container():
                            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                            
                            col_info, col_metrics, col_actions = st.columns([3, 1.5, 1.2], gap="20px")
                            
                            with col_info:
                                taxa_color = COLORS["success"] if row['taxa'] >= 80 else COLORS["warning"] if row['taxa'] >= 60 else COLORS["danger"]
                                
                                st.markdown(f"""
                                    <div style="margin-bottom: 10px;">
                                        <span style="color: #94A3B8; font-size: 0.85rem; font-weight: 600;">📅 {row['data_estudo_display']}</span>
                                        <span style="color: {taxa_color}; font-size: 0.85rem; font-weight: 700; margin-left: 15px;">
                                            {row['taxa']:.1f}%
                                        </span>
                                        <span style="color: #94A3B8; font-size: 0.85rem; margin-left: 15px;">
                                            {row.get('dificuldade', '🟡 Médio')}
                                        </span>
                                    </div>
                                    <h3 style="margin: 0; color: #fff; font-size: 1.2rem;">{row['materia']}</h3>
                                    <p style="color: #94A3B8; font-size: 0.95rem; margin: 5px 0 0 0;">{row['assunto']}</p>
                                """, unsafe_allow_html=True)
                                
                                if row.get('comentarios'):
                                    with st.expander("📝 Ver Anotações", expanded=False):
                                        st.markdown(f"<p style='color: #94A3B8; font-size: 0.9rem;'>{row['comentarios']}</p>", unsafe_allow_html=True)
                            
                            with col_metrics:
                                st.markdown(f"""
                                    <div style="text-align: right;">
                                        <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 5px;">Desempenho</div>
                                        <div style="font-size: 1.4rem; font-weight: 800; color: #fff;">
                                            {int(row['acertos'])}/{int(row['total'])}
                                        </div>
                                        <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 5px;">
                                            ⏱️ {int(row['tempo']//60)}h{int(row['tempo']%60):02d}m
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            with col_actions:
                                action_col1, action_col2 = st.columns(2, gap="5px")
                                
                                if action_col1.button("✏️", 
                                                    key=f"edit_premium_{row['id']}", 
                                                    help="Editar registro",
                                                    use_container_width=True):
                                    st.session_state.edit_id = row['id']
                                    st.rerun()
                                
                                if action_col2.button("🗑️", 
                                                    key=f"del_premium_{row['id']}", 
                                                    help="Excluir registro",
                                                    use_container_width=True):
                                    try:
                                        if st.session_state.get(f"confirm_delete_premium_{row['id']}", False):
                                            supabase.table("registros_estudos").delete().eq("id", row['id']).execute()
                                            st.toast("✅ Registro excluído com sucesso!", icon="✅")
                                            time.sleep(0.5)
                                            st.session_state[f"confirm_delete_premium_{row['id']}"] = False
                                            st.rerun()
                                        else:
                                            st.session_state[f"confirm_delete_premium_{row['id']}"] = True
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao excluir: {e}")
                                
                                if st.session_state.get(f"confirm_delete_premium_{row['id']}", False):
                                    st.warning(f"⚠️ Clique em 🗑️ novamente para confirmar", icon="⚠️")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📚 Nenhum registro de estudo encontrado ainda. Comece a estudar!")
    
    # --- CONFIGURAÇÕES SIMPLIFICADAS ---
    elif menu == "Configurações":
        st.markdown('<h1 class="premium-title">⚙️ Configurações</h1>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🎯 Missão", "📚 Matérias", "⚠️ Perigo"])
        
        with tab1:
            with st.container():
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.markdown("### 📌 Gerenciar Missão")
                
                ed = get_editais(supabase)
                if ed:
                    nomes_missoes = list(ed.keys())
                    try:
                        indice_atual = nomes_missoes.index(missao) if missao in nomes_missoes else 0
                    except (ValueError, IndexError):
                        indice_atual = 0
                    
                    nova_missao = st.selectbox(
                        "Selecione a missão ativa:",
                        options=nomes_missoes,
                        index=indice_atual
                    )
                    
                    if nova_missao != missao:
                        st.session_state.missao_ativa = nova_missao
                        st.success(f"✅ Missão alterada para: {nova_missao}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Nenhuma missão cadastrada.")
                    if st.button("➕ Criar Nova Missão", use_container_width=True):
                        st.session_state.missao_ativa = None
                        st.rerun()
                
                st.divider()
                
                st.markdown("### 📅 Data da Prova")
                
                data_prova_atual = None
                if data_prova_direta:
                    try:
                        data_prova_atual = pd.to_datetime(data_prova_direta).date()
                    except:
                        data_prova_atual = None
                
                with st.form("form_data_prova"):
                    nova_data = st.date_input(
                        "Defina a data da prova:",
                        value=data_prova_atual or datetime.date.today()
                    )
                    
                    remover_data = st.checkbox("Remover data da prova")
                    
                    if st.form_submit_button("💾 Salvar Data", use_container_width=True):
                        try:
                            valor_final = None if remover_data else nova_data.strftime("%Y-%m-%d")
                            supabase.table("editais_materias").update({"data_prova": valor_final}).eq("concurso", missao).execute()
                            st.success("✅ Data atualizada!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            with st.container():
                st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                st.markdown("### 📚 Gerenciar Matérias")
                
                try:
                    res_materias = supabase.table("editais_materias").select("id, materia, topicos").eq("concurso", missao).execute()
                    registros_materias = res_materias.data
                except Exception as e:
                    st.error(f"Erro ao buscar matérias: {e}")
                    registros_materias = []
                
                if registros_materias:
                    for reg in registros_materias:
                        with st.expander(f"📖 {reg['materia']} ({len(reg['topicos'] if reg['topicos'] else [])} assuntos)"):
                            topicos = reg['topicos'] if reg['topicos'] else []
                            if topicos:
                                for i, topico in enumerate(topicos):
                                    col_t1, col_t2 = st.columns([5, 1])
                                    col_t1.write(f"• {topico}")
                                    if col_t2.button("🗑️", key=f"del_t_{reg['id']}_{i}", use_container_width=True):
                                        try:
                                            novos_topicos = [t for t in topicos if t != topico]
                                            supabase.table("editais_materias").update({"topicos": novos_topicos}).eq("id", reg['id']).execute()
                                            st.success("✅ Assunto removido!")
                                            time.sleep(1)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Erro: {e}")
                            else:
                                st.info("Nenhum assunto cadastrado.")
                            
                            with st.form(f"add_assunto_{reg['id']}"):
                                novo_assunto = st.text_input("Novo assunto:", key=f"novo_ass_{reg['id']}")
                                if st.form_submit_button("➕ Adicionar", use_container_width=True):
                                    if novo_assunto:
                                        try:
                                            if not topicos:
                                                topicos = []
                                            if novo_assunto not in topicos:
                                                topicos.append(novo_assunto)
                                                supabase.table("editais_materias").update({"topicos": topicos}).eq("id", reg['id']).execute()
                                                st.success("✅ Assunto adicionado!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.warning("⚠️ Este assunto já existe.")
                                        except Exception as e:
                                            st.error(f"❌ Erro: {e}")
                                    else:
                                        st.warning("⚠️ Digite um assunto.")
                
                # Adicionar nova matéria
                st.divider()
                st.markdown("#### ➕ Nova Matéria")
                
                with st.form("form_nova_materia_premium"):
                    nova_materia = st.text_input("Nome da matéria:", placeholder="Ex: Direito Constitucional")
                    
                    if st.form_submit_button("🎯 Adicionar Matéria", use_container_width=True):
                        if nova_materia:
                            try:
                                res_existente = supabase.table("editais_materias").select("*").eq("concurso", missao).eq("materia", nova_materia).execute()
                                if res_existente.data:
                                    st.error("❌ Matéria já existe!")
                                else:
                                    cargo_atual = dados.get('cargo', '')
                                    payload = {
                                        "concurso": missao,
                                        "cargo": cargo_atual,
                                        "materia": nova_materia,
                                        "topicos": ["Geral"]
                                    }
                                    if data_prova_direta:
                                        payload["data_prova"] = data_prova_direta
                                    
                                    supabase.table("editais_materias").insert(payload).execute()
                                    st.success(f"✅ Matéria '{nova_materia}' adicionada!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro: {e}")
                        else:
                            st.warning("⚠️ Digite o nome da matéria.")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            with st.container():
                st.markdown('<div class="premium-card" style="border-color: rgba(255, 75, 75, 0.3); background: linear-gradient(145deg, rgba(255, 75, 75, 0.05), rgba(255, 75, 75, 0.02));">', unsafe_allow_html=True)
                
                st.markdown("### ⚠️ Zona de Perigo")
                st.warning("Esta ação é irreversível e excluirá TODOS os dados desta missão!")
                
                confirm_1 = st.checkbox("✅ Entendo que esta ação não pode ser desfeita")
                confirm_2 = st.checkbox("✅ Confirmo que quero excluir todos os registros")
                confirm_3 = st.checkbox("✅ Estou ciente de que perderei todo o progresso")
                
                if confirm_1 and confirm_2 and confirm_3:
                    st.error("🚨 ATENÇÃO: Ao clicar no botão abaixo, todos os dados serão perdidos permanentemente!")
                    
                    col_btn1, col_btn2 = st.columns(2, gap="20px")
                    with col_btn1:
                        if st.button("🗑️ EXCLUIR MISSÃO", type="primary", use_container_width=True):
                            if excluir_concurso_completo(supabase, missao):
                                st.success("Missão excluída! Redirecionando...")
                                st.session_state.missao_ativa = None
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ Erro ao excluir missão.")
                    
                    with col_btn2:
                        if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                            st.rerun()
                else:
                    st.info("👆 Marque todas as caixas de confirmação para habilitar a exclusão.")
                
                st.markdown('</div>', unsafe_allow_html=True)
