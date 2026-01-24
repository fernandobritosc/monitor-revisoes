import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from supabase import create_client, Client

# ============================================================================
# 1. CONFIGURAÇÕES GERAIS E DESIGN SYSTEM
# ============================================================================
st.set_page_config(page_title="Monitor Pro | Inteligência de Revisão", layout="wide", initial_sidebar_state="expanded")

# Paleta SaaS Moderno
COLORS = {
    "primary": "#8B5CF6",    # Roxo Real
    "secondary": "#06B6D4",  # Ciano Digital
    "success": "#10B981",    # Esmeralda
    "danger": "#F43F5E",     # Rosa/Vermelho
    "warning": "#F59E0B",    # Laranja
    "bg": "#0B0B1E",         # Navy Profundo
    "card": "rgba(30, 30, 60, 0.4)",
    "text": "#F8FAFC"
}

# CSS Customizado (Glassmorphism + Layout Profissional)
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp {{ background-color: {COLORS["bg"]}; font-family: 'Inter', sans-serif; }}
    
    /* Header com Gradiente */
    .main-header {{
        background: linear-gradient(90deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 0.5rem;
    }}
    
    /* Cartões de Vidro (Glassmorphism) */
    .modern-card {{
        background: {COLORS["card"]};
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        margin-bottom: 1rem;
    }}
    
    /* Métricas */
    .metric-value {{ font-size: 1.8rem; font-weight: 800; color: white; }}
    .metric-label {{ color: #94A3B8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }}
    
    /* Remover barra de ferramentas do Plotly para visual limpo */
    .js-plotly-plot .plotly .modebar {{ display: none !important; }}
    
    /* Ajuste de padding padrão do Streamlit */
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; }}
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. CONEXÃO SUPABASE (COM FALLBACK)
# ============================================================================
@st.cache_resource
def init_connection():
    try:
        # Tenta pegar dos Secrets do Streamlit Cloud
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        # Se falhar (rodando local sem secrets), retorna None
        return None

supabase = init_connection()

# ============================================================================
# 3. GERADORES DE GRÁFICOS (PLOTLY)
# ============================================================================

def plot_priority_matrix(df):
    """Matriz de Prioridade: Relevância vs Precisão"""
    fig = px.scatter(
        df, x="relevancia", y="precisao", size="questoes", color="precisao",
        hover_name="materia", text="materia",
        color_continuous_scale=[COLORS["danger"], COLORS["warning"], COLORS["success"]],
        range_x=[0, 11], range_y=[0, 110]
    )
    fig.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='white')))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color="#94A3B8", height=350, showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(title="Importância (FGV)", showgrid=False, zeroline=False),
        yaxis=dict(title="Precisão (%)", showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    )
    return fig

def plot_radar_chart(df):
    """Radar de Equilíbrio"""
    fig = go.Figure(data=go.Scatterpolar(
        r=df['precisao'], theta=df['materia'], fill='toself',
        fillcolor='rgba(139, 92, 246, 0.2)', 
        line=dict(color=COLORS["primary"], width=2)
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.1)"),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=40, r=40, t=20, b=20), height=350,
        showlegend=False
    )
    return fig

def plot_treemap(df):
    """Treemap: Tamanho = Relevância, Cor = Precisão"""
    fig = px.treemap(
        df, path=['materia'], values='relevancia', color='precisao',
        color_continuous_scale=[COLORS["danger"], COLORS["warning"], COLORS["success"]],
        range_color=[0, 100]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )
    # Ajuste visual das bordas do Treemap
    fig.update_traces(marker_line_width=1, marker_line_color=COLORS["bg"])
    return fig

# ============================================================================
# 4. INTERFACE PRINCIPAL
# ============================================================================

# --- SIDEBAR DE NAVEGAÇÃO ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=60)
    st.markdown("### Monitor Pro")
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Registrar", "Configurações"],
        icons=["speedometer2", "pencil-square", "gear"],
        default_index=0,
        styles={
            "container": {"background-color": "transparent"},
            "nav-link-selected": {"background-color": COLORS["primary"]},
            "nav-link": {"--hover-color": "rgba(139, 92, 246, 0.2)"}
        }
    )

# --- DADOS (MOCKUP PARA EVITAR ERROS SE O BANCO ESTIVER VAZIO) ---
# Aqui simulamos o banco de dados. Quando conectar o Supabase, substituiremos isso.
df_data = pd.DataFrame({
    'materia': ['Português', 'RLM', 'Dir. Const.', 'Dir. Adm.', 'Informática', 'AFO'],
    'precisao': [88, 62, 74, 95, 40, 55],
    'relevancia': [10, 8, 9, 7, 5, 6],
    'questoes': [320, 150, 450, 280, 90, 110],
    'momentum': ['up', 'down', 'stable', 'up', 'down', 'up'], # up, down, stable
    'delta': ['+5%', '-2%', '0%', '+8%', '-10%', '+3%']
})

# --- LÓGICA DAS PÁGINAS ---

if selected == "Dashboard":
    # 1. CABEÇALHO DO COCKPIT
    st.markdown('<h1 class="main-header">Cockpit de Aprovação</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{COLORS["text"]}; margin-bottom: 2rem;">Análise estratégica para dominar a banca FGV.</p>', unsafe_allow_html=True)
    
    # 2. LINHA DE KPIs (INDICADORES)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="modern-card"><span class="metric-label">Precisão Global</span><br><span class="metric-value" style="color:{COLORS["primary"]}">78%</span></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="modern-card"><span class="metric-label">Questões Hoje</span><br><span class="metric-value" style="color:{COLORS["secondary"]}">45</span></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="modern-card"><span class="metric-label">Streak</span><br><span class="metric-value" style="color:{COLORS["success"]}">🔥 12 Dias</span></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="modern-card"><span class="metric-label">Próx. Simulado</span><br><span class="metric-value" style="color:{COLORS["warning"]}">3 Dias</span></div>', unsafe_allow_html=True)

    # 3. BANNER DE RECOMENDAÇÃO (IA INSIGHT)
    st.info("🤖 **IA Insight:** Notei uma queda de Momentum em **RLM**. Sugiro 20 questões de Lógica Proposicional hoje para recuperar.")

    # 4. GRÁFICOS DE ELITE (LINHA SUPERIOR)
    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Matriz de Ataque (Prioridade)")
        st.plotly_chart(plot_priority_matrix(df_data), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c2:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("### 🛡️ Escudo de Competência")
        st.plotly_chart(plot_radar_chart(df_data), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. TREEMAP E MOMENTUM (LINHA INFERIOR - NOVIDADE)
    st.markdown("### 🧠 Mapa de Ocupação & Momentum")
    t1, t2 = st.columns([2, 1])
    
    with t1:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("#### 📐 Peso na Prova vs. Seu Desempenho")
        st.caption("Tamanho do bloco = Importância na Prova. Cor = Sua Precisão (Verde é bom).")
        st.plotly_chart(plot_treemap(df_data), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t2:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("#### ⚡ Momentum (7 Dias)")
        for index, row in df_data.iterrows():
            # Lógica de cores e setas para o Momentum
            if row['momentum'] == 'up':
                cor, seta = COLORS["success"], "▲"
            elif row['momentum'] == 'down':
                cor, seta = COLORS["danger"], "▼"
            else:
                cor, seta = COLORS["text"], "●"
                
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <span style="color: white; font-weight: 500;">{row['materia']}</span>
                    <span style="color: {cor}; font-weight: bold;">{seta} {row['delta']}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif selected == "Registrar":
    st.markdown('<div class="modern-card"><h3>📝 Registrar Sessão</h3><p>Funcionalidade de registro aqui...</p></div>', unsafe_allow_html=True)

elif selected == "Configurações":
    st.markdown('<div class="modern-card"><h3>⚙️ Configurações</h3><p>Ajuste suas metas e API keys.</p></div>', unsafe_allow_html=True)
