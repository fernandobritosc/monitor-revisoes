import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import re
import time
import numpy as np

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

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "Home"

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- 1. CONFIGURAÇÃO SEM SIDEBAR ---
st.set_page_config(
    page_title="Monitor de Revisões Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# CSS para layout sem sidebar
st.markdown("""
    <style>
    /* Esconder sidebar completamente */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Menu superior fixo */
    .top-menu-container {
        position: sticky;
        top: 0;
        z-index: 1000;
        background: rgba(14, 17, 23, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255, 75, 75, 0.3);
        padding: 15px 20px;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    /* Header da missão */
    .mission-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    
    .mission-title {
        margin: 0;
        color: #FF4B4B;
        font-size: 1.6rem;
        font-weight: 700;
    }
    
    .mission-subtitle {
        margin: 0;
        color: #adb5bd;
        font-size: 0.9rem;
    }
    
    /* Menu de navegação */
    .nav-tabs {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        padding-bottom: 5px;
    }
    
    .nav-tab {
        padding: 10px 16px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
        transition: all 0.3s;
        font-size: 0.9rem;
        white-space: nowrap;
        text-align: center;
        color: #adb5bd;
        text-decoration: none;
    }
    
    .nav-tab:hover {
        background: rgba(255, 75, 75, 0.1);
        border-color: rgba(255, 75, 75, 0.3);
        color: #fff;
        transform: translateY(-2px);
    }
    
    .nav-tab.active {
        background: rgba(255, 75, 75, 0.2);
        border-color: #FF4B4B;
        color: #FF4B4B;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
    }
    
    /* Botões */
    .btn-voltar {
        background: rgba(255, 75, 75, 0.1) !important;
        border: 1px solid rgba(255, 75, 75, 0.3) !important;
        color: #FF4B4B !important;
        font-weight: 600 !important;
    }
    
    .btn-voltar:hover {
        background: rgba(255, 75, 75, 0.2) !important;
    }
    
    /* Cards modernos (mantendo seu estilo) */
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
    
    /* Títulos */
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
    
    /* Responsividade */
    @media (max-width: 768px) {
        .nav-tabs {
            flex-wrap: wrap;
        }
        .nav-tab {
            flex: 1;
            min-width: 80px;
            font-size: 0.8rem;
            padding: 8px 10px;
        }
        .mission-title {
            font-size: 1.3rem;
        }
    }
    
    /* Esconder elementos padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Importações dos seus módulos
try:
    from database import supabase
    from logic import get_editais, excluir_concurso_completo
    from styles import apply_styles
    apply_styles()
except:
    # Fallback para desenvolvimento
    st.warning("Algumas importações podem estar faltando. Executando em modo de desenvolvimento.")

# Inicializar estados do Pomodoro
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco"

# --- 2. FUNÇÕES AUXILIARES (MANTENDO SUAS FUNÇÕES) ---
def render_metric_card(label, value, icon="📊"):
    st.markdown(f"""
        <div style="text-align: center; padding: 15px; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; background: rgba(15, 52, 96, 0.5);">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

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

def calcular_proximo_intervalo(dificuldade, taxa_acerto):
    if dificuldade == "🟢 Fácil":
        return 15 if taxa_acerto > 80 else 7
    elif dificuldade == "🟡 Médio":
        return 7
    else:
        return 3 if taxa_acerto < 70 else 5

def tempo_recomendado_rev24h(dificuldade):
    tempos = {
        "🟢 Fácil": (2, "Apenas releitura rápida dos títulos"),
        "🟡 Médio": (8, "Revise seus grifos + 5 questões"),
        "🔴 Difícil": (18, "Active Recall completo + questões-chave")
    }
    return tempos.get(dificuldade, (5, "Padrão"))

@st.cache_data(ttl=300)
def calcular_revisoes_pendentes(df, filtro_rev, filtro_dif):
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
        
        # Lógica de Ciclos Longos
        elif row.get('rev_24h', True):
            intervalo = calcular_proximo_intervalo(dif, tx)
            
            if intervalo <= 7:
                col_alv, lbl = "rev_07d", f"Revisão {intervalo}d"
            else:
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
    
    if filtro_dif != "Todas":
        pend = [p for p in pend if p['dificuldade'] == filtro_dif]
    
    return pend

# --- 3. TELA DE SELEÇÃO DE MISSÃO ---
if st.session_state.missao_ativa is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Selecione sua missão ou inicie um novo ciclo</p>', unsafe_allow_html=True)
    
    # Simulando get_editais para exemplo
    try:
        ed = get_editais(supabase) if 'supabase' in locals() else {}
    except:
        ed = {}
    
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
                        if 'supabase' in locals():
                            payload = {
                                "concurso": nome_concurso,
                                "cargo": cargo_concurso,
                                "materia": "Geral",
                                "topicos": ["Introdução"]
                            }
                            if data_prova_input:
                                payload["data_prova"] = data_prova_input.strftime("%Y-%m-%d")
                            supabase.table("editais_materias").insert(payload).execute()
                        
                        st.success(f"✅ Missão '{nome_concurso}' criada com sucesso!")
                        time.sleep(1)
                        st.session_state.missao_ativa = nome_concurso
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
                else:
                    st.warning("⚠️ Por favor, preencha o nome e o cargo.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 4. TELA COM MISSÃO ATIVA (MENU SUPERIOR) ---
else:
    missao = st.session_state.missao_ativa
    
    # Carregar dados da missão
    try:
        if 'supabase' in locals():
            res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
            df = pd.DataFrame(res.data)
        else:
            # Dados de exemplo para demonstração
            df = pd.DataFrame({
                'id': [1, 2, 3],
                'concurso': [missao, missao, missao],
                'materia': ['Direito Administrativo', 'Português', 'Raciocínio Lógico'],
                'assunto': ['Princípios', 'Concordância', 'Lógica Proposicional'],
                'data_estudo': ['2024-01-15', '2024-01-14', '2024-01-13'],
                'acertos': [11, 18, 22],
                'total': [20, 30, 25],
                'taxa': [55.0, 60.0, 88.0],
                'dificuldade': ['🔴 Difícil', '🟡 Médio', '🟢 Fácil'],
                'comentarios': ['Precisa revisar', 'Bom desempenho', 'Excelente'],
                'tempo': [70, 105, 120],
                'rev_24h': [False, True, True],
                'rev_07d': [False, False, True],
                'rev_15d': [False, False, False],
                'rev_30d': [False, False, False]
            })
    except:
        df = pd.DataFrame()
    
    # Buscar data da prova
    try:
        if 'supabase' in locals():
            res_data_prova = supabase.table("editais_materias").select("data_prova").eq("concurso", missao).limit(1).execute()
            if res_data_prova.data and len(res_data_prova.data) > 0:
                data_prova_direta = res_data_prova.data[0].get('data_prova')
            else:
                data_prova_direta = None
        else:
            data_prova_direta = "2024-06-15"  # Exemplo
    except:
        data_prova_direta = None
    
    # Buscar dados do edital
    try:
        dados = get_editais(supabase).get(missao, {}) if 'supabase' in locals() else {'cargo': 'Cargo Exemplo'}
    except:
        dados = {'cargo': 'Cargo Exemplo'}
    
    # ============================================
    # MENU SUPERIOR FIXO
    # ============================================
    st.markdown(f'''
    <div class="top-menu-container">
        <div class="mission-header">
            <div>
                <h1 class="mission-title">{missao}</h1>
                <p class="mission-subtitle">{dados.get('cargo', '')}</p>
            </div>
            <div>
                <a href="#" onclick="window.location.href='?reset=true'; return false;">
                    <button class="nav-tab btn-voltar">← Trocar Missão</button>
                </a>
            </div>
        </div>
        
        <div class="nav-tabs">
            <a href="#" onclick="window.location.href='?menu=Home'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Home' else ''}">🏠 Home</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Revisões'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Revisões' else ''}">🔄 Revisões</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Registrar'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Registrar' else ''}">📝 Registrar</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Foco'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Foco' else ''}">⏱️ Foco</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Dashboard'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Dashboard' else ''}">📊 Dashboard</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Histórico'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Histórico' else ''}">📜 Histórico</div>
            </a>
            <a href="#" onclick="window.location.href='?menu=Configurar'; return false;">
                <div class="nav-tab {'active' if st.session_state.current_menu == 'Configurar' else ''}">⚙️ Configurar</div>
            </a>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Botão real para trocar missão (fallback)
    if st.button("← Trocar Missão", key="trocar_missao", type="secondary"):
        st.session_state.missao_ativa = None
        st.rerun()
    
    st.write("")  # Espaço
    
    # Menu nativo como fallback (opcional)
    menu_options = ["Home", "Revisões", "Registrar", "Foco", "Dashboard", "Histórico", "Configurar"]
    menu_selected = st.selectbox(
        "Navegação", 
        menu_options,
        index=menu_options.index(st.session_state.current_menu) if st.session_state.current_menu in menu_options else 0,
        label_visibility="collapsed",
        key="menu_select"
    )
    
    # Atualizar menu atual
    if menu_selected != st.session_state.current_menu:
        st.session_state.current_menu = menu_selected
        st.rerun()
    
    # Definir menu
    menu = st.session_state.current_menu
    
    # ============================================
    # CONTEÚDO DAS ABAS
    # ============================================
    
    # --- ABA: HOME ---
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
                # Countdown da prova
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

            # Status por disciplina
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
                        <div class="modern-progress-container" style="margin-top:8px; height:8px; background:rgba(255,255,255,0.05); border-radius:10px; overflow:hidden;">
                            <div style="height:100%; border-radius:10px; background:linear-gradient(90deg, #FF4B4B, #FF8E8E); width: {pct}%;"></div>
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
    
        pend = calcular_revisoes_pendentes(df, filtro_rev, filtro_dif)
        
        if not pend: 
            st.success("✨ Tudo em dia! Aproveite para avançar no conteúdo.")
        else:
            pend = sorted(pend, key=lambda x: (x['dificuldade'] != "🔴 Difícil", x['data_prevista']))
            
            # Resumo rápido
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
                            st.success(f"Revisão de {p['materia']} concluída!")
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    
    # --- ABA: REGISTRAR ---
    elif menu == "Registrar":
        st.markdown('<h2 class="main-title">📝 Novo Registro de Estudo</h2>', unsafe_allow_html=True)
        
        # Matérias disponíveis
        if not df.empty:
            materias_disponiveis = list(df['materia'].unique())
        else:
            materias_disponiveis = ["Direito Administrativo", "Português", "Raciocínio Lógico", "Informática"]
        
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
            c1, c2 = st.columns([2, 1])
            dt_reg = c1.date_input("Data do Estudo", format="DD/MM/YYYY")
            tm_reg = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30min")
            
            mat_reg = st.selectbox("Disciplina", materias_disponiveis)
            ass_reg = st.text_input("Assunto/Tópico", placeholder="Ex: Princípios administrativos")
            
            st.divider()
            
            with st.form("form_registro_final", clear_on_submit=True):
                ca_reg, ct_reg = st.columns(2)
                ac_reg = ca_reg.number_input("Questões Acertadas", 0)
                to_reg = ct_reg.number_input("Total de Questões", 1)
                
                # Classificação de Dificuldade
                st.markdown("##### 🎯 Como foi esse assunto?")
                dif_reg = st.segmented_control(
                    "Classificação:",
                    ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                    default="🟡 Médio"
                )
                
                # Mostrar recomendação
                tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_reg)
                st.info(f"💡 **{dif_reg}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                
                st.divider()
                
                com_reg = st.text_area("Anotações / Comentários", placeholder="O que você aprendeu ou sentiu dificuldade?")
                
                btn_salvar = st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True, type="primary")
                
                if btn_salvar:
                    try:
                        t_b = formatar_tempo_para_bigint(tm_reg)
                        taxa = (ac_reg/to_reg*100 if to_reg > 0 else 0)
                        
                        st.success("✅ Registro salvo com sucesso!")
                        st.info(f"📊 {ac_reg}/{to_reg} acertos ({taxa:.1f}%) | ⏱️ {t_b}min")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # --- ABA: FOCO ---
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
            st.markdown(f'<div style="font-size:5rem; font-weight:800; color:#fff; text-align:center; margin:20px 0;">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # Barra de Progresso
            total_sec = (25 * 60) if st.session_state.pomodoro_mode == "Foco" else (5 * 60)
            progresso = (total_sec - st.session_state.pomodoro_seconds) / total_sec
            st.markdown(f"""
                <div style="width:100%; height:10px; background-color:rgba(255,255,255,0.05); border-radius:5px; margin:10px 0; overflow:hidden;">
                    <div style="height:100%; border-radius:5px; background:linear-gradient(90deg, #FF4B4B, #FF8E8E); width: {progresso*100}%;"></div>
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
                
            # Lógica do Timer
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
        
        # Métricas
        m1, m2, m3 = st.columns(3)
        with m1: render_metric_card("Questões", int(t_q), "📝")
        with m2: render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
        with m3: render_metric_card("Horas", f"{horas:.1f}h", "⏱️")
        
        st.divider()
        
        # Gráficos
        if not df.empty:
            c_g1, c_g2 = st.columns(2)
            
            with c_g1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Distribuição por Matéria")
                fig_pie = px.pie(df, values='total', names='materia', hole=0.6)
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c_g2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Evolução de Precisão")
                try:
                    df['data_estudo'] = pd.to_datetime(df['data_estudo'])
                    df_ev = df.groupby('data_estudo')['taxa'].mean().reset_index()
                    st.line_chart(df_ev.set_index('data_estudo'))
                except:
                    st.info("Não há dados suficientes para o gráfico")
                st.markdown('</div>', unsafe_allow_html=True)
    
    # --- ABA: HISTÓRICO ---
    elif menu == "Histórico":
        st.markdown('<h2 class="main-title">📜 Histórico de Estudos</h2>', unsafe_allow_html=True)
        
        if not df.empty:
            st.dataframe(
                df[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'dificuldade']],
                column_config={
                    "data_estudo": "Data",
                    "materia": "Matéria",
                    "assunto": "Assunto",
                    "acertos": "Acertos",
                    "total": "Total",
                    "taxa": st.column_config.NumberColumn("Taxa %", format="%.1f"),
                    "dificuldade": "Dificuldade"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("📚 Nenhum registro de estudo encontrado ainda.")
    
    # --- ABA: CONFIGURAR ---
    elif menu == "Configurar":
        st.markdown('<h2 class="main-title">⚙️ Configurar Missão</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Editar dados do edital ativo</p>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('### Dados do Edital', unsafe_allow_html=True)
            st.write(f"**Concurso:** {missao}")
            st.write(f"**Cargo:** {dados.get('cargo', '—')}")
            st.write(f"**Data da Prova:** {data_prova_direta if data_prova_direta else 'Não definida'}")
            
            st.divider()
            
            # Ajustar data da prova
            with st.form("form_editar_edital"):
                st.markdown("### 📅 Ajustar Data da Prova")
                
                if data_prova_direta:
                    data_atual = pd.to_datetime(data_prova_direta).date()
                else:
                    data_atual = datetime.date.today() + timedelta(days=30)
                
                nova_data = st.date_input("Nova data da prova", value=data_atual)
                remover = st.checkbox("Remover data da prova")
                
                submitted = st.form_submit_button("Salvar alterações", use_container_width=True)
                
                if submitted:
                    if remover:
                        st.success("✅ Data da prova removida!")
                    else:
                        st.success(f"✅ Data da prova atualizada para {nova_data.strftime('%d/%m/%Y')}")
                    time.sleep(1)
                    st.rerun()
            
            st.divider()
            
            # Estatísticas da missão
            st.markdown("### 📈 Estatísticas")
            if not df.empty:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Registros", len(df))
                col2.metric("Média de Acertos", f"{df['taxa'].mean():.1f}%")
                col3.metric("Tempo Total", f"{df['tempo'].sum()/60:.1f}h")
            else:
                st.info("Nenhuma estatística disponível ainda.")
            
            st.markdown('</div>', unsafe_allow_html=True)
