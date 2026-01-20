import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

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

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

# Importações dos seus módulos (ajuste conforme necessário)
try:
    from database import supabase
    from logic import get_editais, excluir_concurso_completo
    from styles import apply_styles
    apply_styles()
except:
    st.warning("Algumas importações podem estar faltando. Verifique os módulos.")

# Inicializar estados do Pomodoro
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco" # Foco ou Pausa

# CSS Customizado para Layout Moderno + Painel de Desempenho
st.markdown("""
    <style>
    /* Importar Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
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

    /* Pomodoro Timer Display */
    .timer-display {
        font-size: 5rem;
        font-weight: 800;
        color: #fff;
        text-align: center;
        margin: 20px 0;
        font-variant-numeric: tabular-nums;
        text-shadow: 0 0 20px rgba(255, 75, 75, 0.3);
    }
    
    /* ===== ESTILOS DO PAINEL DE DESEMPENHO ===== */
    .summary-card {
        background: rgba(15, 52, 96, 0.8);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(0, 173, 181, 0.3);
        height: 100%;
        transition: all 0.3s ease;
    }
    .summary-card:hover {
        border: 1px solid rgba(0, 173, 181, 0.6);
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 173, 181, 0.2);
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .legend-color {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        margin-right: 10px;
    }
    
    /* Cards para melhor/pior disciplina */
    .highlight-card {
        background: rgba(0, 173, 181, 0.1);
        padding: 1rem;
        border-radius: 10px;
        margin-top: 1rem;
        border-left: 4px solid;
    }
    .highlight-good {
        border-left-color: #00ff00;
    }
    .highlight-bad {
        border-left-color: #ff4b4b;
    }
    
    /* Ajustes para tabelas */
    .dataframe th {
        background-color: #0f3460 !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        text-align: center !important;
    }
    .dataframe td {
        text-align: center !important;
    }
    
    /* Esconder elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES ---
def render_metric_card(label, value, icon="📊"):
    """Renderiza um cartão de métrica."""
    st.markdown(f"""
        <div style="text-align: center; padding: 15px; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; background: rgba(15, 52, 96, 0.5);">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

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
        return f"{horas}h {minutos_rest}m"
    return f"{minutos_rest}m"

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
        elif row.get('rev_24h', True):
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

# --- FUNÇÃO DO PAINEL DE DESEMPENHO AVANÇADO ---
def render_painel_desempenho(df, missao):
    """Renderiza o painel de desempenho avançado."""
    if df.empty:
        st.info("📚 Ainda não há dados para exibir o painel.")
        return
    
    # --- CÁLCULO DOS DADOS ---
    # Agrupa por disciplina
    df_agg = df.groupby('materia').agg({
        'tempo': 'sum',
        'acertos': 'sum',
        'total': 'sum',
        'taxa': 'mean'
    }).reset_index()
    
    # Calcula totais
    total_corretas = int(df['acertos'].sum())
    total_erradas = int(df['total'].sum() - total_corretas)
    total_percentual = df['taxa'].mean() if not df['taxa'].empty else 0
    total_tempo = int(df['tempo'].sum())
    
    # Determina melhor e pior disciplina
    if not df_agg.empty:
        melhor_idx = df_agg['taxa'].idxmax()
        pior_idx = df_agg['taxa'].idxmin()
        melhor_disciplina = df_agg.loc[melhor_idx, 'materia']
        melhor_taxa = df_agg.loc[melhor_idx, 'taxa']
        pior_disciplina = df_agg.loc[pior_idx, 'materia']
        pior_taxa = df_agg.loc[pior_idx, 'taxa']
    
    # --- LAYOUT PRINCIPAL ---
    st.markdown('<h2 class="main-title">📊 Dashboard de Performance Avançado</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Análise detalhada do seu desempenho por disciplina</p>', unsafe_allow_html=True)
    
    # --- CARDS DE RESUMO ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="summary-card">
                <div style="font-size: 2.5rem; font-weight: 700; color: #00ff00;">{total_corretas}</div>
                <div style="color: #adb5bd; font-size: 0.9rem;">Total de Acertos</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="summary-card">
                <div style="font-size: 2.5rem; font-weight: 700; color: #ff4b4b;">{total_erradas}</div>
                <div style="color: #adb5bd; font-size: 0.9rem;">Total de Erros</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Determinar cor do percentual médio
        if total_percentual >= 70:
            percent_color = "#00ff00"
        elif total_percentual >= 50:
            percent_color = "#ffd700"
        else:
            percent_color = "#ff4b4b"
            
        st.markdown(f"""
            <div class="summary-card">
                <div style="font-size: 2.5rem; font-weight: 700; color: {percent_color};">{total_percentual:.1f}%</div>
                <div style="color: #adb5bd; font-size: 0.9rem;">Média Geral</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        horas = total_tempo // 60
        minutos = total_tempo % 60
        st.markdown(f"""
            <div class="summary-card">
                <div style="font-size: 2.5rem; font-weight: 700; color: #00adb5;">{horas}h {minutos}m</div>
                <div style="color: #adb5bd; font-size: 0.9rem;">Tempo Total</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- TABELA PRINCIPAL E GRÁFICOS ---
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        # Tabela de desempenho
        st.markdown("### 📋 Desempenho por Disciplina")
        
        # Preparar dados para tabela
        df_display = df_agg.copy()
        df_display['tempo_formatado'] = df_display['tempo'].apply(lambda x: f"{x//60}h {x%60}m")
        df_display['taxa_formatada'] = df_display['taxa'].apply(lambda x: f"{x:.1f}%")
        df_display['neutras'] = 0  # Placeholder se não tiver coluna
        
        # Reordenar colunas
        df_display = df_display[['materia', 'tempo_formatado', 'acertos', 'total', 'taxa_formatada']]
        
        # Exibir tabela
        st.dataframe(
            df_display,
            column_config={
                "materia": "Disciplina",
                "tempo_formatado": "Tempo",
                "acertos": st.column_config.NumberColumn("✓", format="%d"),
                "total": st.column_config.NumberColumn("Total", format="%d"),
                "taxa_formatada": "%"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Gráfico de barras
        st.markdown("### 📈 Percentual de Acerto por Disciplina")
        
        fig = go.Figure()
        
        for _, row in df_agg.iterrows():
            color = "#00ff00" if row['taxa'] >= 70 else "#ffd700" if row['taxa'] >= 50 else "#ff4b4b"
            
            fig.add_trace(go.Bar(
                x=[row['materia']],
                y=[row['taxa']],
                name=row['materia'],
                marker_color=color,
                text=[f"{row['taxa']:.1f}%"],
                textposition='auto',
                hovertemplate=f"<b>{row['materia']}</b><br>Percentual: {row['taxa']:.1f}%<br>Acertos: {row['acertos']}/{row['total']}<br>Tempo: {row['tempo']//60}h{row['tempo']%60}m<extra></extra>"
            ))
        
        fig.update_layout(
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            xaxis_title="Disciplinas",
            yaxis_title="Percentual (%)",
            yaxis_range=[0, 100],
            showlegend=False,
            bargap=0.3,
            margin=dict(t=20, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_side:
        # Destaques
        st.markdown("### 🏆 Destaques")
        
        if not df_agg.empty:
            # Melhor disciplina
            st.markdown(f"""
                <div class="highlight-card highlight-good">
                    <div style="font-weight: 600; color: white; font-size: 1rem;">🎖️ Melhor Desempenho</div>
                    <div style="color: #adb5bd; font-size: 0.9rem; margin-top: 5px;">{melhor_disciplina}</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #00ff00; margin-top: 10px;">{melhor_taxa:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Pior disciplina
            st.markdown(f"""
                <div class="highlight-card highlight-bad">
                    <div style="font-weight: 600; color: white; font-size: 1rem;">📚 Precisa de Revisão</div>
                    <div style="color: #adb5bd; font-size: 0.9rem; margin-top: 5px;">{pior_disciplina}</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #ff4b4b; margin-top: 10px;">{pior_taxa:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Legenda
        st.markdown("### 📝 Legenda")
        
        col_leg1, col_leg2 = st.columns(2)
        
        with col_leg1:
            st.markdown("""
                <div style="margin-top: 10px;">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #00ff00;"></div>
                        <span style="color: white;">✓ Acertos</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ffd700;"></div>
                        <span style="color: white;">🟡 Médio</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with col_leg2:
            st.markdown("""
                <div style="margin-top: 10px;">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ff4b4b;"></div>
                        <span style="color: white;">X Erros</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: linear-gradient(90deg, #00adb5, #0097a7);"></div>
                        <span style="color: white;">⏱️ Tempo</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # Distribuição por dificuldade
        st.markdown("### 🎯 Distribuição por Dificuldade")
        
        if 'dificuldade' in df.columns:
            df_dificuldade = df['dificuldade'].value_counts().reset_index()
            df_dificuldade.columns = ['Dificuldade', 'Contagem']
            
            fig_pie = px.pie(
                df_dificuldade, 
                values='Contagem', 
                names='Dificuldade',
                color='Dificuldade',
                color_discrete_map={
                    '🟢 Fácil': '#00ff00',
                    '🟡 Médio': '#ffd700',
                    '🔴 Difícil': '#ff4b4b'
                },
                hole=0.4
            )
            
            fig_pie.update_layout(
                height=250,
                margin=dict(t=0, b=0, l=0, r=0),
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#fff", size=12)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ℹ️ Adicione classificação de dificuldade nos registros.")
    
    st.divider()
    
    # --- EVOLUÇÃO TEMPORAL ---
    st.markdown("### 📈 Evolução da Precisão")
    
    if not df.empty:
        try:
            df['data_estudo'] = pd.to_datetime(df['data_estudo'])
            df_evo = df.groupby('data_estudo')['taxa'].mean().reset_index()
            
            fig_line = px.line(
                df_evo, 
                x='data_estudo', 
                y='taxa', 
                markers=True,
                line_shape='spline'
            )
            
            fig_line.update_traces(
                line_color='#FF4B4B', 
                line_width=3,
                marker=dict(size=8, color='#FF8E8E')
            )
            
            fig_line.update_layout(
                height=300,
                margin=dict(t=20, b=0, l=0, r=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#fff"),
                xaxis_title=None,
                yaxis_title="Taxa %",
                yaxis_range=[0, 100]
            )
            
            st.plotly_chart(fig_line, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar gráfico de evolução: {e}")
    
    # --- DETALHAMENTO POR ASSUNTO ---
    st.markdown("### 📚 Detalhamento por Assunto")
    
    materia_selecionada = st.selectbox(
        "Selecione uma disciplina para detalhar:",
        options=["Todas"] + list(df['materia'].unique()),
        key="detalhe_materia"
    )
    
    if materia_selecionada != "Todas":
        df_filtrado = df[df['materia'] == materia_selecionada]
        
        if not df_filtrado.empty:
            df_assuntos = df_filtrado.groupby('assunto').agg({
                'acertos': 'sum',
                'total': 'sum',
                'taxa': 'mean'
            }).reset_index().sort_values('taxa', ascending=False)
            
            for _, assunto in df_assuntos.iterrows():
                with st.expander(f"{assunto['assunto']} — {assunto['taxa']:.1f}%", expanded=False):
                    col_a1, col_a2, col_a3 = st.columns(3)
                    
                    col_a1.metric("Acertos", int(assunto['acertos']))
                    col_a2.metric("Total", int(assunto['total']))
                    col_a3.metric("Taxa", f"{assunto['taxa']:.1f}%")
                    
                    st.markdown(f"""
                        <div class="modern-progress-container" style="margin-top: 10px;">
                            <div class="modern-progress-fill" style="width: {assunto['taxa']}%;"></div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Não há registros para {materia_selecionada}.")
    else:
        st.info("Selecione uma disciplina para ver o detalhamento por assunto.")

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
        st.markdown(f"<p style='color:#adb5bd; font-size:0.8rem; margin-bottom:20px;'>{dados.get('cargo', '')}</p>", unsafe_allow_html=True)
        
        if st.button("← Voltar à Central", use_container_width=True): 
            st.session_state.missao_ativa = None
            st.rerun()
        
        st.write("")
        menu = option_menu(None, ["Home", "Revisões", "Registrar", "Foco", "Dashboard", "Histórico", "Configurar"], 
                           icons=["house", "arrow-repeat", "pencil-square", "clock", "grid", "list", "gear"], 
                           default_index=0,
                           styles={
                               "container": {"padding": "0!important", "background-color": "transparent"},
                               "icon": {"color": "#FF4B4B", "font-size": "18px"}, 
                               "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "rgba(255,75,75,0.1)"},
                               "nav-link-selected": {"background-color": "rgba(255,75,75,0.2)", "border-left": "3px solid #FF4B4B"}
                           })

    # --- ABA: HOME (PAINEL GERAL) ---
    if menu == "Home":
        st.markdown('<h2 class="main-title">🏠 Home — Painel Geral</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Visão rápida: tempo, precisão, streak e contagem regressiva</p>', unsafe_allow_html=True)

        if df.empty:
            st.info("Ainda não há registros. Faça seu primeiro estudo para preencher o painel.")
        else:
            # Métricas principais
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df['tempo'].sum())
            streak = calcular_streak(df)

            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                render_metric_card("Tempo Total", formatar_minutos(minutos_totais), "⏱️")
            with c2:
                render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
            with c3:
                render_metric_card("Streak", f"{streak} 🔥", "🔥")
            with c4:
                # Countdown da prova - AGORA USA A DATA DA TABELA CORRETA
                dias_restantes = None
                if data_prova_direta:
                    try:
                        dt_prova = pd.to_datetime(data_prova_direta).date()
                        dias_restantes = (dt_prova - datetime.date.today()).days
                    except Exception:
                        dias_restantes = None
                
                if dias_restantes is not None:
                    render_metric_card("Dias para a Prova", f"{dias_restantes} dias", "📅")
                else:
                    render_metric_card("Dias para a Prova", "—", "📅")

            st.divider()

            # Status por disciplina (barras de progresso)
            st.markdown('<h3 style="margin-top:1rem; color:#fff;">Status por Disciplina</h3>', unsafe_allow_html=True)
            df_mat = df.groupby('materia').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean', 'tempo': 'sum'}).reset_index()
            for _, row in df_mat.iterrows():
                pct = float(row['taxa']) if not pd.isna(row['taxa']) else 0
                tempo_mat = int(row['tempo'])
                badge = get_badge_cor(pct)
                st.markdown(f"<div class='modern-card' style='padding:12px;'>", unsafe_allow_html=True)
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center;'><strong style='color:#fff;'>{row['materia']}</strong><span class='{badge}' style='font-size:0.85rem;padding:4px 8px;border-radius:8px;'>{pct:.1f}%</span></div>", unsafe_allow_html=True)
                    st.markdown(f"""
                        <div class="modern-progress-container" style="margin-top:8px;">
                            <div class="modern-progress-fill" style="width: {pct}%;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div style='text-align:right; color:#adb5bd;'>{formatar_minutos(tempo_mat)}</div>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: REVISÕES ---
    elif menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            filtro_rev = st.segmented_control("Visualizar:", ["Pendentes/Hoje", "Todas (incluindo futuras)"], default="Pendentes/Hoje")
        with c2:
            filtro_dif = st.segmented_control("Dificuldade:", ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"], default="Todas")
    
        # Usar função com cache para melhor performance
        pend = calcular_revisoes_pendentes(df, filtro_rev, filtro_dif)
        
        if not pend: 
            st.success("✨ Tudo em dia! Aproveite para avançar no conteúdo.")
        else:
            pend = sorted(pend, key=lambda x: (x['dificuldade'] != "🔴 Difícil", x['data_prevista']))
            
            # 📊 Resumo rápido
            col_res1, col_res2, col_res3 = st.columns(3)
            dif_count = len([p for p in pend if p['dificuldade'] == "🔴 Difícil"])
            med_count = len([p for p in pend if p['dificuldade'] == "🟡 Médio"])
            fac_count = len([p for p in pend if p['dificuldade'] == "🟢 Fácil"])
            
            col_res1.metric("🔴 Difícil", dif_count)
            col_res2.metric("🟡 Médio", med_count)
            col_res3.metric("🟢 Fácil", fac_count)
            
            st.divider()
            
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
                        ci1, ci2 = st.columns(2)
                        acr_rev = ci1.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['col']}")
                        tor_rev = ci2.number_input("Total", 0, key=f"to_{p['id']}_{p['col']}")
                    
                    with c_action:
                        st.write("") # Alinhamento
                        if st.button("CONCLUIR", key=f"btn_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                            res_db = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                            n_ac = res_db.data[0]['acertos'] + acr_rev
                            n_to = res_db.data[0]['total'] + tor_rev
                            supabase.table("registros_estudos").update({
                                p['col']: True, 
                                "comentarios": f"{p['coment']} | {p['tipo']}: {acr_rev}/{tor_rev}", 
                                "acertos": n_ac, "total": n_to, 
                                "taxa": (n_ac/n_to*100 if n_to > 0 else 0)
                            }).eq("id", p['id']).execute()
                            st.rerun()
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

    # --- ABA: FOCO (POMODORO) ---
    elif menu == "Foco":
        st.markdown('<h2 class="main-title">⏱️ Modo Foco (Pomodoro)</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Mantenha a concentração total nos seus estudos</p>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="modern-card" style="max-width: 600px; margin: 0 auto;">', unsafe_allow_html=True)
            
            # Seleção de Modo
            col_m1, col_m2 = st.columns(2)
            if col_m1.button("🔥 FOCO (25m)", use_container_width=True, type="primary" if st.session_state.pomodoro_mode == "Foco" else "secondary"):
                st.session_state.pomodoro_mode = "Foco"
                st.session_state.pomodoro_seconds = 25 * 60
                st.session_state.pomodoro_active = False
                st.rerun()
            if col_m2.button("☕ PAUSA (5m)", use_container_width=True, type="primary" if st.session_state.pomodoro_mode == "Pausa" else "secondary"):
                st.session_state.pomodoro_mode = "Pausa"
                st.session_state.pomodoro_seconds = 5 * 60
                st.session_state.pomodoro_active = False
                st.rerun()
            
            # Display do Timer
            mins, secs = divmod(st.session_state.pomodoro_seconds, 60)
            st.markdown(f'<div class="timer-display">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # Barra de Progresso
            total_sec = (25 * 60) if st.session_state.pomodoro_mode == "Foco" else (5 * 60)
            progresso = (total_sec - st.session_state.pomodoro_seconds) / total_sec
            st.markdown(f"""
                <div class="modern-progress-container">
                    <div class="modern-progress-fill" style="width: {progresso*100}%;"></div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            # Controles
            c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([1, 1, 1])
            
            if not st.session_state.pomodoro_active:
                if c_ctrl1.button("▶️ INICIAR", use_container_width=True):
                    st.session_state.pomodoro_active = True
                    st.rerun()
            else:
                if c_ctrl1.button("⏸️ PAUSAR", use_container_width=True):
                    st.session_state.pomodoro_active = False
                    st.rerun()
            
            if c_ctrl2.button("🔄 RESETAR", use_container_width=True):
                st.session_state.pomodoro_seconds = (25 * 60) if st.session_state.pomodoro_mode == "Foco" else (5 * 60)
                st.session_state.pomodoro_active = False
                st.rerun()
                
            # Lógica do Timer (Loop de atualização)
            if st.session_state.pomodoro_active and st.session_state.pomodoro_seconds > 0:
                time.sleep(1)
                st.session_state.pomodoro_seconds -= 1
                st.rerun()
            elif st.session_state.pomodoro_seconds == 0:
                st.session_state.pomodoro_active = False
                st.balloons()
                st.success("🎉 Ciclo finalizado! Hora de descansar ou voltar ao foco.")
                st.session_state.pomodoro_seconds = (25 * 60) if st.session_state.pomodoro_mode == "Foco" else (5 * 60)
            
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: DASHBOARD (PAINEL AVANÇADO) ---
    elif menu == "Dashboard":
        # Chama a função do painel de desempenho
        render_painel_desempenho(df, missao)

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

        # mostrar data atual se existir
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

        with st.form("form_editar_edital"):
                st.markdown("### 📅 Ajustar Data da Prova")
                
                nova_data_escolhida = st.date_input(
                    "Selecione a data da prova", 
                    value=(data_prova_atual or datetime.date.today())
                )
                
                remover = st.checkbox("Remover data da prova (deixar em branco)")

                submitted = st.form_submit_button("Salvar alterações", use_container_width=True)
                
                if submitted:
                    try:
                        valor_final = None if remover else nova_data_escolhida.strftime("%Y-%m-%d")
                        
                        # 1. SALVA NO BANCO - Atualiza a tabela CORRETA: editais_materias
                        res = supabase.table("editais_materias").update({"data_prova": valor_final}).eq("concurso", missao).execute()
                        
                        if res.data:
                            # 2. LIMPA A MEMÓRIA DO APP (MUITO IMPORTANTE)
                            st.cache_data.clear() 
                            
                            # 3. ATUALIZA O ESTADO DA MISSÃO PARA FORÇAR RECARREGAMENTO
                            st.session_state.missao_ativa = missao
                            
                            st.success(f"✅ Data atualizada no banco! Recarregando...")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {e}")
