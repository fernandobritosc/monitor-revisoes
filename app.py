import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu
from fpdf import FPDF
import io
from supabase import create_client, Client

# ============================================================================
# 🎨 CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM
# ============================================================================
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

COLORS = {
    "primary": "#8B5CF6", "secondary": "#06B6D4", "accent": "#EC4899",
    "success": "#10B981", "warning": "#F59E0B", "danger": "#EF4444",
    "bg_dark": "#0F0F23", "text_primary": "#FFFFFF", "text_secondary": "#94A3B8"
}

st.markdown(f"""
    <style>
    .main {{ background-color: {COLORS["bg_dark"]}; color: white; }}
    .stApp {{ background-color: {COLORS["bg_dark"]}; }}
    .modern-card {{
        background: rgba(255, 255, 255, 0.03);
        padding: 1.5rem;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1rem;
        transition: 0.3s;
    }}
    .modern-card:hover {{ border: 1px solid {COLORS["primary"]}; background: rgba(139, 92, 246, 0.05); }}
    h1, h2, h3 {{ color: white !important; font-family: 'Inter', sans-serif; }}
    .stMetric {{ background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 🔐 CONEXÃO SEGURA (SUPABASE VIA SECRETS)
# ============================================================================
def init_supabase():
    try:
        # Tenta buscar dos Secrets (Nuvem) ou volta para Hardcoded se falhar (Local)
        url = st.secrets.get("SUPABASE_URL", "https://dyxtalcvjcprmhuktyfd.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "sb_secret_uEyhPGa8T-JUw0X1m5JyOA_PygMIKW3")
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()

# ============================================================================
# 📊 FUNÇÕES DE UI - DASHBOARD PROFISSIONAL
# ============================================================================
def render_circular_progress(percentage, label, value, color_start, color_end):
    """Renderiza anéis de progresso com SVG para não quebrar o layout"""
    st.markdown(f"""
        <div style="text-align: center; background: rgba(255,255,255,0.03); padding: 20px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05);">
            <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8" />
                <circle cx="50" cy="50" r="45" fill="none" stroke="{color_start}" stroke-width="8" 
                    stroke-dasharray="{2.82 * percentage}, 282" stroke-linecap="round" transform="rotate(-90 50 50)" />
                <text x="50" y="55" text-anchor="middle" fill="white" font-size="16px" font-weight="bold">{value}</text>
            </svg>
            <p style="margin-top:10px; color:{COLORS['text_secondary']}; font-size:14px;">{label}</p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 🚀 MENU E NAVEGAÇÃO
# ============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=80)
    st.title("Revisões Pro")
    selected = option_menu(
        menu_title=None,
        options=["Home", "Dashboard", "Simulados", "Configurações"],
        icons=["house", "graph-up", "clipboard-check", "gear"],
        default_index=0,
        styles={"container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"5px", "--hover-color": "rgba(139, 92, 246, 0.2)"},
                "nav-link-selected": {"background-color": COLORS["primary"]}}
    )

# Simulando dados para visualização (Aqui entraria sua lógica de fetch do Supabase)
df_mock = pd.DataFrame({
    'materia': ['Português', 'RLM', 'Direito Const.', 'Direito Adm.', 'Informática'],
    'precisao': [85, 62, 78, 90, 45],
    'relevancia': [10, 8, 9, 7, 6],
    'questoes': [150, 80, 200, 120, 50]
})

# ============================================================================
# 🏠 ÁREA PRINCIPAL
# ============================================================================
if selected == "Dashboard":
    st.markdown("## 📊 Inteligência de Dados")
    
    # Linha 1: Métricas de Impacto
    m1, m2, m3 = st.columns(3)
    with m1: render_circular_progress(df_mock['precisao'].mean(), "Precisão Geral", f"{df_mock['precisao'].mean():.0f}%", COLORS["primary"], COLORS["secondary"])
    with m2: render_circular_progress(75, "Meta", "75%", COLORS["success"], "#059669")
    with m3: render_circular_progress(100, "Questões", f"{df_mock['questoes'].sum()}", COLORS["accent"], "#BE185D")

    st.markdown("<br>", unsafe_allow_html=True)

    # Linha 2: Gráficos de Alta Performance
    c1, c2 = st.columns([1.2, 1])
    
    with c1:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.subheader("🎯 Matriz de Prioridade (Relevância vs Precisão)")
        fig_matriz = px.scatter(
            df_mock, x="relevancia", y="precisao", size="questoes", color="precisao",
            hover_name="materia", text="materia",
            color_continuous_scale="Viridis", range_x=[0,11], range_y=[0,110]
        )
        fig_matriz.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                 font_color="white", margin=dict(l=0, r=0, t=30, b=0), height=350)
        st.plotly_chart(fig_matriz, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.subheader("🛡️ Equilíbrio de Matérias")
        fig_radar = go.Figure(data=go.Scatterpolar(r=df_mock['precisao'], theta=df_mock['materia'], fill='toself', line_color=COLORS["secondary"]))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.1)"),
                                           bgcolor='rgba(0,0,0,0)'),
                                paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=40, r=40, t=40, b=40), height=350)
        st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("Selecione 'Dashboard' para ver a nova interface de elite.")
