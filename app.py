# app.py (sem bolinhas, apenas números horizontais)

import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu
import calendar

# --- NOVA FUNÇÃO: Cartões de métricas estilo da imagem ---
def render_metric_card_simple(label, value, help_text=None):
    """Renderiza cartões de métricas no estilo da imagem (simples e limpo)"""
    st.markdown(f"""
        <div style="
            text-align: center; 
            padding: 20px 15px; 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            border-radius: 12px;
            background: rgba(26, 28, 35, 0.8);
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="
                color: #adb5bd; 
                font-size: 0.85rem; 
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
                font-weight: 600;
            ">{label}</div>
            <div style="
                font-size: 2.2rem; 
                font-weight: 800; 
                color: #fff;
                line-height: 1;
                margin-bottom: 5px;
            ">{value}</div>
            {"<div style='color: #6c757d; font-size: 0.75rem; margin-top: 5px;'>" + help_text + "</div>" if help_text else ""}
        </div>
    """, unsafe_allow_html=True)

# --- FUNÇÃO ORIGINAL MANTIDA PARA COMPATIBILIDADE ---
def render_metric_card(label, value, icon="📊"):
    st.markdown(f"""
        <div style="text-align: center; padding: 15px; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- ADICIONAR FUNÇÃO PARA BARRA DE PROGRESSO SIMPLES ---
def render_progress_bar(percentage, height=8):
    """Renderiza uma barra de progresso simples"""
    st.markdown(f"""
        <div style="
            width: 100%;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            height: {height}px;
            margin: 8px 0;
            overflow: hidden;
        ">
            <div style="
                height: 100%;
                border-radius: 10px;
                background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
                width: {percentage}%;
            "></div>
        </div>
    """, unsafe_allow_html=True)

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
    except:
        return 0

# --- INICIALIZAÇÃO OBRIGATÓRIA (ÚNICA - sem duplicação) ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# Inicializar estados das metas semanais
if 'meta_horas_semana' not in st.session_state:
    st.session_state.meta_horas_semana = 22  # Valor padrão

if 'meta_questoes_semana' not in st.session_state:
    st.session_state.meta_questoes_semana = 350  # Valor padrão

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# Aplicar estilos base
apply_styles()

# CSS Customizado para Layout Moderno (ATUALIZADO - removido CSS das bolinhas)
st.markdown("""
    <style>
    /* Importar Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* CORREÇÃO CRÍTICA: Ajuste para conteúdo principal EXPANDIR quando sidebar fecha */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
        transition: all 0.3s ease;
    }
    
    /* Quando a sidebar está recolhida, expandir conteúdo */
    [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
        margin-left: 0 !important;
    }
    
    /* Quando a sidebar está expandida, manter padding normal */
    [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: calc(100% - 280px) !important;
        margin-left: 280px !important;
    }

    /* Estilo dos Cards (Glassmorphism) */
    .modern-card {
        background: rgba(26, 28, 35, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s ease, border 0.2s ease;
    }
    .modern-card:hover {
        border: 1px solid rgba(255, 75, 75, 0.4);
        transform: translateY(-2px);
    }

    /* Títulos e Textos */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    /* NOVO: Título estilo da imagem */
    .visao-mes-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .section-subtitle {
        color: #adb5bd;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1.5rem;
    }

    /* Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-red { background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.3); }
    .badge-green { background: rgba(0, 255, 0, 0.1); color: #00FF00; border: 1px solid rgba(0, 255, 0, 0.2); }
    .badge-gray { background: rgba(173, 181, 189, 0.1); color: #adb5bd; border: 1px solid rgba(173, 181, 189, 0.2); }

    /* Progress Bar */
    .modern-progress-container {
        width: 100%;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        height: 8px;
        margin: 10px 0;
        overflow: hidden;
    }
    .modern-progress-fill {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        min-width: 280px !important;
        width: 280px !important;
    }
    
    /* Inputs e Botões */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 8px !important;
    }
    
    /* Menu Lateral Personalizado (ATUALIZADO para corresponder à imagem) */
    .sidebar-menu {
        background: transparent;
        margin-top: 20px;
    }
    
    .sidebar-menu .stRadio {
        background: transparent;
    }
    
    .sidebar-menu .stRadio > div {
        flex-direction: column;
        gap: 5px;
    }
    
    .sidebar-menu .stRadio > div > label {
        background: transparent;
        border-radius: 8px;
        padding: 12px 15px !important;
        margin-bottom: 5px;
        border-left: 0px solid transparent;
        transition: all 0.3s;
        min-height: 50px;
        display: flex;
        align-items: center;
    }
    
    .sidebar-menu .stRadio > div > label:hover {
        background: rgba(255, 75, 75, 0.1);
        border-left: 0px solid rgba(255, 75, 75, 0.5);
    }
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"] div:first-child {
        display: flex;
        align-items: center;
        gap: 12px;
        color: #adb5bd;
        font-weight: 500;
        font-size: 15px !important;
    }
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"] div:first-child span {
        font-size: 18px !important;
    }
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"][aria-checked="true"] {
        background: rgba(255, 75, 75, 0.15);
        border-left: 0px solid #FF4B4B;
    }
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"][aria-checked="true"] div:first-child {
        color: #FF4B4B;
        font-weight: 600;
    }
    
    /* REMOVIDO: Navegação por páginas estilo da imagem (1-6) */
    
    /* Tabela de Disciplinas */
    .disciplina-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        background: rgba(26, 28, 35, 0.3);
        border-radius: 8px;
        overflow: hidden;
    }
    
    .disciplina-table thead {
        background: rgba(255, 75, 75, 0.1);
    }
    
    .disciplina-table th {
        text-align: left;
        padding: 18px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: #FF8E8E;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 1px;
    }
    
    .disciplina-table td {
        padding: 16px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        color: #fff;
        font-size: 0.95rem;
    }
    
    .disciplina-table tr:hover {
        background-color: rgba(255, 75, 75, 0.05);
    }
    
    .disciplina-table tr:last-child td {
        border-bottom: none;
    }
    
    /* Metas Cards */
    .meta-card {
        background: rgba(26, 28, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 25px;
        text-align: center;
        height: 100%;
        position: relative;
    }
    
    .meta-title {
        color: #adb5bd;
        font-size: 1rem;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .meta-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #fff;
        margin: 15px 0;
    }
    
    .meta-progress {
        margin-top: 20px;
    }
    
    .meta-subtitle {
        color: #FF8E8E;
        font-size: 0.9rem;
        margin-top: 10px;
    }
    
    /* Modal de Configuração de Metas */
    .meta-modal {
        background: rgba(26, 28, 35, 0.95);
        border: 1px solid rgba(255, 75, 75, 0.3);
        border-radius: 12px;
        padding: 25px;
        margin-top: 20px;
    }
    
    /* Streak Card */
    .streak-card {
        background: rgba(26, 28, 35, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
    }
    
    .streak-title {
        color: #adb5bd;
        font-size: 1.2rem;
        margin-bottom: 15px;
        font-weight: 600;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .streak-value-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 20px 0;
        gap: 20px;
    }
    
    .streak-value-box {
        flex: 1;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, rgba(255, 75, 75, 0.15), rgba(255, 75, 75, 0.05));
        border-radius: 12px;
        border: 1px solid rgba(255, 75, 75, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .streak-value-label {
        color: #FF8E8E;
        font-size: 1rem;
        margin-bottom: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .streak-value-number {
        font-size: 3rem;
        font-weight: 800;
        color: #FF4B4B;
        margin: 10px 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .streak-period {
        color: #adb5bd;
        font-size: 0.9rem;
        margin-top: 15px;
        text-align: center;
        background: rgba(255, 255, 255, 0.05);
        padding: 8px 15px;
        border-radius: 8px;
        display: inline-block;
    }
    
    /* Estilo para os filtros do Radar de Revisões */
    .stSegmentedControl {
        margin-bottom: 10px;
    }
    
    /* Números de 1 a 31 em linha horizontal ÚNICA - MANTIDO */
    .numeros-mes-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin: 15px 0;
        padding: 15px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        width: 100%;
        max-height: 500px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 75, 75, 0.3) rgba(255, 255, 255, 0.05);
    }
    
    .numeros-mes-container::-webkit-scrollbar {
        height: 6px;
    }
    
    .numeros-mes-container::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 3px;
    }
    
    .numeros-mes-container::-webkit-scrollbar-thumb {
        background: rgba(255, 75, 75, 0.3);
        border-radius: 3px;
    }
    
    .numeros-mes-container::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 75, 75, 0.5);
    }
    
    .numero-dia {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.9rem;
        color: #fff;
        background: rgba(255, 255, 255, 0.1);
        transition: all 0.3s;
        position: relative;
        border: 2px solid transparent;
    }
    
    .numero-dia.hoje {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #000;
        font-weight: 700;
        border: 2px solid rgba(255, 215, 0, 0.7);
        transform: scale(1.1);
    }
    
    .numero-dia.estudou {
        background: linear-gradient(135deg, #00FF00, #00CC00);
        border: 2px solid rgba(0, 255, 0, 0.7);
        color: #fff;
    }
    
    .numero-dia:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Tooltip para números */
    .numero-tooltip {
        position: absolute;
        bottom: calc(100% + 10px);
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.95);
        color: white;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        white-space: nowrap;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s, visibility 0.3s;
        z-index: 1000;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .numero-dia:hover .numero-tooltip {
        opacity: 1;
        visibility: visible;
    }
    
    /* Seção de Constância Melhorada */
    .constancia-section {
        margin-top: 30px;
        padding: 25px;
        background: linear-gradient(135deg, rgba(26, 28, 35, 0.9), rgba(26, 28, 35, 0.7));
        border-radius: 15px;
        border: 1px solid rgba(255, 75, 75, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    .constancia-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .constancia-title {
        color: #fff;
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Ajustes para responsividade */
    @media (max-width: 768px) {
        .streak-value-container {
            flex-direction: column;
            gap: 15px;
        }
        
        .streak-value-box {
            width: 100%;
        }
        
        .numero-dia {
            width: 35px;
            height: 35px;
            font-size: 0.8rem;
        }
    }
    
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES ---
def calcular_countdown(data_str):
    if not data_str: return None, "#adb5bd"
    try:
        dias = (pd.to_datetime(data_str).date() - datetime.date.today()).days
        cor = "#FF4B4B" if dias <= 7 else "#FFD700" if dias <= 30 else "#00FF00"
        return dias, cor
    except: return None, "#adb5bd"

# Formata minutos em '2h 15m'
def formatar_minutos(minutos_totais):
    try:
        minutos = int(minutos_totais)
    except Exception:
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
    except Exception:
        return "0h00min"
    horas = minutos // 60
    minutos_rest = minutos % 60
    return f"{horas}h{minutos_rest:02d}min"

def get_badge_cor(taxa):
    """Retorna classe CSS simples para badges baseado na taxa (0-100)."""
    try:
        t = float(taxa)
    except Exception:
        return "badge-gray"
    if t >= 80:
        return "badge-green"
    if t >= 60:
        return "badge-gray"
    return "badge-red"

def calcular_streak(df):
    """Calcula dias consecutivos até hoje baseado na coluna 'data_estudo'."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
        return 0, 0

# --- FUNÇÃO REMOVIDA: gerar_calendario_estudos (bolinhas) ---

# --- FUNÇÃO MANTIDA: Gerar números de 1 a 31 para visualização horizontal ---
def gerar_numeros_mes(df):
    """Gera os números de 1 a 31 com indicação visual."""
    hoje = datetime.date.today()
    dia_hoje = hoje.day
    # Obter número de dias no mês atual
    _, num_dias_mes = calendar.monthrange(hoje.year, hoje.month)
    
    numeros = []
    
    try:
        # Converte datas de estudo para conjunto de datas
        datas_estudo = set(pd.to_datetime(df['data_estudo']).dt.date.unique())
        
        # Gera os números de 1 até num_dias_mes
        for dia in range(1, num_dias_mes + 1):
            # Verifica se este dia do mês atual foi estudado
            estudou = any(
                data.day == dia and data.month == hoje.month and data.year == hoje.year 
                for data in datas_estudo
            )
            
            numeros.append({
                'numero': dia,
                'estudou': estudou,
                'hoje': dia == dia_hoje
            })
    except Exception:
        # Em caso de erro, gera números básicos
        for dia in range(1, num_dias_mes + 1):
            numeros.append({
                'numero': dia,
                'estudou': False,
                'hoje': dia == dia_hoje
            })
    
    return numeros

# --- NOVA FUNÇÃO: Cálculo dinâmico de intervalos ---
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

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Selecione sua missão ou inicie um novo ciclo</p>', unsafe_allow_html=True)
    
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 Missões Ativas", "➕ Novo Cadastro"])
    
    with tabs[0]:
        if not ed: 
            st.info("Nenhuma missão ativa no momento.")
        else:
            cols = st.columns(2)
            for i, (nome, d_concurso) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="modern-card">
                            <h3 style="margin:0; color:#FF4B4B;">{nome}</h3>
                            <p style="color:#adb5bd; font-size:0.9rem; margin-bottom:15px;">{d_concurso['cargo']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Acessar Missão", key=f"ac_{nome}", use_container_width=True, type="primary"):
                        st.session_state.missao_ativa = nome
                        st.rerun()
    
    with tabs[1]:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("##### Cadastrar Novo Concurso/Edital")
        with st.form("form_novo_concurso", clear_on_submit=True):
            nome_concurso = st.text_input("Nome do Concurso", placeholder="Ex: Receita Federal, TJ-SP, etc.")
            cargo_concurso = st.text_input("Cargo", placeholder="Ex: Auditor Fiscal, Escrevente, etc.")
            informar_data_prova = st.checkbox("Informar data da prova (opcional)")
            if informar_data_prova:
                data_prova_input = st.date_input("Data da Prova")
            else:
                data_prova_input = None
            
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
                        # confirmar inserção
                        try:
                            check = supabase.table("editais_materias").select("data_prova").eq("concurso", nome_concurso).execute()
                            if check.data and len(check.data) > 0:
                                st.success(f"✅ Missão '{nome_concurso}' criada com sucesso!")
                                time.sleep(1)
                                st.session_state.missao_ativa = nome_concurso
                                st.rerun()
                            else:
                                st.warning("Missão criada, mas não foi possível confirmar 'data_prova' no banco. Verifique o supabase.")
                        except Exception:
                            st.success(f"✅ Missão '{nome_concurso}' criada (não foi possível confirmar via consulta).")
                            time.sleep(1)
                            st.session_state.missao_ativa = nome_concurso
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
                else:
                    st.warning("⚠️ Por favor, preencha o nome e o cargo.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()
    
    # --- IMPORTANTE: BUSCA DIRETA DA DATA DA PROVA DO BANCO ---
    try:
        res_data_prova = supabase.table("editais_materias").select("data_prova").eq("concurso", missao).limit(1).execute()
        if res_data_prova.data and len(res_data_prova.data) > 0:
            data_prova_direta = res_data_prova.data[0].get('data_prova')
        else:
            data_prova_direta = None
    except:
        data_prova_direta = None
    
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"<h2 style='color:#FF4B4B; margin-bottom:0;'>{missao}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#adb5bd; font-size:0.9rem; margin-bottom:20px;'>{dados.get('cargo', '')}</p>", unsafe_allow_html=True)
        
        # Botão com seta como na imagem
        if st.button("◀ Voltar à Central", use_container_width=True): 
            st.session_state.missao_ativa = None
            st.rerun()
        
        st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
        
        # Menu personalizado usando st.radio - ATUALIZADO para corresponder à imagem
        opcoes_menu = [
            "🏠 Home",
            "🔄 Revisões", 
            "📝 Registrar",
            "📊 Dashboard",
            "📜 Histórico",
            "⚙️ Configurar"
        ]
        
        menu_selecionado = st.radio(
            "Navegação",
            opcoes_menu,
            index=0,
            label_visibility="collapsed",
            key="sidebar_menu"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # REMOVIDO: Navegação por páginas (1-6) - Conforme solicitado
        
        # Extrair o nome real do menu (remover ícone)
        if "🏠 Home" in menu_selecionado:
            menu = "Home"
        elif "🔄 Revisões" in menu_selecionado:
            menu = "Revisões"
        elif "📝 Registrar" in menu_selecionado:
            menu = "Registrar"
        elif "📊 Dashboard" in menu_selecionado:
            menu = "Dashboard"
        elif "📜 Histórico" in menu_selecionado:
            menu = "Histórico"
        elif "⚙️ Configurar" in menu_selecionado:
            menu = "Configurar"
        else:
            menu = "Home"

    # --- ABA: HOME (PAINEL GERAL) - ATUALIZADO sem bolinhas ---
    if menu == "Home":
        # Título principal
        st.markdown(f'<h1 style="color:#fff; font-size:1.8rem; margin-bottom:0;">{missao}</h1>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:#adb5bd; font-size:1rem; margin-bottom:2rem;">{dados.get("cargo", "")}</p>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("Ainda não há registros. Faça seu primeiro estudo para preencher o painel.")
        else:
            # --- VISÃO DO MÊS ATUAL (como na imagem) ---
            st.markdown('<div class="visao-mes-title">VISÃO DO MÊS ATUAL</div>', unsafe_allow_html=True)
            
            # Calcular métricas
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df['tempo'].sum())
            
            # Formatar tempo como na imagem (3h45min)
            tempo_formatado = formatar_minutos(minutos_totais)
            
            # Dias para a prova
            dias_restantes = None
            if data_prova_direta:
                try:
                    dt_prova = pd.to_datetime(data_prova_direta).date()
                    dias_restantes = (dt_prova - datetime.date.today()).days
                except Exception:
                    dias_restantes = None
            
            # 4 cartões de métricas (como na imagem)
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                render_metric_card_simple("TEMPO TOTAL", tempo_formatado)
            with c2:
                render_metric_card_simple("PRECISÃO", f"{precisao:.1f}%")
            with c3:
                render_metric_card_simple("QUESTÕES", f"{int(t_q)}")
            with c4:
                if dias_restantes is not None:
                    render_metric_card_simple("DIAS PARA A PROVA", f"{dias_restantes}")
                else:
                    render_metric_card_simple("DIAS PARA A PROVA", "—")
            
            st.divider()

            # --- SEÇÃO DE CONSTÂNCIA MELHORADA (SEM BOLINHAS) ---
            st.markdown('<div class="constancia-section">', unsafe_allow_html=True)
            
            streak = calcular_streak(df)
            recorde = calcular_recorde_streak(df)
            inicio_streak, fim_streak = calcular_datas_streak(df)
            
            st.markdown('<div class="constancia-header">', unsafe_allow_html=True)
            st.markdown('<div class="constancia-title">📊 CONSTÂNCIA NOS ESTUDOS</div>', unsafe_allow_html=True)
            
            # Indicador de performance (como na imagem)
            performance = "🟢 Excelente" if streak >= 7 else "🟡 Bom" if streak >= 3 else "🔴 Precisa melhorar"
            st.markdown(f'<div style="color: #FF8E8E; font-size: 0.9rem; font-weight: 600;">{performance}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Stats de constância em 3 colunas
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                st.markdown(f'''
                    <div style="text-align: center; padding: 20px; background: rgba(255, 75, 75, 0.1); border-radius: 10px; border: 1px solid rgba(255, 75, 75, 0.2);">
                        <div style="color: #FF8E8E; font-size: 0.9rem; font-weight: 600; margin-bottom: 8px;">STREAK ATUAL</div>
                        <div style="font-size: 2.8rem; font-weight: 800; color: #FF4B4B; margin: 10px 0;">{streak}</div>
                        <div style="color: #adb5bd; font-size: 0.8rem;">dias consecutivos</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col_s2:
                st.markdown(f'''
                    <div style="text-align: center; padding: 20px; background: rgba(0, 255, 0, 0.1); border-radius: 10px; border: 1px solid rgba(0, 255, 0, 0.2);">
                        <div style="color: #00FF00; font-size: 0.9rem; font-weight: 600; margin-bottom: 8px;">SEU RECORDE</div>
                        <div style="font-size: 2.8rem; font-weight: 800; color: #00FF00; margin: 10px 0;">{recorde}</div>
                        <div style="color: #adb5bd; font-size: 0.8rem;">dias seguidos</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col_s3:
                # Calcular dias estudados no mês
                hoje = datetime.date.today()
                dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
                dias_estudados_mes = len(set(pd.to_datetime(df['data_estudo']).dt.date.unique()))
                percentual_mes = (dias_estudados_mes / dias_no_mes) * 100
                
                st.markdown(f'''
                    <div style="text-align: center; padding: 20px; background: rgba(255, 215, 0, 0.1); border-radius: 10px; border: 1px solid rgba(255, 215, 0, 0.2);">
                        <div style="color: #FFD700; font-size: 0.9rem; font-weight: 600; margin-bottom: 8px;">MÊS ATUAL</div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #FFD700; margin: 10px 0;">{dias_estudados_mes}/{dias_no_mes}</div>
                        <div style="color: #adb5bd; font-size: 0.8rem;">dias estudados ({percentual_mes:.0f}%)</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            # Período do streak atual
            if inicio_streak and fim_streak:
                data_formatada = f"{inicio_streak.strftime('%d/%m')} a {fim_streak.strftime('%d/%m')}"
                st.markdown(f'<div style="text-align: center; margin-top: 15px; color: #adb5bd; font-size: 0.9rem; background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 8px;">Período do streak atual: <span style="color: #FF8E8E; font-weight: 600;">{data_formatada}</span></div>', unsafe_allow_html=True)
            
            # --- LINHA HORIZONTAL COM NÚMEROS DO MÊS (1-31) ---
            st.markdown('<div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); width: 100%;">', unsafe_allow_html=True)
            st.markdown('<div style="color: #adb5bd; font-size: 0.9rem; margin-bottom: 15px; text-align: center; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">DIAS DO MÊS ATUAL</div>', unsafe_allow_html=True)
            
            # Gerar números do mês
            numeros_mes = gerar_numeros_mes(df)
            
            # Mostrar os números em linha horizontal
            st.markdown('<div class="numeros-mes-container">', unsafe_allow_html=True)
            
            for num_info in numeros_mes:
                if num_info['hoje']:
                    classe = "numero-dia hoje"
                    tooltip = f"HOJE - {num_info['numero']}/{datetime.date.today().month}"
                elif num_info['estudou']:
                    classe = "numero-dia estudou"
                    tooltip = f"✓ Dia {num_info['numero']} - Estudou"
                else:
                    classe = "numero-dia"
                    tooltip = f"✗ Dia {num_info['numero']} - Não estudou"
                
                st.markdown(f'''
                <div class="{classe}">
                    {num_info['numero']}
                    <div class="numero-tooltip">{tooltip}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Legenda simplificada
            st.markdown('''
            <div style="display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 15px; padding: 12px; background: rgba(255, 255, 255, 0.03); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                <div style="display: flex; align-items: center; gap: 8px; color: #adb5bd; font-size: 0.8rem;">
                    <div class="numero-dia estudou" style="width: 20px; height: 20px; font-size: 10px;">✓</div>
                    <span>Estudou</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; color: #adb5bd; font-size: 0.8rem;">
                    <div class="numero-dia" style="width: 20px; height: 20px; font-size: 10px;">✗</div>
                    <span>Não estudou</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; color: #adb5bd; font-size: 0.8rem;">
                    <div class="numero-dia hoje" style="width: 20px; height: 20px; font-size: 10px;">H</div>
                    <span>Hoje</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)  # Fecha container números
            
            st.markdown('</div>', unsafe_allow_html=True)  # Fecha constancia-section

            # --- SEÇÃO 3: PAINEL DE DISCIPLINAS ---
            st.markdown('<h3 style="margin-top:2rem; color:#fff;">📊 PAINEL DE DESEMPENHO</h3>', unsafe_allow_html=True)
            
            if not df.empty:
                # Calcular totais por disciplina
                df_disciplinas = df.groupby('materia').agg({
                    'tempo': 'sum',
                    'acertos': 'sum',
                    'total': 'sum',
                    'taxa': 'mean'
                }).reset_index()
                
                df_disciplinas['erros'] = df_disciplinas['total'] - df_disciplinas['acertos']
                df_disciplinas['tempo_formatado'] = df_disciplinas['tempo'].apply(formatar_horas_minutos)
                df_disciplinas['taxa_formatada'] = df_disciplinas['taxa'].round(0).astype(int)
                df_disciplinas = df_disciplinas.sort_values('tempo', ascending=False)
                
                # Criar tabela HTML CORRIGIDA - SIMPLIFICADA
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                # Criar DataFrame para display
                display_df = pd.DataFrame({
                    'DISCIPLINAS': df_disciplinas['materia'],
                    'TEMPO': df_disciplinas['tempo_formatado'],
                    '✓': df_disciplinas['acertos'].astype(int),
                    '✗': df_disciplinas['erros'].astype(int),
                    '🎉': df_disciplinas['total'].astype(int),
                    '%': df_disciplinas['taxa_formatada']
                })
                
                # Exibir tabela usando st.dataframe com formatação condicional
                def color_taxa(val):
                    if val >= 80:
                        return 'color: #00FF00; font-weight: 700;'
                    elif val >= 70:
                        return 'color: #FFD700; font-weight: 700;'
                    else:
                        return 'color: #FF4B4B; font-weight: 700;'
                
                styled_df = display_df.style.applymap(color_taxa, subset=['%'])
                
                # Mostrar tabela
                st.dataframe(
                    styled_df,
                    column_config={
                        "DISCIPLINAS": st.column_config.Column(width="large"),
                        "TEMPO": st.column_config.Column(width="medium"),
                        "✓": st.column_config.Column(width="small"),
                        "✗": st.column_config.Column(width="small"),
                        "🎉": st.column_config.Column(width="small"),
                        "%": st.column_config.Column(width="small")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # --- SEÇÃO 4: METAS DE ESTUDO SEMANAL ---
            st.markdown('<h3 style="margin-top:2rem; color:#fff;">🎯 METAS DE ESTUDO SEMANAL</h3>', unsafe_allow_html=True)
            
            # Estado para controlar a edição das metas
            if 'editando_metas' not in st.session_state:
                st.session_state.editando_metas = False
            
            horas_semana, questoes_semana = calcular_estudos_semana(df)
            meta_horas = st.session_state.meta_horas_semana
            meta_questoes = st.session_state.meta_questoes_semana
            
            # Botão para editar metas
            col_btn1, col_btn2, col_btn3 = st.columns([4, 1, 1])
            with col_btn2:
                if st.button("⚙️ Configurar Metas", key="btn_config_metas", use_container_width=True):
                    st.session_state.editando_metas = not st.session_state.editando_metas
                    st.rerun()
            
            # Modal de edição de metas
            if st.session_state.editando_metas:
                with st.container():
                    st.markdown('<div class="meta-modal">', unsafe_allow_html=True)
                    st.markdown("##### 📝 Configurar Metas Semanais")
                    
                    with st.form("form_metas_semanais"):
                        col_meta1, col_meta2 = st.columns(2)
                        
                        with col_meta1:
                            nova_meta_horas = st.number_input(
                                "Horas de estudo semanais",
                                min_value=1,
                                max_value=100,
                                value=meta_horas,
                                step=1,
                                help="Meta de horas de estudo por semana"
                            )
                        
                        with col_meta2:
                            nova_meta_questoes = st.number_input(
                                "Questões semanais",
                                min_value=1,
                                max_value=1000,
                                value=meta_questoes,
                                step=10,
                                help="Meta de questões resolvidas por semana"
                            )
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
                        if col_btn1.form_submit_button("💾 Salvar Metas", use_container_width=True, type="primary"):
                            st.session_state.meta_horas_semana = nova_meta_horas
                            st.session_state.meta_questoes_semana = nova_meta_questoes
                            st.session_state.editando_metas = False
                            st.success("✅ Metas atualizadas com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        
                        if col_btn2.form_submit_button("❌ Cancelar", use_container_width=True, type="secondary"):
                            st.session_state.editando_metas = False
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Cartões de metas
            col_meta1, col_meta2 = st.columns(2)
            
            with col_meta1:
                progresso_horas = min((horas_semana / meta_horas) * 100, 100) if meta_horas > 0 else 0
                st.markdown(f'''
                <div class="meta-card">
                    <div class="meta-title">Horas de Estudo</div>
                    <div class="meta-value">{horas_semana:.1f}h/{meta_horas}h</div>
                    <div class="meta-progress">
                        <div class="modern-progress-container">
                            <div class="modern-progress-fill" style="width: {progresso_horas}%;"></div>
                        </div>
                    </div>
                    <div class="meta-subtitle">{progresso_horas:.0f}% da meta alcançada</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col_meta2:
                progresso_questoes = min((questoes_semana / meta_questoes) * 100, 100) if meta_questoes > 0 else 0
                st.markdown(f'''
                <div class="meta-card">
                    <div class="meta-title">Questões Resolvidas</div>
                    <div class="meta-value">{int(questoes_semana)}/{meta_questoes}</div>
                    <div class="meta-progress">
                        <div class="modern-progress-container">
                            <div class="modern-progress-fill" style="width: {progresso_questoes}%;"></div>
                        </div>
                    </div>
                    <div class="meta-subtitle">{progresso_questoes:.0f}% da meta alcançada</div>
                </div>
                ''', unsafe_allow_html=True)

    # --- ABA: REVISÕES ---
    elif menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        
        # CORREÇÃO: Filtros organizados corretamente
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            filtro_rev = st.segmented_control(
                "Visualizar:", 
                ["Pendentes/Hoje", "Todas (incluindo futuras)"], 
                default="Pendentes/Hoje",
                key="filtro_rev"
            )
        with c2:
            # CORREÇÃO: Ordem corrigida para mostrar Fácil ao lado de Médio
            filtro_dif = st.segmented_control(
                "Dificuldade:", 
                ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"], 
                default="Todas",
                key="filtro_dif"
            )
    
        # Usar função com cache para melhor performance
        pend = calcular_revisoes_pendentes(df, filtro_rev, filtro_dif)
        
        if not pend: 
            st.success("✨ Tudo em dia! Aproveite para avançar no conteúdo.")
        else:
            pend = sorted(pend, key=lambda x: (x['dificuldade'] != "🔴 Difícil", x['data_prevista']))
            
            # 📊 Resumo rápido
            st.markdown("##### 📊 Resumo de Revisões Pendentes")
            col_res1, col_res2, col_res3 = st.columns(3)
            
            # Contar por dificuldade
            dif_count = len([p for p in pend if p['dificuldade'] == "🔴 Difícil"])
            med_count = len([p for p in pend if p['dificuldade'] == "🟡 Médio"])
            fac_count = len([p for p in pend if p['dificuldade'] == "🟢 Fácil"])
            
            with col_res1:
                st.metric("🔴 Difícil", dif_count)
            with col_res2:
                st.metric("🟡 Médio", med_count)
            with col_res3:
                st.metric("🟢 Fácil", fac_count)
            
            st.divider()
            
            # Listar revisões pendentes
            st.markdown("##### 📋 Lista de Revisões")
            for p in pend:
                with st.container():
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    c_info, c_input, c_action = st.columns([2, 1.5, 1])
                    
                    with c_info:
                        badge_class = "badge-red" if p['atraso'] > 0 else "badge-green" if p['atraso'] == 0 else "badge-gray"
                        status_text = f"⚠️ {p['atraso']}d atraso" if p['atraso'] > 0 else "🎯 Vence hoje" if p['atraso'] == 0 else "📅 Futura"
                        
                        # Mostrar dificuldade e recomendação de tempo
                        tempo_rec, desc = tempo_recomendado_rev24h(p['dificuldade'])
                        
                        st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                                <span class="badge {badge_class}">{status_text}</span>
                                <span class="badge badge-gray">{p['dificuldade']}</span>
                                <span style="color: #adb5bd; font-size: 12px;">{p['data_prevista'].strftime('%d/%m/%Y')}</span>
                            </div>
                            <h4 style="margin:0; color:#fff;">{p['materia']}</h4>
                            <p style="color:#adb5bd; font-size:0.85rem; margin:0;">{p['assunto']} • <b>{p['tipo']}</b></p>
                            <p style="color:#FF8E8E; font-size:0.75rem; margin-top:8px;">⏱️ {desc} (~{tempo_rec}min)</p>
                        """, unsafe_allow_html=True)
                        
                        if p['coment']:
                            with st.expander("📝 Ver Anotações"):
                                st.info(p['coment'])
                    
                    with c_input:
                        st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
                        ci1, ci2 = st.columns(2)
                        acr_rev = ci1.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['col']}", help="Acertos na revisão")
                        tor_rev = ci2.number_input("Total", 0, key=f"to_{p['id']}_{p['col']}", help="Total de questões na revisão")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with c_action:
                        st.write("") # Alinhamento
                        if st.button("CONCLUIR", key=f"btn_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
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

    # --- ABA: REGISTRAR ---
    elif menu == "Registrar":
        st.markdown('<h2 class="main-title">📝 Novo Registro de Estudo</h2>', unsafe_allow_html=True)
        mats = list(dados.get('materias', {}).keys())
        
        if not mats:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'Configurar' para adicionar disciplinas.")
        else:
            with st.container():
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                c1, c2 = st.columns([2, 1])
                dt_reg = c1.date_input("Data do Estudo", format="DD/MM/YYYY")
                tm_reg = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30min")
                
                mat_reg = st.selectbox("Disciplina", mats)
                assuntos_disponiveis = dados['materias'].get(mat_reg, ["Geral"])
                ass_reg = st.selectbox("Assunto", assuntos_disponiveis, key=f"assunto_select_{mat_reg}")
                
                st.divider()
                
                with st.form("form_registro_final", clear_on_submit=True):
                    ca_reg, ct_reg = st.columns(2)
                    ac_reg = ca_reg.number_input("Questões Acertadas", 0)
                    to_reg = ct_reg.number_input("Total de Questões", 1)
                    
                    # NOVO: Classificação de Dificuldade
                    st.markdown("##### 🎯 Como foi esse assunto?")
                    dif_reg = st.segmented_control(
                        "Classificação:",
                        ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                        default="🟡 Médio"
                    )
                    
                    # Mostrar recomendação baseada na dificuldade
                    tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_reg)
                    st.info(f"💡 **{dif_reg}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                    
                    st.divider()
                    
                    com_reg = st.text_area("Anotações / Comentários", placeholder="O que você aprendeu ou sentiu dificuldade?")
                    
                    btn_salvar = st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True, type="primary")
                    
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
                                "dificuldade": dif_reg,  # Novo campo
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
                            st.error(f"Erro ao salvar: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        if df.empty:
            t_q, precisao, horas = 0, 0, 0
        else:
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q > 0 else 0)
            horas = df['tempo'].sum()/60
        
        # Exibe os cartões - APENAS 3 CARTÕES, SEM DATA DA PROVA
        m1, m2, m3 = st.columns(3)
        with m1: render_metric_card("Questões", int(t_q), "📝")
        with m2: render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
        with m3: render_metric_card("Horas", f"{horas:.1f}h", "⏱️")
        
        st.divider()

        # 3. GRÁFICO DE EVOLUÇÃO (CORRIGIDO)
        if not df.empty:
            st.subheader("📈 Evolução de Acertos")
            try:
                # Agrupa pela coluna certa: 'data_estudo'
                df_evo = df.groupby('data_estudo')['acertos'].sum().reset_index()
                st.line_chart(df_evo.set_index('data_estudo'))
            except Exception as e:
                st.error(f"Erro ao gerar gráfico: {e}")
        else:
            st.info("📚 Registre seus primeiros estudos para ver o gráfico de evolução!")

        # 4. GRÁFICOS PLOTLY (se houver dados)
        if not df.empty:
            # Gráficos
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Distribuição por Matéria")
                fig_pie = px.pie(df, values='total', names='materia', hole=0.6, 
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True, 
                                     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                     font=dict(color="#fff"))
                st.plotly_chart(fig_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c_g2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Evolução de Precisão")
                df_ev = df.groupby('data_estudo')['taxa'].mean().reset_index()
                fig_line = px.line(df_ev, x='data_estudo', y='taxa', markers=True)
                fig_line.update_traces(line_color='#FF4B4B', marker=dict(size=8))
                fig_line.update_layout(margin=dict(t=20, b=0, l=0, r=0), 
                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      font=dict(color="#fff"), xaxis_title=None, yaxis_title="Taxa %")
                st.plotly_chart(fig_line, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Detalhamento por Matéria
            st.markdown("### 📁 Detalhamento por Disciplina")
            df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
            
            for _, m in df_mat.iterrows():
                with st.expander(f"{m['materia'].upper()} — {m['taxa']:.1f}% de Precisão"):
                    with st.container(border=True):
                        df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                        for _, a in df_ass.iterrows():
                            ca1, ca2 = st.columns([4, 1])
                            ca1.markdown(f"<span style='color:#fff; font-size:0.9rem; font-weight:600;'>{a['assunto']}</span>", unsafe_allow_html=True)
                            ca2.markdown(f"<p style='text-align: right; color:#adb5bd; font-size: 0.8rem;'>{int(a['acertos'])}/{int(a['total'])}</p>", unsafe_allow_html=True)
                            st.markdown(f"""
                                <div class="modern-progress-container" style="margin-top: 5px; margin-bottom: 15px;">
                                    <div class="modern-progress-fill" style="width: {a['taxa']}%;"></div>
                                </div>
                            """, unsafe_allow_html=True)

    # --- ABA: HISTÓRICO ---
    elif menu == "Histórico":
        st.markdown('<h2 class="main-title">📜 Histórico de Estudos</h2>', unsafe_allow_html=True)
        
        if not df.empty:
            df_h = df.copy()
            df_h['data_estudo_display'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
            # Filtros
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                mat_filter = st.selectbox("Filtrar por Matéria:", ["Todas"] + list(df_h['materia'].unique()), key="mat_hist_filter")
            with col_f2:
                ordem = st.selectbox("Ordenar por:", ["Mais Recente", "Mais Antigo", "Maior Taxa", "Menor Taxa"], key="ord_hist")
            with col_f3:
                st.write("")  # Espaçamento
            
            # Aplicar filtros
            df_filtered = df_h.copy()
            if mat_filter != "Todas":
                df_filtered = df_filtered[df_filtered['materia'] == mat_filter]
            
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
            
            col_info1, col_info2, col_info3 = st.columns(3)
            col_info1.metric("📝 Registros", total_registros)
            col_info2.metric("🎯 Taxa Média", f"{taxa_media:.1f}%")
            col_info3.metric("⏱️ Tempo Total", f"{tempo_total:.1f}h")
            
            st.divider()
            
            # --- MODAL DE EDIÇÃO ---
            if st.session_state.edit_id is not None:
                registro_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
                
                st.markdown('<div class="modern-card" style="border: 2px solid rgba(255, 75, 75, 0.3); background: rgba(255, 75, 75, 0.05);">', unsafe_allow_html=True)
                st.markdown("### ✏️ Editar Registro")
                
                with st.form("form_edit_registro", clear_on_submit=False):
                    col_e1, col_e2 = st.columns([2, 1])
                    dt_edit = col_e1.date_input(
                        "Data do Estudo", 
                        value=pd.to_datetime(registro_edit['data_estudo']).date(), 
                        format="DD/MM/YYYY", 
                        key="dt_edit"
                    )
                    tm_edit = col_e2.text_input(
                        "Tempo (HHMM)", 
                        value=f"{int(registro_edit['tempo']//60):02d}{int(registro_edit['tempo']%60):02d}", 
                        key="tm_edit"
                    )
                    
                    mat_edit = st.selectbox(
                        "Disciplina", 
                        list(dados.get('materias', {}).keys()), 
                        index=list(dados.get('materias', {}).keys()).index(registro_edit['materia']), 
                        key="mat_edit"
                    )
                    assuntos_edit = dados['materias'].get(mat_edit, ["Geral"])
                    ass_edit = st.selectbox(
                        "Assunto", 
                        assuntos_edit, 
                        index=assuntos_edit.index(registro_edit['assunto']) if registro_edit['assunto'] in assuntos_edit else 0, 
                        key="ass_edit"
                    )
                    
                    st.divider()
                    
                    ca_edit, ct_edit = st.columns(2)
                    ac_edit = ca_edit.number_input("Questões Acertadas", value=int(registro_edit['acertos']), min_value=0, key="ac_edit")
                    to_edit = ct_edit.number_input("Total de Questões", value=int(registro_edit['total']), min_value=1, key="to_edit")
                    
                    # Dificuldade
                    st.markdown("##### 🎯 Classificação de Dificuldade")
                    dif_edit = st.segmented_control(
                        "Classificação:",
                        ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                        default=registro_edit.get('dificuldade', '🟡 Médio'),
                        key="dif_edit"
                    )
                    
                    tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_edit)
                    st.info(f"💡 **{dif_edit}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                    
                    st.divider()
                    
                    com_edit = st.text_area(
                        "Anotações / Comentários", 
                        value=registro_edit.get('comentarios', ''), 
                        key="com_edit",
                        height=100
                    )
                    
                    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
                    
                    if col_btn1.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True, type="primary"):
                        try:
                            t_b = formatar_tempo_para_bigint(tm_edit)
                            taxa = (ac_edit/to_edit*100 if to_edit > 0 else 0)
                            
                            supabase.table("registros_estudos").update({
                                "data_estudo": dt_edit.strftime('%Y-%m-%d'),
                                "materia": mat_edit,
                                "assunto": ass_edit,
                                "acertos": ac_edit,
                                "total": to_edit,
                                "taxa": taxa,
                                "dificuldade": dif_edit,
                                "comentarios": com_edit,
                                "tempo": t_b
                            }).eq("id", st.session_state.edit_id).execute()
                            
                            st.success("✅ Registro atualizado com sucesso!")
                            time.sleep(1)
                            st.session_state.edit_id = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao atualizar: {e}")
                    
                    if col_btn2.form_submit_button("❌ CANCELAR", use_container_width=True, type="secondary"):
                        st.session_state.edit_id = None
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.divider()
            
            # --- LISTA DE REGISTROS ---
            st.markdown("##### 📝 Gerenciar Registros")
            
            if len(df_filtered) == 0:
                st.info("Nenhum registro encontrado com os filtros selecionados.")
            else:
                for index, row in df_filtered.iterrows():
                    with st.container():
                        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                        
                        # Layout principal
                        info_col, metrics_col, action_col = st.columns([3, 1.5, 1.2])
                        
                        with info_col:
                            # Informações do Registro
                            taxa_color = "#00FF00" if row['taxa'] >= 80 else "#FFD700" if row['taxa'] >= 60 else "#FF4B4B"
                            
                            st.markdown(f"""
                                <div style="margin-bottom: 8px;">
                                    <span style="color: #adb5bd; font-size: 0.85rem; font-weight: 600;">📅 {row['data_estudo_display']}</span>
                                    <span style="color: {taxa_color}; font-size: 0.85rem; font-weight: 700; margin-left: 15px;">
                                        {row['taxa']:.1f}%
                                    </span>
                                    <span style="color: #adb5bd; font-size: 0.85rem; margin-left: 15px;">
                                        {row.get('dificuldade', '🟡 Médio')}
                                    </span>
                                </div>
                                <h4 style="margin: 0; color: #fff; font-size: 1.1rem;">{row['materia']}</h4>
                                <p style="color: #adb5bd; font-size: 0.9rem; margin: 5px 0 0 0;">{row['assunto']}</p>
                            """, unsafe_allow_html=True)
                            
                            # Anotações
                            if row.get('comentarios'):
                                with st.expander("📝 Ver Anotações", expanded=False):
                                    st.markdown(f"<p style='color: #adb5bd; font-size: 0.9rem;'>{row['comentarios']}</p>", unsafe_allow_html=True)
                        
                        with metrics_col:
                            # Métricas
                            st.markdown(f"""
                                <div style="text-align: right;">
                                    <div style="font-size: 0.8rem; color: #adb5bd; margin-bottom: 5px;">Desempenho</div>
                                    <div style="font-size: 1.3rem; font-weight: 700; color: #fff;">
                                        {int(row['acertos'])}/{int(row['total'])}
                                    </div>
                                    <div style="font-size: 0.75rem; color: #adb5bd;">
                                        ⏱️ {int(row['tempo']//60)}h{int(row['tempo']%60):02d}m
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with action_col:
                            col_a1, col_a2 = st.columns(2, gap="small")
                            
                            # Botão Editar
                            if col_a1.button("✏️", key=f"edit_{row['id']}", help="Editar registro", use_container_width=True):
                                st.session_state.edit_id = row['id']
                                st.rerun()
                            
                            # Botão Excluir com confirmação
                            if col_a2.button("🗑️", key=f"del_{row['id']}", help="Excluir registro", use_container_width=True):
                                try:
                                    # Confirmação via dialog
                                    if st.session_state.get(f"confirm_delete_{row['id']}", False):
                                        supabase.table("registros_estudos").delete().eq("id", row['id']).execute()
                                        st.toast("✅ Registro excluído com sucesso!", icon="✅")
                                        time.sleep(0.5)
                                        st.session_state[f"confirm_delete_{row['id']}"] = False
                                        st.rerun()
                                    else:
                                        st.session_state[f"confirm_delete_{row['id']}"] = True
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir: {e}")
                            
                            # Confirmação visual
                            if st.session_state.get(f"confirm_delete_{row['id']}", False):
                                st.warning(f"⚠️ Clique em 🗑️ novamente para confirmar exclusão", icon="⚠️")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📚 Nenhum registro de estudo encontrado ainda. Comece a estudar!")

    # --- ABA: CONFIGURAR ---
    elif menu == "Configurar":
        st.markdown('<h2 class="main-title">⚙️ Configurar Missão</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Editar dados do edital ativo</p>', unsafe_allow_html=True)

        # Mostrar data atual se existir
        try:
            data_prova_atual = pd.to_datetime(data_prova_direta).date() if data_prova_direta else None
        except Exception:
            data_prova_atual = None

        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('### Dados do Edital', unsafe_allow_html=True)
            st.write(f"**Concurso:** {missao}")
            st.write(f"**Cargo:** {dados.get('cargo', '—')}")
            st.write(f"**Data da Prova (atual):** {data_prova_atual.strftime('%d/%m/%Y') if data_prova_atual else '—'}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Formulário para editar data da prova
        with st.form("form_editar_edital"):
            st.markdown("### 📅 Ajustar Data da Prova")
            
            nova_data_escolhida = st.date_input(
                "Selecione a data da prova", 
                value=(data_prova_atual or datetime.date.today())
            )
            
            remover = st.checkbox("Remover data da prova (deixar em branco)")

            submitted = st.form_submit_button("Salvar alterações", use_container_width=True, type="primary")
            
            if submitted:
                try:
                    valor_final = None if remover else nova_data_escolhida.strftime("%Y-%m-%d")
                    
                    # 1. SALVA NO BANCO - Atualiza a tabela CORRETA: editais_materias
                    res = supabase.table("editais_materias").update({"data_prova": valor_final}).eq("concurso", missao).execute()
                    
                    if res.data:
                        # 2. LIMPA A MEMÓRIA DO APP
                        st.cache_data.clear() 
                        
                        # 3. ATUALIZA O ESTADO PARA FORÇAR RECARREGAMENTO
                        st.session_state.missao_ativa = missao
                        
                        st.success(f"✅ Data atualizada no banco! Recarregando...")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {e}")

        # Seção para adicionar/gerenciar matérias
        st.divider()
        st.markdown("### 📚 Gerenciar Matérias")
        
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
            # Mostrar matérias atuais
            if 'materias' in dados and dados['materias']:
                st.markdown("**Matérias cadastradas:**")
                for materia, topicos in dados['materias'].items():
                    with st.expander(f"📖 {materia}"):
                        st.markdown(f"**Tópicos:** {', '.join(topicos)}")
            else:
                st.info("Nenhuma matéria cadastrada ainda.")
            
            # Formulário para adicionar nova matéria
            with st.form("form_nova_materia"):
                st.markdown("#### Adicionar Nova Matéria")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    nova_materia = st.text_input("Nome da Matéria", placeholder="Ex: Direito Constitucional")
                
                with col2:
                    st.write("")  # Espaçamento
                    st.write("")  # Espaçamento
                    if st.form_submit_button("➕ Adicionar", use_container_width=True):
                        if nova_materia:
                            # Aqui você precisaria implementar a lógica para salvar no banco
                            st.success(f"Matéria '{nova_materia}' adicionada (lógica de banco a implementar)")
                            time.sleep(1)
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

        # Botão para excluir o concurso
        st.divider()
        st.markdown("### ⚠️ Zona de Perigo")
        
        with st.container():
            st.markdown('<div class="modern-card" style="border: 2px solid rgba(255, 75, 75, 0.3); background: rgba(255, 75, 75, 0.05);">', unsafe_allow_html=True)
            
            st.warning("Esta ação é irreversível!")
            if st.button("🗑️ Excluir Missão Completa", type="secondary", use_container_width=True):
                # Confirmação adicional
                confirmacao = st.checkbox("Confirmo que quero excluir TODOS os dados desta missão")
                if confirmacao:
                    if excluir_concurso_completo(supabase, missao):  # Função do logic.py
                        st.error("Missão excluída! Redirecionando...")
                        st.session_state.missao_ativa = None
                        time.sleep(2)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
