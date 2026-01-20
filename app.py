import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# ... seus imports (streamlit, pandas, etc)

def render_metric_card(label, value, icon="📊"):
    st.markdown(f"""
        <div style="text-align: center; padding: 15px; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{value}</div>
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
            return int(tempo_str)
    except:
        return 0

# --- INICIALIZAÇÃO OBRIGATÓRIA (ÚNICA - sem duplicação) ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# Inicializar metas semanais
if 'meta_horas' not in st.session_state:
    st.session_state.meta_horas = 22
if 'meta_questoes' not in st.session_state:
    st.session_state.meta_questoes = 350

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# Aplicar estilos base
apply_styles()

# Inicializar estados do Pomodoro
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco"

# CSS Customizado para Layout Moderno
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
    
    /* Tabela de Disciplinas */
    .disciplina-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    .disciplina-table th {
        color: #adb5bd;
        font-size: 0.85rem;
        text-align: left;
        padding: 12px 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        font-weight: 600;
        text-transform: uppercase;
    }
    .disciplina-table td {
        color: #fff;
        padding: 12px 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 0.9rem;
    }
    .disciplina-table tr:hover {
        background-color: rgba(255, 75, 75, 0.05);
    }
    .disciplina-table .percent-cell {
        text-align: center;
        font-weight: 700;
    }
    .disciplina-table .percent-high {
        color: #00FF00;
    }
    .disciplina-table .percent-medium {
        color: #FFD700;
    }
    .disciplina-table .percent-low {
        color: #FF4B4B;
    }
    
    /* Streak Display */
    .streak-container {
        background: linear-gradient(135deg, rgba(255,75,75,0.1), rgba(255,142,142,0.05));
        border: 1px solid rgba(255,75,75,0.2);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
    }
    .streak-number {
        font-size: 3rem;
        font-weight: 800;
        color: #FF4B4B;
        margin: 10px 0;
    }
    .streak-label {
        color: #adb5bd;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Progresso Semanal */
    .weekly-progress-container {
        background: rgba(26, 28, 35, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    }
    .weekly-progress-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #fff;
        margin: 5px 0;
    }
    .weekly-progress-label {
        color: #adb5bd;
        font-size: 0.85rem;
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

def formatar_minutos(minutos_totais):
    """Formata minutos para 'Xh Ymin' ou 'Zmin'."""
    try:
        minutos = int(minutos_totais)
    except Exception:
        return "0min"
    horas = minutos // 60
    minutos_rest = minutos % 60
    if horas > 0:
        return f"{horas}h{minutos_rest:02d}min"
    return f"{minutos_rest}min"

def formatar_horas_minutos(minutos_totais):
    """Formata minutos para 'Xh Ymin' (sempre mostra horas mesmo se zero)."""
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

def calcular_record_streak(df):
    """Calcula o maior streak (recorde) de dias consecutivos."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
        datas = sorted(datas)
    except Exception:
        return 0
    
    if len(datas) == 0:
        return 0
    
    max_streak = 1
    current_streak = 1
    
    for i in range(1, len(datas)):
        diff = (datas[i] - datas[i-1]).days
        if diff == 1:
            current_streak += 1
        else:
            if current_streak > max_streak:
                max_streak = current_streak
            current_streak = 1
    
    if current_streak > max_streak:
        max_streak = current_streak
    
    return max_streak

def calcular_progresso_semanal(df, meta_horas=22, meta_questoes=350):
    """Calcula o progresso da semana atual."""
    hoje = datetime.date.today()
    # Encontra o início da semana (segunda-feira)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    if df.empty:
        return 0, 0, 0, 0
    
    # Filtra registros da semana atual
    df_semana = df.copy()
    df_semana['data_estudo_date'] = pd.to_datetime(df_semana['data_estudo']).dt.date
    df_semana = df_semana[(df_semana['data_estudo_date'] >= inicio_semana) & 
                          (df_semana['data_estudo_date'] <= fim_semana)]
    
    if df_semana.empty:
        return 0, 0, 0, 0
    
    tempo_semana_min = df_semana['tempo'].sum()
    tempo_semana_horas = tempo_semana_min / 60
    questoes_semana = df_semana['total'].sum()
    
    progresso_horas = min((tempo_semana_horas / meta_horas) * 100, 100) if meta_horas > 0 else 0
    progresso_questoes = min((questoes_semana / meta_questoes) * 100, 100) if meta_questoes > 0 else 0
    
    return tempo_semana_horas, questoes_semana, progresso_horas, progresso_questoes

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

# --- FUNÇÃO: Renderizar tabela de disciplinas (ESTILO DA IMAGEM) ---
def render_tabela_disciplinas(df):
    """Renderiza a tabela de disciplinas no estilo da imagem."""
    if df.empty:
        return
    
    # Agrupa dados por disciplina
    df_disciplinas = df.groupby('materia').agg({
        'tempo': 'sum',
        'acertos': 'sum',
        'total': 'sum'
    }).reset_index()
    
    # Calcula métricas adicionais
    df_disciplinas['erros'] = df_disciplinas['total'] - df_disciplinas['acertos']
    df_disciplinas['percentual'] = (df_disciplinas['acertos'] / df_disciplinas['total'] * 100).round(0)
    
    # Ordena por tempo (descrescente)
    df_disciplinas = df_disciplinas.sort_values('tempo', ascending=False)
    
    # Cria a tabela HTML estilizada
    html_table = """
    <div style="margin: 20px 0; border-radius: 10px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1);">
        <table class="disciplina-table">
            <thead>
                <tr>
                    <th style="width: 40%; text-align: left;">Disciplinas</th>
                    <th style="width: 15%; text-align: center;">Tempo</th>
                    <th style="width: 8%; text-align: center;">✓</th>
                    <th style="width: 8%; text-align: center;">✗</th>
                    <th style="width: 8%; text-align: center;">😐</th>
                    <th style="width: 8%; text-align: center;">%</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in df_disciplinas.iterrows():
        # Determina classe de cor baseada no percentual
        percent_class = "percent-high" if row['percentual'] >= 80 else "percent-medium" if row['percentual'] >= 60 else "percent-low"
        
        html_table += f"""
                <tr>
                    <td style="color: #fff; font-weight: 500;">{row['materia']}</td>
                    <td style="text-align: center; color: #adb5bd;">{formatar_horas_minutos(row['tempo'])}</td>
                    <td style="text-align: center; color: #00FF00;">{int(row['acertos'])}</td>
                    <td style="text-align: center; color: #FF4B4B;">{int(row['erros'])}</td>
                    <td style="text-align: center; color: #FFD700;">{int(row['total'])}</td>
                    <td class="percent-cell {percent_class}">{int(row['percentual'])}</td>
                </tr>
        """
    
    html_table += """
            </tbody>
        </table>
    </div>
    """
    
    st.markdown(html_table, unsafe_allow_html=True)

# --- FUNÇÃO: Renderizar streak display ---
def render_streak_display(streak_atual, record_streak):
    """Renderiza o display de streak no estilo da imagem."""
    hoje = datetime.date.today()
    inicio_periodo = hoje - timedelta(days=streak_atual - 1)
    
    # Formata datas
    data_inicio = inicio_periodo.strftime("%d/%m")
    data_fim = hoje.strftime("%d/%m")
    
    st.markdown(f"""
    <div class="streak-container">
        <div class="streak-label">CONSTÂNCIA NOS ESTUDOS</div>
        <div class="streak-number">{streak_atual} dias</div>
        <div style="color: #adb5bd; font-size: 0.9rem; margin-bottom: 15px;">
            Você está há <strong>{streak_atual} dias</strong> sem falhar! Seu recorde é de <strong>{record_streak} dias.</strong>
        </div>
        <div style="display: flex; justify-content: center; align-items: center; color: #FF4B4B; font-weight: 600; font-size: 0.9rem;">
            <span style="margin-right: 10px;">◀</span>
            <span>{data_inicio} ~ {data_fim}</span>
            <span style="margin-left: 10px;">▶</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- FUNÇÃO: Renderizar metas semanais ---
def render_metas_semanais(tempo_semana_horas, questoes_semana, meta_horas, meta_questoes):
    """Renderiza as metas semanais no estilo da imagem."""
    col1, col2 = st.columns(2)
    
    with col1:
        progresso_horas = min((tempo_semana_horas / meta_horas) * 100, 100) if meta_horas > 0 else 0
        st.markdown(f"""
        <div class="weekly-progress-container">
            <div class="weekly-progress-label">Horas de Estudo</div>
            <div class="weekly-progress-value">{tempo_semana_horas:.1f}h / {meta_horas}h</div>
            <div class="modern-progress-container">
                <div class="modern-progress-fill" style="width: {progresso_horas}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        progresso_questoes = min((questoes_semana / meta_questoes) * 100, 100) if meta_questoes > 0 else 0
        st.markdown(f"""
        <div class="weekly-progress-container">
            <div class="weekly-progress-label">Questões</div>
            <div class="weekly-progress-value">{int(questoes_semana)} / {meta_questoes}</div>
            <div class="modern-progress-container">
                <div class="modern-progress-fill" style="width: {progresso_questoes}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    
    # Busca a data da prova diretamente da tabela editais_materias
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

    # --- ABA: HOME (PAINEL GERAL) - MODIFICADA COM NOVAS FUNCIONALIDADES ---
    if menu == "Home":
        st.markdown('<h2 class="main-title">🏠 Home — Painel Geral</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Visão completa do seu desempenho e constância nos estudos</p>', unsafe_allow_html=True)

        if df.empty:
            st.info("Ainda não há registros. Faça seu primeiro estudo para preencher o painel.")
        else:
            # --- SEÇÃO 1: MÉTRICAS PRINCIPAIS (4 CARTÕES) ---
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df['tempo'].sum())
            streak_atual = calcular_streak(df)

            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                render_metric_card("Tempo Total", formatar_minutos(minutos_totais), "⏱️")
            with c2:
                render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
            with c3:
                render_metric_card("Streak", f"{streak_atual} 🔥", "🔥")
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
            
            # --- SEÇÃO 2: CONSTÂNCIA NOS ESTUDOS (STREAK) ---
            record_streak = calcular_record_streak(df)
            render_streak_display(streak_atual, record_streak)
            
            st.divider()
            
            # --- SEÇÃO 3: PAINEL DE DISCIPLINAS (TABELA) ---
            st.markdown('<h3 style="color:#fff; margin-bottom:15px;">📊 PAINEL DE DESEMPENHO</h3>', unsafe_allow_html=True)
            render_tabela_disciplinas(df)
            
            st.divider()
            
            # --- SEÇÃO 4: METAS DE ESTUDO SEMANAL ---
            st.markdown('<h3 style="color:#fff; margin-bottom:15px;">🎯 METAS DE ESTUDO SEMANAL</h3>', unsafe_allow_html=True)
            
            # Calcula progresso da semana
            tempo_semana_horas, questoes_semana, _, _ = calcular_progresso_semanal(
                df, 
                st.session_state.meta_horas, 
                st.session_state.meta_questoes
            )
            
            # Renderiza as metas
            render_metas_semanais(
                tempo_semana_horas, 
                questoes_semana, 
                st.session_state.meta_horas, 
                st.session_state.meta_questoes
            )
            
            # Configuração das metas (em um expander)
            with st.expander("⚙️ Configurar Metas Semanais"):
                col_meta1, col_meta2 = st.columns(2)
                with col_meta1:
                    nova_meta_horas = st.number_input(
                        "Meta de Horas", 
                        min_value=1, 
                        max_value=100, 
                        value=st.session_state.meta_horas,
                        step=1
                    )
                with col_meta2:
                    nova_meta_questoes = st.number_input(
                        "Meta de Questões", 
                        min_value=10, 
                        max_value=1000, 
                        value=st.session_state.meta_questoes,
                        step=10
                    )
                
                if st.button("💾 Salvar Metas", use_container_width=True):
                    st.session_state.meta_horas = nova_meta_horas
                    st.session_state.meta_questoes = nova_meta_questoes
                    st.success("Metas atualizadas com sucesso!")
                    st.rerun()

    # --- ABA: REVISÕES (mantida igual) ---
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

    # --- ABA: DASHBOARD (REMOVIDA A DATA DA PROVA) ---
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
