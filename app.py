import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from supabase import create_client, Client

# ============================================================================
# 💎 CONFIGURAÇÕES DE ELITE & DESIGN SYSTEM
# ============================================================================
st.set_page_config(page_title="Monitor Pro | Inteligência de Revisão", layout="wide")

# Paleta SaaS Moderno
COLORS = {
    "primary": "#8B5CF6",    # Roxo Real
    "secondary": "#06B6D4",  # Ciano Digital
    "success": "#10B981",    # Esmeralda
    "danger": "#F43F5E",     # Rosa/Vermelho
    "bg": "#0B0B1E",         # Navy Profundo
    "card": "rgba(30, 30, 60, 0.4)",
    "text": "#F8FAFC"
}

# CSS Customizado para cara de "Site Profissional"
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp {{ background-color: {COLORS["bg"]}; font-family: 'Inter', sans-serif; }}
    
    .main-header {{
        background: linear-gradient(90deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 0.5rem;
    }}
    
    .modern-card {{
        background: {COLORS["card"]};
        backdrop-filter: blur(10px);
        border-radius: 24px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
    }}
    
    /* Remove padding padrão do Streamlit para colunas */
    [data-testid="column"] {{ padding: 0 0.5rem !important; }}
    
    /* Estilo para as métricas */
    .metric-value {{ font-size: 2rem; font-weight: 800; color: white; }}
    .metric-label {{ color: #94A3B8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 🛰️ CONEXÃO E DADOS (SUPABASE SECRETS)
# ============================================================================
@st.cache_resource
def get_supabase():
    url = st.secrets.get("SUPABASE_URL", "https://dyxtalcvjcprmhuktyfd.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "SUA_CHAVE_AQUI")
    return create_client(url, key)

# Dados Mockados para o Layout (Substituir por sua query real)
df_data = pd.DataFrame({
    'materia': ['Português', 'RLM', 'Const.', 'Adm.', 'Informática'],
    'precisao': [88, 65, 74, 92, 40],
    'relevancia': [10, 8, 9, 7, 5],
    'questoes': [320, 150, 450, 280, 90]
})

# ============================================================================
# 🛠️ COMPONENTES DE INTERFACE (A CARA DO SITE)
# ============================================================================
def render_header():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<h1 class="main-header">Monitor de Revisões Pro</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#94A3B8">Seu cockpit estratégico para derrotar a FGV.</p>', unsafe_allow_html=True)
    with col2:
        # Mini-estatística rápida no canto
        st.markdown(f"""
            <div style="text-align:right">
                <span class="metric-label">Streak Atual</span><br>
                <span class="metric-value" style="color:{COLORS['secondary']}">🔥 12 Dias</span>
            </div>
        """, unsafe_allow_html=True)

def draw_priority_matrix(df):
    fig = px.scatter(
        df, x="relevancia", y="precisao", size="questoes", color="precisao",
        hover_name="materia", text="materia",
        color_continuous_scale=[COLORS["danger"], COLORS["success"]],
        range_x=[0, 11], range_y=[0, 105]
    )
    fig.update_traces(textposition='top center', marker=dict(line=dict(width=2, color='white')))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color="#94A3B8", height=450, showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(title="Importância (FGV)", showgrid=False, zeroline=False),
        yaxis=dict(title="Sua Precisão (%)", showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    )
    return fig

# ============================================================================
# 🚀 RENDERIZAÇÃO DA PÁGINA
# ============================================================================
render_header()
st.markdown("---")

# Layout de Colunas Principais
col_left, col_right = st.columns([1.4, 1])

with col_left:
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("### 🏹 Matriz de Ataque")
    st.markdown("<small>Assuntos no canto inferior direito são sua prioridade total!</small>", unsafe_allow_html=True)
    st.plotly_chart(draw_priority_matrix(df_data), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("### 🛡️ Escudo de Conhecimento")
    fig_radar = go.Figure(data=go.Scatterpolar(
        r=df_data['precisao'], theta=df_data['materia'], fill='toself',
        fillcolor=f'rgba(139, 92, 246, 0.2)', line=dict(color=COLORS["primary"], width=3)
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.1)"),
                   bgcolor='rgba(0,0,0,0)'),
        paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=40, r=40, t=20, b=20), height=400
    )
    st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# Footer com Cards de Ação Rápida
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="modern-card" style="text-align:center; border-left: 5px solid {COLORS["success"]}">🚀 Próxima Missão: <b>Português</b></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="modern-card" style="text-align:center; border-left: 5px solid {COLORS["secondary"]}">📊 Precisão Geral: <b>78.4%</b></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="modern-card" style="text-align:center; border-left: 5px solid {COLORS["primary"]}">📅 Simulado em: <b>3 Dias</b></div>', unsafe_allow_html=True)
