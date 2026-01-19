import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu
from notion_client import Client # Necessário para ler o seu Notion

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# --- CONFIGURAÇÃO DO NOTION (ADICIONADO) ---
NOTION_TOKEN = "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"
DATABASE_ID = "2ec82bc022d780a592dcea3616f520c0"
notion = Client(auth=NOTION_TOKEN)

def get_notion_errors_count():
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={"property": "Revisado", "checkbox": {"equals": False}}
        )
        return len(response.get("results", []))
    except:
        return 0

# Aplicar estilos base
apply_styles()

# --- INICIALIZAÇÃO DE ESTADO (PROTEÇÃO CONTRA TRAVAMENTOS) ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None # Evita o erro de AttributeError
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco"

# [MANTIDO TODO O SEU CSS CUSTOMIZADO AQUI...]
st.markdown("""<style>...</style>""", unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES ---
def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    return (int(numeros[:-2]) * 60) + int(numeros[-2:])

def render_metric_card(label, value, icon="📊"):
    st.markdown(f"""
        <div class="modern-card" style="text-align: center; padding: 15px;">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #fff;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE NAVEGAÇÃO ---
# Agora usa st.session_state.get() para maior segurança
if st.session_state.get('missao_ativa') is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    # [LOGICA DE MISSÕES ATIVAS...]
else:
    missao = st.session_state.missao_ativa
    # [CARREGAMENTO DE DADOS DO SUPABASE...]

    # --- ABA: DASHBOARD (ATUALIZADA) ---
    if menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        # Busca em tempo real do Notion
        erros_notion = get_notion_errors_count()
        
        if df.empty:
            st.info("Ainda não há dados suficientes.")
        else:
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q>0 else 0)
            
            # Adicionado a 4ª coluna para o Notion
            m1, m2, m3, m4 = st.columns(4)
            with m1: render_metric_card("Total de Questões", int(t_q), "📝")
            with m2: render_metric_card("Precisão Média", f"{precisao:.1f}%", "🎯")
            with m3: render_metric_card("Erros Notion", erros_notion, "🔥")
            with m4: render_metric_card("Horas Estudadas", f"{df['tempo'].sum()/60:.1f}h", "⏱️")
            
            # [MANTIDO TODOS OS SEUS GRÁFICOS E DETALHAMENTO ABAIXO...]
