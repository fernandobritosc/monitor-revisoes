# app.py (com Dashboard Avançado e Planejador)

import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import time
import calendar
import numpy as np
from scipy import stats

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

# --- NOVAS FUNÇÕES PARA DASHBOARD AVANÇADO ---

def gerar_heatmap_estudos(df):
    """Gera um heatmap estilo GitHub contributions dos estudos"""
    if df.empty:
        return None
    
    try:
        # Converter data para datetime
        df['data'] = pd.to_datetime(df['data_estudo'])
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month
        df['dia'] = df['data'].dt.day
        df['dia_semana'] = df['data'].dt.dayofweek  # 0=segunda, 6=domingo
        
        # Agrupar por data e calcular métricas
        df_agrupado = df.groupby('data').agg({
            'tempo': 'sum',
            'total': 'sum',
            'acertos': 'sum'
        }).reset_index()
        
        # Criar dataframe com todas as datas dos últimos 6 meses
        data_fim = datetime.date.today()
        data_inicio = data_fim - timedelta(days=180)  # 6 meses
        
        todas_datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
        df_todas_datas = pd.DataFrame({'data': todas_datas})
        
        # Mesclar com dados reais
        df_todas_datas = df_todas_datas.merge(df_agrupado, on='data', how='left')
        df_todas_datas.fillna(0, inplace=True)
        
        # Calcular intensidade (0-4 baseado no tempo de estudo)
        # 0: 0min, 1: 1-30min, 2: 31-90min, 3: 91-180min, 4: 180+ min
        df_todas_datas['intensidade'] = pd.cut(
            df_todas_datas['tempo'] / 60,  # converter para horas
            bins=[-1, 0, 0.5, 1.5, 3, float('inf')],
            labels=[0, 1, 2, 3, 4]
        ).astype(int)
        
        # Preparar dados para o heatmap
        df_todas_datas['ano'] = df_todas_datas['data'].dt.year
        df_todas_datas['mes'] = df_todas_datas['data'].dt.month
        df_todas_datas['dia'] = df_todas_datas['data'].dt.day
        df_todas_datas['dia_semana'] = df_todas_datas['data'].dt.dayofweek
        df_todas_datas['semana_ano'] = df_todas_datas['data'].dt.isocalendar().week
        
        return df_todas_datas
    
    except Exception as e:
        st.error(f"Erro ao gerar heatmap: {e}")
        return None

def criar_grafico_burndown(df, meta_horas, meta_questoes):
    """Cria gráfico de burndown para a semana atual"""
    if df.empty:
        return None
    
    hoje = datetime.date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda-feira
    fim_semana = inicio_semana + timedelta(days=6)  # Domingo
    
    # Filtrar dados da semana
    df['data_estudo_date'] = pd.to_datetime(df['data_estudo']).dt.date
    df_semana = df[(df['data_estudo_date'] >= inicio_semana) & (df['data_estudo_date'] <= fim_semana)]
    
    if df_semana.empty:
        return None
    
    # Criar dataframe com todos os dias da semana
    dias_semana = [inicio_semana + timedelta(days=i) for i in range(7)]
    df_burndown = pd.DataFrame({'data': dias_semana})
    
    # Calcular acumulado real
    acumulado_horas = []
    acumulado_questoes = []
    horas_acum = 0
    questoes_acum = 0
    
    for dia in dias_semana:
        dados_dia = df_semana[df_semana['data_estudo_date'] == dia]
        if not dados_dia.empty:
            horas_acum += dados_dia['tempo'].sum() / 60
            questoes_acum += dados_dia['total'].sum()
        acumulado_horas.append(horas_acum)
        acumulado_questoes.append(questoes_acum)
    
    df_burndown['horas_acumulado'] = acumulado_horas
    df_burndown['questoes_acumulado'] = acumulado_questoes
    
    # Calcular meta ideal (linear)
    meta_horas_diaria = meta_horas / 7
    meta_questoes_diaria = meta_questoes / 7
    
    df_burndown['meta_horas_ideal'] = [meta_horas_diaria * (i+1) for i in range(7)]
    df_burndown['meta_questoes_ideal'] = [meta_questoes_diaria * (i+1) for i in range(7)]
    
    return df_burndown

def prever_desempenho(df, data_prova):
    """Prever desempenho na prova baseado no histórico"""
    if df.empty or data_prova is None:
        return None, None, None
    
    try:
        # Converter data da prova
        data_prova_dt = pd.to_datetime(data_prova).date()
        hoje = datetime.date.today()
        
        # Calcular dias até a prova
        dias_ate_prova = (data_prova_dt - hoje).days
        
        if dias_ate_prova <= 0:
            return None, None, None
        
        # Preparar dados históricos
        df['data_estudo_date'] = pd.to_datetime(df['data_estudo']).dt.date
        df = df.sort_values('data_estudo_date')
        
        # Calcular média móvel das últimas 4 semanas
        data_limite = hoje - timedelta(days=28)  # 4 semanas
        df_recente = df[df['data_estudo_date'] >= data_limite]
        
        if df_recente.empty:
            # Usar todos os dados se não houver dados recentes
            df_recente = df
        
        # Calcular taxa de acerto média
        taxa_media = df_recente['taxa'].mean()
        
        # Calcular tendência (regressão linear simples)
        if len(df_recente) > 1:
            # Criar índice numérico para regressão
            df_recente = df_recente.copy()
            df_recente['dias_desde_inicio'] = (df_recente['data_estudo_date'] - df_recente['data_estudo_date'].min()).dt.days
            
            # Regressão linear
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                df_recente['dias_desde_inicio'], 
                df_recente['taxa']
            )
            
            # Prever para o dia da prova
            dias_totais = (data_prova_dt - df_recente['data_estudo_date'].min()).days
            previsao = intercept + slope * dias_totais
            
            # Limitar previsão entre 0 e 100
            previsao = max(0, min(100, previsao))
            
            # Calcular intervalo de confiança (simplificado)
            erro_padrao = std_err * np.sqrt(1 + 1/len(df_recente) + 
                                          (dias_totais - df_recente['dias_desde_inicio'].mean())**2 / 
                                          np.sum((df_recente['dias_desde_inicio'] - df_recente['dias_desde_inicio'].mean())**2))
            
            limite_inferior = previsao - 1.96 * erro_padrao
            limite_superior = previsao + 1.96 * erro_padrao
            
            return previsao, limite_inferior, limite_superior
        else:
            # Não há dados suficientes para regressão
            return taxa_media, taxa_media - 5, taxa_media + 5
    
    except Exception as e:
        st.error(f"Erro na previsão: {e}")
        return None, None, None

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# Inicializar estados das metas semanais
if 'meta_horas_semana' not in st.session_state:
    st.session_state.meta_horas_semana = 22  # Valor padrão

if 'meta_questoes_semana' not in st.session_state:
    st.session_state.meta_questoes_semana = 350  # Valor padrão

# Inicializar estados para renomear matérias
if 'editando_metas' not in st.session_state:
    st.session_state.editando_metas = False

# Inicializar estados para controle de edição de matérias
if 'renomear_materia' not in st.session_state:
    st.session_state.renomear_materia = {}

# Inicializar o estado do menu
if 'menu_atual' not in st.session_state:
    st.session_state.menu_atual = "Home"

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# Aplicar estilos base
apply_styles()

# CSS Customizado para Layout Moderno
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
    
    /* Menu Lateral Personalizado */
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
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"][aria-checked="true"] {
        background: rgba(255, 75, 75, 0.15);
        border-left: 0px solid #FF4B4B;
    }
    
    .sidebar-menu .stRadio > div > label[data-baseweb="radio"][aria-checked="true"] div:first-child {
        color: #FF4B4B;
        font-weight: 600;
    }
    
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
    }
    
    </style>
""", unsafe_allow_html=True)

# --- NOVA FUNÇÃO: Processar assuntos em massa ---
def processar_assuntos_em_massa(texto, separador=";"):
    """
    Processa um texto com múltiplos assuntos separados por um separador.
    Retorna uma lista limpa de assuntos.
    """
    if not texto:
        return []
    
    # Remove espaços em branco no início e fim
    texto = texto.strip()
    
    # Processa baseado no separador
    if separador == ";":
        assuntos = texto.split(";")
    elif separador == ",":
        assuntos = texto.split(",")
    elif separador == "linha":
        # Divide por quebras de linha
        assuntos = texto.split("\n")
    elif separador == "ponto":
        # Divide por ponto
        assuntos = texto.split(".")
    else:
        assuntos = [texto]
    
    # Limpa cada assunto
    assuntos_limpos = []
    for assunto in assuntos:
        assunto = assunto.strip()
        # Remove caracteres especiais no início/fim
        assunto = re.sub(r'^[^a-zA-Z0-9]*|[^a-zA-Z0-9]*$', '', assunto)
        if assunto:  # Só adiciona se não estiver vazio
            assuntos_limpos.append(assunto)
    
    return assuntos_limpos

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
        
        # Lógica de Ciclos Longos (ADAPTATIVA)
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
        
        # Menu personalizado usando st.radio
        opcoes_menu = [
            "🏠 Home",
            "🔄 Revisões", 
            "📝 Registrar",
            "📊 Dashboard",
            "📋 Planejador",  # NOVA ABA
            "📜 Histórico",
            "⚙️ Configurar"
        ]
        
        # Use uma chave fixa para o radio
        menu_selecionado = st.radio(
            "Navegação",
            opcoes_menu,
            index=opcoes_menu.index(f"🏠 Home") if f"🏠 Home" in opcoes_menu else 0,
            label_visibility="collapsed",
            key="sidebar_menu_radio"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Atualizar o estado do menu baseado na seleção
        if "🏠 Home" in menu_selecionado:
            st.session_state.menu_atual = "Home"
        elif "🔄 Revisões" in menu_selecionado:
            st.session_state.menu_atual = "Revisões"
        elif "📝 Registrar" in menu_selecionado:
            st.session_state.menu_atual = "Registrar"
        elif "📊 Dashboard" in menu_selecionado:
            st.session_state.menu_atual = "Dashboard"
        elif "📋 Planejador" in menu_selecionado:  # NOVA ABA
            st.session_state.menu_atual = "Planejador"
        elif "📜 Histórico" in menu_selecionado:
            st.session_state.menu_atual = "Histórico"
        elif "⚙️ Configurar" in menu_selecionado:
            st.session_state.menu_atual = "Configurar"

    # Usar o estado atual do menu
    menu = st.session_state.menu_atual

    # --- ABA: HOME (PAINEL GERAL) ---
    if menu == "Home":
        # Título principal
        st.markdown(f'<h1 style="color:#fff; font-size:1.8rem; margin-bottom:0;">{missao}</h1>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:#adb5bd; font-size:1rem; margin-bottom:2rem;">{dados.get("cargo", "")}</p>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("Ainda não há registros. Faça seu primeiro estudo para preencher o painel.")
        else:
            # --- VISÃO DO MÊS ATUAL ---
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

            # --- SEÇÃO DE CONSTÂNCIA MELHORADA ---
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
        st.markdown('<h2 class="main-title">📊 Dashboard Avançado</h2>', unsafe_allow_html=True)
        
        if df.empty:
            t_q, precisao, horas = 0, 0, 0
        else:
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q > 0 else 0)
            horas = df['tempo'].sum()/60
        
        # Exibe os cartões básicos
        m1, m2, m3 = st.columns(3)
        with m1: render_metric_card("Questões", int(t_q), "📝")
        with m2: render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
        with m3: render_metric_card("Horas", f"{horas:.1f}h", "⏱️")
        
        st.divider()
        
        # --- NOVA SEÇÃO: DASHBOARD AVANÇADO ---
        st.markdown('<h3 style="color:#fff; margin-top:2rem;">📈 Dashboard Preditivo</h3>', unsafe_allow_html=True)
        
        if not df.empty:
            # 1. HEATMAP DE ESTUDOS
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### 🔥 Heatmap de Estudos (últimos 6 meses)")
            
            # Gerar dados do heatmap
            df_heatmap = gerar_heatmap_estudos(df)
            
            if df_heatmap is not None:
                # Criar heatmap com Plotly
                meses = df_heatmap['mes'].unique()
                semanas = df_heatmap['semana_ano'].unique()
                
                # Preparar matriz para heatmap
                heatmap_data = []
                for semana in sorted(semanas):
                    semana_data = []
                    for dia in range(7):  # 0-6 (segunda a domingo)
                        dados = df_heatmap[(df_heatmap['semana_ano'] == semana) & 
                                          (df_heatmap['dia_semana'] == dia)]
                        if not dados.empty:
                            semana_data.append(dados['intensidade'].iloc[0])
                        else:
                            semana_data.append(0)
                    heatmap_data.append(semana_data)
                
                # Criar heatmap
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_data,
                    colorscale=[
                        [0, 'rgba(255, 255, 255, 0.1)'],
                        [0.25, 'rgba(255, 75, 75, 0.3)'],
                        [0.5, 'rgba(255, 75, 75, 0.5)'],
                        [0.75, 'rgba(255, 75, 75, 0.7)'],
                        [1, 'rgba(255, 75, 75, 1)']
                    ],
                    showscale=False
                ))
                
                fig_heatmap.update_layout(
                    height=300,
                    margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        tickmode='array',
                        tickvals=list(range(7)),
                        ticktext=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                        showgrid=False
                    ),
                    yaxis=dict(showgrid=False)
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Legenda
                col_leg1, col_leg2, col_leg3, col_leg4, col_leg5 = st.columns(5)
                with col_leg1:
                    st.markdown('<div style="text-align:center;"><div style="width:20px;height:20px;background:rgba(255,255,255,0.1);margin:0 auto;"></div><div style="font-size:0.7rem;color:#adb5bd;">0min</div></div>', unsafe_allow_html=True)
                with col_leg2:
                    st.markdown('<div style="text-align:center;"><div style="width:20px;height:20px;background:rgba(255,75,75,0.3);margin:0 auto;"></div><div style="font-size:0.7rem;color:#adb5bd;">1-30min</div></div>', unsafe_allow_html=True)
                with col_leg3:
                    st.markdown('<div style="text-align:center;"><div style="width:20px;height:20px;background:rgba(255,75,75,0.5);margin:0 auto;"></div><div style="font-size:0.7rem;color:#adb5bd;">31-90min</div></div>', unsafe_allow_html=True)
                with col_leg4:
                    st.markdown('<div style="text-align:center;"><div style="width:20px;height:20px;background:rgba(255,75,75,0.7);margin:0 auto;"></div><div style="font-size:0.7rem;color:#adb5bd;">91-180min</div></div>', unsafe_allow_html=True)
                with col_leg5:
                    st.markdown('<div style="text-align:center;"><div style="width:20px;height:20px;background:rgba(255,75,75,1);margin:0 auto;"></div><div style="font-size:0.7rem;color:#adb5bd;">180+min</div></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 2. GRÁFICO DE BURNDOWN
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### 📉 Burndown Semanal")
            
            meta_horas = st.session_state.meta_horas_semana
            meta_questoes = st.session_state.meta_questoes_semana
            
            df_burndown = criar_grafico_burndown(df, meta_horas, meta_questoes)
            
            if df_burndown is not None:
                # Criar gráfico de burndown duplo
                fig_burndown = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("Horas de Estudo", "Questões Resolvidas"),
                    vertical_spacing=0.15
                )
                
                # Gráfico de horas
                fig_burndown.add_trace(
                    go.Scatter(
                        x=df_burndown['data'],
                        y=df_burndown['horas_acumulado'],
                        name='Real',
                        line=dict(color='#FF4B4B', width=3),
                        mode='lines+markers'
                    ),
                    row=1, col=1
                )
                
                fig_burndown.add_trace(
                    go.Scatter(
                        x=df_burndown['data'],
                        y=df_burndown['meta_horas_ideal'],
                        name='Meta Ideal',
                        line=dict(color='#00FF00', width=2, dash='dash'),
                        mode='lines'
                    ),
                    row=1, col=1
                )
                
                # Gráfico de questões
                fig_burndown.add_trace(
                    go.Scatter(
                        x=df_burndown['data'],
                        y=df_burndown['questoes_acumulado'],
                        name='Real',
                        line=dict(color='#FF4B4B', width=3),
                        mode='lines+markers',
                        showlegend=False
                    ),
                    row=2, col=1
                )
                
                fig_burndown.add_trace(
                    go.Scatter(
                        x=df_burndown['data'],
                        y=df_burndown['meta_questoes_ideal'],
                        name='Meta Ideal',
                        line=dict(color='#00FF00', width=2, dash='dash'),
                        mode='lines',
                        showlegend=False
                    ),
                    row=2, col=1
                )
                
                fig_burndown.update_layout(
                    height=500,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#fff"),
                    margin=dict(t=50, b=20, l=40, r=20)
                )
                
                fig_burndown.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
                fig_burndown.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
                
                st.plotly_chart(fig_burndown, use_container_width=True)
                
                # Estatísticas da semana
                hoje = datetime.date.today()
                dia_semana = hoje.weekday()  # 0=segunda, 6=domingo
                
                if dia_semana < 7:  # Se ainda está na semana
                    progresso_ate_hoje_horas = df_burndown.loc[dia_semana, 'horas_acumulado']
                    meta_ate_hoje_horas = df_burndown.loc[dia_semana, 'meta_horas_ideal']
                    percentual_horas = (progresso_ate_hoje_horas / meta_ate_hoje_horas * 100) if meta_ate_hoje_horas > 0 else 0
                    
                    progresso_ate_hoje_questoes = df_burndown.loc[dia_semana, 'questoes_acumulado']
                    meta_ate_hoje_questoes = df_burndown.loc[dia_semana, 'meta_questoes_ideal']
                    percentual_questoes = (progresso_ate_hoje_questoes / meta_ate_hoje_questoes * 100) if meta_ate_hoje_questoes > 0 else 0
                    
                    col_stat1, col_stat2 = st.columns(2)
                    with col_stat1:
                        st.metric("Horas (até hoje)", f"{progresso_ate_hoje_horas:.1f}h", 
                                 f"{percentual_horas:.1f}% da meta")
                    with col_stat2:
                        st.metric("Questões (até hoje)", f"{int(progresso_ate_hoje_questoes)}", 
                                 f"{percentual_questoes:.1f}% da meta")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 3. PREVISÃO DE DESEMPENHO
            if data_prova_direta:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### 🔮 Previsão de Desempenho")
                
                # Calcular previsão
                previsao, limite_inferior, limite_superior = prever_desempenho(df, data_prova_direta)
                
                if previsao is not None:
                    # Data da prova
                    data_prova_dt = pd.to_datetime(data_prova_direta).date()
                    dias_ate_prova = (data_prova_dt - datetime.date.today()).days
                    
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.metric("Dias até a prova", dias_ate_prova)
                    
                    with col_info2:
                        # Classificação da previsão
                        if previsao >= 80:
                            status = "🟢 Excelente"
                            cor = "#00FF00"
                        elif previsao >= 70:
                            status = "🟡 Bom"
                            cor = "#FFD700"
                        elif previsao >= 60:
                            status = "🟠 Regular"
                            cor = "#FF8C00"
                        else:
                            status = "🔴 Precisa melhorar"
                            cor = "#FF4B4B"
                        
                        st.metric("Previsão", f"{previsao:.1f}%", status)
                    
                    with col_info3:
                        # Taxa atual para comparação
                        taxa_atual = df['taxa'].mean()
                        diferenca = previsao - taxa_atual
                        sinal = "+" if diferenca >= 0 else ""
                        st.metric("Taxa atual", f"{taxa_atual:.1f}%", f"{sinal}{diferenca:.1f}%")
                    
                    # Gráfico de previsão
                    fig_previsao = go.Figure()
                    
                    # Adicionar barra de previsão
                    fig_previsao.add_trace(go.Indicator(
                        mode="gauge+number",
                        value=previsao,
                        title={'text': "Previsão na Prova", 'font': {'color': '#fff', 'size': 16}},
                        number={'font': {'color': '#fff', 'size': 40}},
                        gauge={
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#fff"},
                            'bar': {'color': "#FF4B4B"},
                            'bgcolor': "rgba(0,0,0,0)",
                            'borderwidth': 2,
                            'bordercolor': "rgba(255,255,255,0.2)",
                            'steps': [
                                {'range': [0, 60], 'color': 'rgba(255, 75, 75, 0.1)'},
                                {'range': [60, 70], 'color': 'rgba(255, 140, 0, 0.1)'},
                                {'range': [70, 80], 'color': 'rgba(255, 215, 0, 0.1)'},
                                {'range': [80, 100], 'color': 'rgba(0, 255, 0, 0.1)'}
                            ]
                        }
                    ))
                    
                    fig_previsao.update_layout(
                        height=300,
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#fff"),
                        margin=dict(t=50, b=20, l=20, r=20)
                    )
                    
                    st.plotly_chart(fig_previsao, use_container_width=True)
                    
                    # Intervalo de confiança
                    if limite_inferior is not None and limite_superior is not None:
                        st.info(f"📊 **Intervalo de confiança 95%:** {limite_inferior:.1f}% a {limite_superior:.1f}%")
                    
                    # Recomendações baseadas na previsão
                    st.markdown("##### 💡 Recomendações:")
                    
                    if previsao >= 80:
                        st.success("""
                        **Excelente!** Você está no caminho certo:
                        - Mantenha o ritmo atual
                        - Foque em revisões de assuntos mais difíceis
                        - Faça simulados para testar tempo
                        """)
                    elif previsao >= 70:
                        st.warning("""
                        **Bom, mas pode melhorar:**
                        - Aumente em 10% o tempo de estudo diário
                        - Revise assuntos com taxa abaixo de 70%
                        - Pratique mais questões dos tópicos fracos
                        """)
                    elif previsao >= 60:
                        st.error("""
                        **Precisa de ajustes:**
                        - Aumente em 20% o tempo de estudo
                        - Identifique seus 3 piores assuntos
                        - Dedique 30% do tempo a eles
                        - Considere revisar material teórico
                        """)
                    else:
                        st.error("""
                        **Atenção urgente necessária:**
                        - Dobrar o tempo de estudo
                        - Revisar fundamentos teóricos
                        - Buscar material adicional
                        - Considerar ajuda de mentor/professor
                        """)
                
                else:
                    st.info("Não há dados suficientes para fazer uma previsão precisa. Continue estudando!")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        else:
            st.info("📚 Registre seus primeiros estudos para ver as visualizações avançadas!")
        
        # 4. GRÁFICOS PLOTLY (se houver dados) - mantendo os originais
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

    # --- NOVA ABA: PLANEJADOR ---
    elif menu == "Planejador":
        st.markdown('<h2 class="main-title">📋 Planejador Inteligente</h2>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("📚 Registre alguns estudos primeiro para habilitar o planejador inteligente.")
        else:
            # --- SEÇÃO 1: PLANEJAMENTO DIÁRIO INTELIGENTE ---
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("### 🎯 Sugestões para Hoje")
            
            # Calcular revisões pendentes
            pend = calcular_revisoes_pendentes(df, "Pendentes/Hoje", "Todas")
            
            if pend:
                # Ordenar por prioridade (dificuldade + atraso)
                pend_priorizados = sorted(pend, 
                                         key=lambda x: (
                                             0 if x['dificuldade'] == "🔴 Difícil" else 
                                             1 if x['dificuldade'] == "🟡 Médio" else 2,
                                             -x['atraso']
                                         ))
                
                # Pegar as 3 principais sugestões
                sugestoes = pend_priorizados[:3]
                
                for i, sug in enumerate(sugestoes):
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 15px; background: rgba(26, 28, 35, 0.5); border-radius: 8px; margin-bottom: 10px;">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                <span style="background: rgba(255, 75, 75, 0.2); color: #FF4B4B; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">
                                    {sug['dificuldade']}
                                </span>
                                <span style="color: #adb5bd; font-size: 0.8rem;">
                                    Pendente há {sug['atraso']} dia(s)
                                </span>
                            </div>
                            <h4 style="margin: 0; color: #fff; font-size: 1.1rem;">
                                📚 {sug['materia']}
                            </h4>
                            <p style="color: #adb5bd; font-size: 0.9rem; margin: 5px 0;">
                                {sug['assunto']} • <b>{sug['tipo']}</b>
                            </p>
                            <div style="color: #FF8E8E; font-size: 0.8rem;">
                                ⏱️ Recomendado: {tempo_recomendado_rev24h(sug['dificuldade'])[0]}min
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Botão para ver todas as revisões (CORREÇÃO: usando JavaScript para navegar)
                if st.button("Ver Todas as Revisões Pendentes", use_container_width=True):
                    # Usar JavaScript para mudar a seleção do menu
                    js = """
                    <script>
                    // Encontrar o elemento do radio button para "Revisões"
                    const radioButtons = document.querySelectorAll('input[type="radio"]');
                    for (let radio of radioButtons) {
                        if (radio.nextElementSibling && radio.nextElementSibling.textContent.includes('🔄 Revisões')) {
                            radio.click();
                            break;
                        }
                    }
                    </script>
                    """
                    st.components.v1.html(js, height=0)
                    # Atualizar estado e recarregar
                    st.session_state.menu_atual = "Revisões"
                    st.rerun()
            else:
                st.success("🎉 Nenhuma revisão pendente para hoje!")
                st.markdown("""
                **Sugestão:** Aproveite para:
                1. Avançar em novos conteúdos
                2. Revisar assuntos marcados como difíceis
                3. Fazer questões de provas anteriores
                """)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # --- SEÇÃO 2: DISTRIBUIÇÃO DE TEMPO ---
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("### ⏱️ Distribuição de Tempo Recomendada")
            
            # Calcular desempenho por matéria
            df_mat = df.groupby('materia').agg({
                'tempo': 'sum',
                'taxa': 'mean',
                'total': 'sum'
            }).reset_index()
            
            if not df_mat.empty:
                # Calcular peso baseado em desempenho (matérias com baixa taxa ganham mais peso)
                df_mat['peso'] = df_mat.apply(lambda row: 
                    max(0.1, 1 - (row['taxa'] / 100)) * (row['total'] / df_mat['total'].sum() if df_mat['total'].sum() > 0 else 1),
                    axis=1
                )
                
                # Normalizar pesos para soma = 100%
                peso_total = df_mat['peso'].sum()
                if peso_total > 0:
                    df_mat['percentual_tempo'] = (df_mat['peso'] / peso_total * 100).round(1)
                else:
                    df_mat['percentual_tempo'] = 100 / len(df_mat)
                
                # Ordenar por percentual (maior primeiro)
                df_mat = df_mat.sort_values('percentual_tempo', ascending=False)
                
                # Definir tempo total disponível (padrão: 4 horas)
                tempo_total_disponivel = st.slider(
                    "Tempo total disponível para estudo hoje (minutos):",
                    min_value=60,
                    max_value=480,
                    value=240,
                    step=30
                )
                
                # Calcular minutos para cada matéria
                df_mat['minutos_recomendados'] = (tempo_total_disponivel * df_mat['percentual_tempo'] / 100).round(0).astype(int)
                
                # Exibir distribuição
                for _, row in df_mat.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 1, 3, 1])
                    
                    with col1:
                        st.markdown(f"**{row['materia']}**")
                    
                    with col2:
                        st.markdown(f"<span style='color: #FF8E8E;'>{row['taxa']:.1f}%</span>", unsafe_allow_html=True)
                    
                    with col3:
                        progress = min(100, row['percentual_tempo'])
                        render_progress_bar(progress, height=8)
                    
                    with col4:
                        st.markdown(f"<span style='color: #fff; font-weight: 600;'>{row['minutos_recomendados']}min</span>", unsafe_allow_html=True)
                
                # Resumo
                st.divider()
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                with col_sum1:
                    st.metric("Matérias", len(df_mat))
                with col_sum2:
                    st.metric("Tempo Total", f"{tempo_total_disponivel}min")
                with col_sum3:
                    st.metric("Meta Diária", f"{sum(df_mat['minutos_recomendados'])}min")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # --- SEÇÃO 3: PLANEJAMENTO SEMANAL ---
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("### 🗓️ Planejamento Semanal")
            
            # Obter metas semanais
            meta_horas = st.session_state.meta_horas_semana
            meta_questoes = st.session_state.meta_questoes_semana
            
            # Calcular progresso da semana atual
            horas_semana, questoes_semana = calcular_estudos_semana(df)
            progresso_horas = (horas_semana / meta_horas * 100) if meta_horas > 0 else 0
            progresso_questoes = (questoes_semana / meta_questoes * 100) if meta_questoes > 0 else 0
            
            # Interface de planejamento
            st.markdown("#### Distribuição Semanal")
            
            # Dias da semana
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            horas_por_dia = meta_horas / 7
            
            # Criar layout de grid para planejamento
            cols = st.columns(7)
            
            for i, (col, dia) in enumerate(zip(cols, dias_semana)):
                with col:
                    st.markdown(f"**{dia}**")
                    
                    # Calcular se é hoje
                    hoje = datetime.date.today()
                    dia_atual = hoje.weekday()  # 0 = segunda
                    
                    if i == dia_atual:
                        st.markdown('<span style="color: #FF4B4B; font-size: 0.8rem;">HOJE</span>', unsafe_allow_html=True)
                    
                    # Mostrar meta diária
                    st.markdown(f"<span style='color: #adb5bd; font-size: 0.8rem;'>{horas_por_dia:.1f}h</span>", unsafe_allow_html=True)
                    
                    # Verificar se já estudou hoje
                    if i == dia_atual:
                        # Calcular horas estudadas hoje
                        hoje_str = hoje.strftime('%Y-%m-%d')
                        df_hoje = df[pd.to_datetime(df['data_estudo']).dt.strftime('%Y-%m-%d') == hoje_str]
                        horas_hoje = df_hoje['tempo'].sum() / 60 if not df_hoje.empty else 0
                        
                        if horas_hoje > 0:
                            progresso_dia = min(100, (horas_hoje / horas_por_dia) * 100)
                            render_progress_bar(progresso_dia, height=6)
                            st.markdown(f"<span style='color: #00FF00; font-size: 0.7rem;'>{horas_hoje:.1f}h</span>", unsafe_allow_html=True)
            
            # Resumo semanal
            st.divider()
            col_week1, col_week2, col_week3 = st.columns(3)
            
            with col_week1:
                st.metric("Horas (semana)", f"{horas_semana:.1f}h", f"{progresso_horas:.1f}%")
            
            with col_week2:
                st.metric("Questões (semana)", int(questoes_semana), f"{progresso_questoes:.1f}%")
            
            with col_week3:
                dias_restantes = 7 - datetime.date.today().weekday()
                st.metric("Dias restantes", dias_restantes)
            
            # Sugestão de ajuste
            if progresso_horas < 50:
                st.warning(f"⚠️ **Atenção:** Você está com {progresso_horas:.1f}% da meta de horas. Considere aumentar o tempo de estudo nos próximos dias.")
            elif progresso_horas > 90:
                st.success(f"✅ **Excelente!** Você já atingiu {progresso_horas:.1f}% da meta semanal.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # --- SEÇÃO 4: ANÁLISE DE CORRELAÇÃO ---
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("### 📈 Análise: Tempo vs Desempenho")
            
            # Preparar dados para análise
            if len(df) > 1:
                # Criar dataframe para análise
                df_corr = df.copy()
                df_corr['horas'] = df_corr['tempo'] / 60
                
                # Calcular correlação
                try:
                    correlacao = df_corr['horas'].corr(df_corr['taxa'])
                    
                    # Criar scatter plot
                    fig_corr = px.scatter(
                        df_corr, 
                        x='horas', 
                        y='taxa',
                        color='materia',
                        hover_data=['assunto', 'data_estudo'],
                        title=f"Correlação Tempo × Desempenho (r = {correlacao:.2f})",
                        labels={'horas': 'Tempo de Estudo (horas)', 'taxa': 'Taxa de Acerto (%)'}
                    )
                    
                    # Adicionar linha de tendência
                    if len(df_corr) > 2:
                        z = np.polyfit(df_corr['horas'], df_corr['taxa'], 1)
                        p = np.poly1d(z)
                        fig_corr.add_trace(
                            go.Scatter(
                                x=df_corr['horas'],
                                y=p(df_corr['horas']),
                                mode='lines',
                                name='Tendência',
                                line=dict(color='#FF4B4B', width=2, dash='dash')
                            )
                        )
                    
                    fig_corr.update_layout(
                        height=400,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#fff"),
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_corr, use_container_width=True)
                    
                    # Insights baseados na correlação
                    st.markdown("#### 💡 Insights:")
                    
                    if correlacao > 0.3:
                        st.success(f"""
                        **Relação positiva forte (r = {correlacao:.2f})**
                        - Seu desempenho tende a melhorar com mais tempo de estudo
                        - Continue investindo tempo nas matérias
                        - O esforço está sendo bem direcionado
                        """)
                    elif correlacao > 0.1:
                        st.info(f"""
                        **Relação positiva moderada (r = {correlacao:.2f})**
                        - Há uma tendência de melhora com mais tempo
                        - Considere revisar a qualidade do estudo, não apenas a quantidade
                        - Experimente técnicas de estudo ativo
                        """)
                    elif correlacao > -0.1:
                        st.warning(f"""
                        **Relação neutra (r = {correlacao:.2f})**
                        - O tempo de estudo não está correlacionado com desempenho
                        - Reavalie seus métodos de estudo
                        - Foque na qualidade e técnicas de revisão
                        """)
                    else:
                        st.error(f"""
                        **Relação negativa (r = {correlacao:.2f})**
                        - Mais tempo está associado a menor desempenho
                        - Possível cansaço ou estudo ineficiente
                        - Considere pausas e técnicas de Pomodoro
                        - Revise os assuntos estudados por muito tempo
                        """)
                    
                    # Estatísticas adicionais
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    
                    with col_stat1:
                        tempo_medio = df_corr['horas'].mean()
                        st.metric("Tempo médio por sessão", f"{tempo_medio:.1f}h")
                    
                    with col_stat2:
                        taxa_media = df_corr['taxa'].mean()
                        st.metric("Taxa média", f"{taxa_media:.1f}%")
                    
                    with col_stat3:
                        sessoes = len(df_corr)
                        st.metric("Sessões analisadas", sessoes)
                    
                except Exception as e:
                    st.info("Não foi possível calcular a correlação com os dados disponíveis.")
            else:
                st.info("📊 Registre mais estudos para habilitar a análise de correlação.")
            
            st.markdown('</div>', unsafe_allow_html=True)

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
                            html_metricas = f"""
                                <div style="text-align: right;">
                                    <div style="font-size: 0.8rem; color: #adb5bd; margin-bottom: 5px;">Desempenho</div>
                                    <div style="font-size: 1.3rem; font-weight: 700; color: #fff;">
                                        {int(row['acertos'])}/{int(row['total'])}
                                    </div>
                                    <div style="font-size: 0.75rem; color: #adb5bd;">
                                        ⏱️ {int(row['tempo']//60)}h{int(row['tempo']%60):02d}m
                                    </div>
                                </div>
                            """
                            st.markdown(html_metricas, unsafe_allow_html=True)
                        
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
        st.markdown("### 📚 Gerenciar Matérias e Assuntos")
        
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
            # Buscar matérias do banco de dados
            try:
                res_materias = supabase.table("editais_materias").select("id, materia, topicos").eq("concurso", missao).execute()
                registros_materias = res_materias.data
            except Exception as e:
                st.error(f"Erro ao buscar matérias: {e}")
                registros_materias = []
            
            # --- NOVA SEÇÃO: EXCLUSÃO EM MASSA ---
            if registros_materias:
                st.markdown("#### 🗑️ Exclusão em Massa de Matérias")
                st.warning("⚠️ Atenção: Esta ação excluirá permanentemente as matérias selecionadas e TODOS os registros de estudo relacionados!", icon="⚠️")
                
                # Criar lista de matérias com checkboxes
                materias_selecionadas = []
                
                for reg in registros_materias:
                    col_check, col_info = st.columns([0.1, 0.9])
                    with col_check:
                        selecionada = st.checkbox("", key=f"sel_{reg['id']}", help=f"Selecionar {reg['materia']} para exclusão")
                    with col_info:
                        st.write(f"**{reg['materia']}** - {len(reg['topicos'] if reg['topicos'] else [])} assuntos")
                    
                    if selecionada:
                        materias_selecionadas.append(reg)
                
                # Botão para excluir matérias selecionadas
                if materias_selecionadas:
                    st.error(f"⚠️ **{len(materias_selecionadas)} matéria(s) selecionada(s) para exclusão:**")
                    for mat in materias_selecionadas:
                        st.write(f"• {mat['materia']}")
                    
                    # Confirmação adicional
                    confirmacao = st.checkbox("✅ Confirmo que compreendo que esta ação é irreversível e excluirá todos os registros relacionados", 
                                             key="confirm_exclusao_massa")
                    
                    if confirmacao:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🚨 EXCLUIR MATÉRIAS SELECIONADAS", type="primary", use_container_width=True):
                                try:
                                    contador_exclusoes = 0
                                    contador_registros = 0
                                    
                                    for mat in materias_selecionadas:
                                        # Primeiro, contar registros de estudos associados a esta matéria
                                        try:
                                            res_contagem = supabase.table("registros_estudos")\
                                                .select("id", count="exact")\
                                                .eq("concurso", missao)\
                                                .eq("materia", mat['materia'])\
                                                .execute()
                                            
                                            # CORREÇÃO: Verificar se count existe e não é None
                                            if hasattr(res_contagem, 'count') and res_contagem.count is not None:
                                                contador_registros += res_contagem.count
                                        except Exception:
                                            # Se não conseguir contar, continuar mesmo assim
                                            pass
                                        
                                        # Excluir registros de estudos dessa matéria
                                        try:
                                            supabase.table("registros_estudos").delete()\
                                                .eq("concurso", missao)\
                                                .eq("materia", mat['materia'])\
                                                .execute()
                                        except Exception as e:
                                            st.warning(f"Aviso: Não foi possível excluir todos os registros de '{mat['materia']}': {e}")
                                        
                                        # Excluir a matéria da tabela editais_materias
                                        try:
                                            supabase.table("editais_materias").delete().eq("id", mat['id']).execute()
                                            contador_exclusoes += 1
                                        except Exception as e:
                                            st.error(f"Erro ao excluir matéria '{mat['materia']}': {e}")
                                    
                                    st.success(f"✅ **{contador_exclusoes} matéria(s) excluída(s) com sucesso!**")
                                    if contador_registros > 0:
                                        st.info(f"🗑️ **{contador_registros} registro(s) de estudo relacionados foram removidos.**")
                                    
                                    # Limpar cache e recarregar
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir matérias: {e}")
                        
                        with col_btn2:
                            if st.button("❌ Cancelar Exclusão", type="secondary", use_container_width=True):
                                st.rerun()
                
                st.divider()
            
            # Mostrar matérias atuais
            if registros_materias:
                st.markdown("#### ✏️ Editar Matérias Individuais")
                
                # Para cada matéria, criar um expander com opções de edição
                for reg in registros_materias:
                    materia = reg['materia']
                    topicos = reg['topicos'] if reg['topicos'] else []
                    id_registro = reg['id']
                    
                    with st.expander(f"📖 {materia} ({len(topicos)} assuntos)"):
                        # Mostrar assuntos atuais
                        st.markdown("**Assuntos atuais:**")
                        if topicos:
                            for i, topico in enumerate(topicos):
                                col1, col2 = st.columns([5, 1])
                                col1.write(f"• {topico}")
                                # Botão para remover assunto
                                if col2.button("🗑️", key=f"del_{id_registro}_{i}", help="Remover assunto", use_container_width=True):
                                    try:
                                        # Remover o tópico da lista
                                        novos_topicos = [t for t in topicos if t != topico]
                                        # Atualizar no banco
                                        supabase.table("editais_materias").update({"topicos": novos_topicos}).eq("id", id_registro).execute()
                                        st.success(f"✅ Assunto '{topico}' removido!")
                                        time.sleep(1)
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao remover assunto: {e}")
                        else:
                            st.info("Nenhum assunto cadastrado.")
                        
                        st.divider()
                        
                        # Formulário para adicionar novos assuntos
                        with st.form(f"form_novo_assunto_{id_registro}"):
                            st.markdown("**Adicionar novos assuntos (em massa)**")
                            
                            # Opções de entrada
                            metodo_entrada = st.selectbox(
                                "Como deseja adicionar os assuntos?",
                                ["Um por um", "Vários com separador", "Vários por linhas"],
                                key=f"metodo_{id_registro}"
                            )
                            
                            if metodo_entrada == "Um por um":
                                # Modo tradicional
                                novo_assunto = st.text_input("Nome do assunto", placeholder="Ex: Princípios fundamentais", key=f"novo_assunto_single_{id_registro}")
                                assuntos_para_adicionar = [novo_assunto] if novo_assunto else []
                                
                            elif metodo_entrada == "Vários com separador":
                                # Modo com separador
                                col_sep1, col_sep2 = st.columns([2, 1])
                                with col_sep1:
                                    texto_assuntos = st.text_area(
                                        "Digite os assuntos separados por:",
                                        placeholder="Ex: Princípios fundamentais; Organização do Estado; Direitos e garantias fundamentais",
                                        key=f"texto_assuntos_{id_registro}",
                                        height=100
                                    )
                                with col_sep2:
                                    separador = st.selectbox(
                                        "Separador",
                                        ["; (ponto e vírgula)", ", (vírgula)", ". (ponto)", "- (hífen)", "| (pipe)"],
                                        key=f"separador_{id_registro}"
                                    )
                                    # Mapear separador
                                    separador_map = {
                                        "; (ponto e vírgula)": ";",
                                        ", (vírgula)": ",",
                                        ". (ponto)": ".",
                                        "- (hífen)": "-",
                                        "| (pipe)": "|"
                                    }
                                    separador_char = separador_map[separador]
                                
                                if texto_assuntos:
                                    # Processar os assuntos
                                    assuntos_brutos = texto_assuntos.split(separador_char)
                                    assuntos_para_adicionar = [a.strip() for a in assuntos_brutos if a.strip()]
                                    
                                    # Mostrar prévia
                                    if assuntos_para_adicionar:
                                        st.info(f"**Prévia:** Serão adicionados {len(assuntos_para_adicionar)} assuntos")
                                        with st.expander("Ver assuntos"):
                                            for a in assuntos_para_adicionar:
                                                st.write(f"• {a}")
                            else:  # "Vários por linhas"
                                # Modo com múltiplas linhas
                                texto_assuntos = st.text_area(
                                    "Digite um assunto por linha:",
                                    placeholder="Princípios fundamentais\nOrganização do Estado\nDireitos e garantias fundamentais\n...",
                                    key=f"texto_assuntos_linhas_{id_registro}",
                                    height=120
                                )
                                
                                if texto_assuntos:
                                    # Processar os assuntos (uma por linha)
                                    assuntos_brutos = texto_assuntos.split("\n")
                                    assuntos_para_adicionar = [a.strip() for a in assuntos_brutos if a.strip()]
                                    
                                    # Mostrar prévia
                                    if assuntos_para_adicionar:
                                        st.info(f"**Prévia:** Serão adicionados {len(assuntos_para_adicionar)} assuntos")
                                        with st.expander("Ver assuntos"):
                                            for a in assuntos_para_adicionar:
                                                st.write(f"• {a}")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            if col_btn1.form_submit_button("➕ Adicionar Assuntos", use_container_width=True):
                                if assuntos_para_adicionar:
                                    try:
                                        # Buscar tópicos atuais
                                        if not topicos:
                                            topicos = []
                                        # Adicionar novos tópicos à lista (evitar duplicados)
                                        for assunto in assuntos_para_adicionar:
                                            if assunto not in topicos:
                                                topicos.append(assunto)
                                            else:
                                                st.warning(f"Assunto '{assunto}' já existe e foi ignorado.")
                                        
                                        # Atualizar no banco
                                        supabase.table("editais_materias").update({"topicos": topicos}).eq("id", id_registro).execute()
                                        st.success(f"✅ {len(assuntos_para_adicionar)} assunto(s) adicionado(s) com sucesso!")
                                        time.sleep(1)
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao adicionar assuntos: {e}")
                                else:
                                    st.warning("⚠️ Nenhum assunto válido para adicionar.")
                            
                            if col_btn2.form_submit_button("✏️ Renomear Matéria", use_container_width=True, type="secondary"):
                                # Abrir modal para renomear matéria
                                st.session_state[f"renomear_{id_registro}"] = True
                                st.rerun()
                        
                        # Modal para renomear matéria
                        if st.session_state.get(f"renomear_{id_registro}", False):
                            st.markdown('<div style="background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 8px; margin-top: 10px;">', unsafe_allow_html=True)
                            novo_nome = st.text_input("Novo nome da matéria", value=materia, key=f"novo_nome_{id_registro}")
                            
                            col_r1, col_r2 = st.columns(2)
                            if col_r1.button("💾 Salvar", key=f"salvar_nome_{id_registro}", use_container_width=True):
                                if novo_nome and novo_nome != materia:
                                    try:
                                        # Atualizar o nome da matéria
                                        supabase.table("editais_materias").update({"materia": novo_nome}).eq("id", id_registro).execute()
                                        
                                        # Atualizar também nos registros de estudo
                                        supabase.table("registros_estudos").update({"materia": novo_nome}).eq("concurso", missao).eq("materia", materia).execute()
                                        
                                        st.success(f"✅ Matéria renomeada para '{novo_nome}'!")
                                        time.sleep(1)
                                        st.session_state[f"renomear_{id_registro}"] = False
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao renomear matéria: {e}")
                            
                            if col_r2.button("❌ Cancelar", key=f"cancelar_nome_{id_registro}", use_container_width=True):
                                st.session_state[f"renomear_{id_registro}"] = False
                                st.rerun()
                            
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Nenhuma matéria cadastrada ainda.")
            
            # Formulário para adicionar nova matéria
            st.divider()
            st.markdown("#### ➕ Adicionar Nova Matéria")
            
            with st.form("form_nova_materia"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    nova_materia = st.text_input("Nome da Matéria", placeholder="Ex: Direito Constitucional")
                
                with col2:
                    st.write("")  # Espaçamento
                    st.write("")  # Espaçamento
                
                # Seção para assuntos iniciais
                st.markdown("**Assuntos iniciais (opcional):**")
                
                metodo_assuntos = st.selectbox(
                    "Como deseja adicionar os assuntos iniciais?",
                    ["Sem assuntos iniciais", "Um por um", "Vários com separador", "Vários por linhas"],
                    key="metodo_assuntos_nova"
                )
                
                assuntos_iniciais = []
                
                if metodo_assuntos == "Um por um":
                    assunto_inicial = st.text_input("Assunto inicial", placeholder="Ex: Princípios fundamentais", key="assunto_inicial_single")
                    if assunto_inicial:
                        assuntos_iniciais = [assunto_inicial]
                        
                elif metodo_assuntos == "Vários com separador":
                    col_sep1, col_sep2 = st.columns([2, 1])
                    with col_sep1:
                        texto_assuntos = st.text_area(
                            "Digite os assuntos separados por:",
                            placeholder="Ex: Princípios fundamentais; Organização do Estado; Direitos e garantias fundamentais",
                            key="texto_assuntos_nova",
                            height=100
                        )
                    with col_sep2:
                        separador = st.selectbox(
                            "Separador",
                            ["; (ponto e vírgula)", ", (vírgula)", ". (ponto)", "- (hífen)", "| (pipe)"],
                            key="separador_nova"
                        )
                        # Mapear separador
                        separador_map = {
                            "; (ponto e vírgula)": ";",
                            ", (vírgula)": ",",
                            ". (ponto)": ".",
                            "- (hífen)": "-",
                            "| (pipe)": "|"
                        }
                        separador_char = separador_map[separador]
                    
                    if texto_assuntos:
                        # Processar os assuntos
                        assuntos_brutos = texto_assuntos.split(separador_char)
                        assuntos_iniciais = [a.strip() for a in assuntos_brutos if a.strip()]
                        
                elif metodo_assuntos == "Vários por linhas":
                    texto_assuntos = st.text_area(
                        "Digite um assunto por linha:",
                        placeholder="Princípios fundamentais\nOrganização do Estado\nDireitos e garantias fundamentais\n...",
                        key="texto_assuntos_linhas_nova",
                        height=120
                    )
                    
                    if texto_assuntos:
                        # Processar os assuntos (uma por linha)
                        assuntos_brutos = texto_assuntos.split("\n")
                        assuntos_iniciais = [a.strip() for a in assuntos_brutos if a.strip()]
                
                # Mostrar prévia se houver assuntos
                if assuntos_iniciais and metodo_assuntos != "Sem assuntos iniciais":
                    st.info(f"**Prévia:** {len(assuntos_iniciais)} assunto(s) inicial(is)")
                    with st.expander("Ver assuntos"):
                        for a in assuntos_iniciais:
                            st.write(f"• {a}")
                
                # Botão de envio
                if st.form_submit_button("Adicionar Matéria", use_container_width=True):
                    if nova_materia:
                        try:
                            # Verificar se já existe
                            res_existente = supabase.table("editais_materias").select("*").eq("concurso", missao).eq("materia", nova_materia).execute()
                            if res_existente.data:
                                st.error(f"❌ A matéria '{nova_materia}' já existe!")
                            else:
                                # Buscar cargo atual
                                cargo_atual = dados.get('cargo', '')
                                # Se não houver assuntos definidos, usar "Geral" como padrão
                                if not assuntos_iniciais:
                                    assuntos_iniciais = ["Geral"]
                                
                                # Adicionar nova matéria
                                payload = {
                                    "concurso": missao,
                                    "cargo": cargo_atual,
                                    "materia": nova_materia,
                                    "topicos": assuntos_iniciais
                                }
                                # Se houver data_prova, incluir
                                if data_prova_direta:
                                    payload["data_prova"] = data_prova_direta
                                
                                supabase.table("editais_materias").insert(payload).execute()
                                st.success(f"✅ Matéria '{nova_materia}' adicionada com {len(assuntos_iniciais)} assunto(s) inicial(is)!")
                                time.sleep(1)
                                st.cache_data.clear()  # Limpar cache para atualizar a interface
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao adicionar matéria: {e}")
                    else:
                        st.warning("⚠️ Por favor, informe o nome da matéria.")
            
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
