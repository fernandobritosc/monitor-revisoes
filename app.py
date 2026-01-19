import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

if 'streak_dias' not in st.session_state:
    st.session_state.streak_dias = 0

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

# Inicializar estados do Pomodoro
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco" # Foco ou Pausa

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
    </style>
""", unsafe_allow_html=True)

# --- CONTINUAÇÃO DAS FUNÇÕES AUXILIARES (COLE AQUI) ---

def formatar_tempo_para_bigint(valor_bruto):
    """Converte HHMM ou strings para minutos totais."""
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    return (int(numeros[:-2]) * 60) + int(numeros[-2:])

def formatar_minutos(minutos_totais):
    """Converte minutos totais para o formato 'XXh XXm'."""
    h = int(minutos_totais // 60)
    m = int(minutos_totais % 60)
    return f"{h}h {m:02d}m"

def get_badge_cor(taxa):
    """Define as cores do design system para os badges de performance."""
    if taxa >= 80: return "#00FF00", "Excelente", "rgba(0, 255, 0, 0.1)"
    elif taxa >= 60: return "#FFD700", "Aceitável", "rgba(255, 215, 0, 0.1)"
    else: return "#FF4B4B", "Crítico", "rgba(255, 75, 75, 0.1)"

def render_metric_card(label, value, icon="📊"):
    """Renderiza o card de métrica estilizado para a aba Dashboard."""
    st.markdown(f"""
        <div class="modern-card" style="text-align: center; padding: 15px;">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #fff;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- RESTAURAÇÃO DAS FUNÇÕES DE LÓGICA DE REVISÃO ---

def calcular_proximo_intervalo(dificuldade, taxa):
    """
    Calcula o intervalo adaptativo de revisão baseado em dificuldade e taxa de acerto.
    
    Lógica:
    - Fácil: 15 dias (ou 20 se taxa > 80%)
    - Médio: 7 dias (padrão)
    - Difícil: 3 dias se taxa < 70%, senão 5 dias
    
    Args:
        dificuldade: str - "🟢 Fácil", "🟡 Médio" ou "🔴 Difícil"
        taxa: float - Taxa de acerto em porcentagem (0-100)
    
    Returns:
        int - Número de dias até a próxima revisão
    """
    # Normalizar dificuldade (remover emojis se necessário)
    dif_limpa = dificuldade.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
    
    if "Fácil" in dif_limpa or dificuldade == "🟢 Fácil":
        # Fácil: 15-20 dias dependendo da performance
        return 20 if taxa >= 80 else 15
    
    elif "Médio" in dif_limpa or dificuldade == "🟡 Médio":
        # Médio: 7 dias (padrão)
        return 7
    
    elif "Difícil" in dif_limpa or dificuldade == "🔴 Difícil":
        # Difícil: 3 dias se taxa baixa, 5 se taxa aceitável
        return 3 if taxa < 70 else 5
    
    else:
        # Fallback: 7 dias
        return 7

def tempo_recomendado_rev24h(dificuldade):
    """
    Retorna tempo recomendado e descrição para revisão 24h baseado na dificuldade.
    
    Args:
        dificuldade: str - "🟢 Fácil", "🟡 Médio" ou "🔴 Difícil"
    
    Returns:
        tuple: (tempo_minutos: int, descricao: str)
    """
    dif_limpa = dificuldade.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
    
    if "Fácil" in dif_limpa or dificuldade == "🟢 Fácil":
        return 15, "Rápida (Fácil)"
    elif "Médio" in dif_limpa or dificuldade == "🟡 Médio":
        return 25, "Normal (Médio)"
    elif "Difícil" in dif_limpa or dificuldade == "🔴 Difícil":
        return 35, "Aprofundada (Difícil)"
    else:
        return 20, "Padrão"

def calcular_streak(df):
    if df.empty: return 0
    datas = pd.to_datetime(df['data_estudo']).dt.date.unique()
    datas = sorted(datas, reverse=True)
    streak, hoje, alvo = 0, datetime.date.today(), datetime.date.today()
    if datas[0] < hoje and (hoje - datas[0]).days > 1: return 0
    elif datas[0] < hoje: alvo = datas[0]
    for d in datas:
        if d == alvo:
            streak += 1
            alvo -= timedelta(days=1)
        else: break
    return streak

def calcular_countdown(data_prova_str):
    if not data_prova_str: return None, "#adb5bd"
    dias = (pd.to_datetime(data_prova_str).date() - datetime.date.today()).days
    cor = "#FF4B4B" if dias <= 7 else "#FFD700" if dias <= 30 else "#00FF00"
    return dias, cor

def obter_progresso_semana(df):
    if df.empty: return 0, 0
    hoje = datetime.date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    df_sem = df[pd.to_datetime(df['data_estudo']).dt.date >= inicio_semana]
    return df_sem['tempo'].sum()/60, df_sem['total'].sum()
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
            
            btn_cadastrar = st.form_submit_button("🚀 INICIAR MISSÃO", use_container_width=True, type="primary")
            
            if btn_cadastrar:
                if nome_concurso and cargo_concurso:
                    try:
                        supabase.table("editais_materias").insert({
                            "concurso": nome_concurso,
                            "cargo": cargo_concurso,
                            "materia": "Geral",
                            "topicos": ["Introdução"]
                        }).execute()
                        st.success(f"✅ Missão '{nome_concurso}' criada com sucesso!")
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
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"<h2 style='color:#FF4B4B; margin-bottom:0;'>{missao}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#adb5bd; font-size:0.8rem; margin-bottom:20px;'>{dados.get('cargo', '')}</p>", unsafe_allow_html=True)
        
        if st.button("← Voltar à Central", use_container_width=True): 
            st.session_state.missao_ativa = None
            st.rerun()
        
        st.write("")
        menu = option_menu(None, ["Revisões", "Registrar", "Foco", "Dashboard", "Histórico", "Configurar"], 
                           icons=["arrow-repeat", "pencil-square", "clock", "grid", "list", "gear"], 
                           default_index=0,
                           styles={
                               "container": {"padding": "0!important", "background-color": "transparent"},
                               "icon": {"color": "#FF4B4B", "font-size": "18px"}, 
                               "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "rgba(255,75,75,0.1)"},
                               "nav-link-selected": {"background-color": "rgba(255,75,75,0.2)", "border-left": "3px solid #FF4B4B"}
                           })

    # --- ABA: REVISÕES ---
    if menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            filtro_rev = st.segmented_control("Visualizar:", ["Pendentes/Hoje", "Todas (incluindo futuras)"], default="Pendentes/Hoje")
        with c2:
            filtro_dif = st.segmented_control("Dificuldade:", ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"], default="Todas")
    
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                dif = row.get('dificuldade', '🟡 Médio')  # 🆕 Ler dificuldade
                
                # Lógica de Revisão 24h
                if not row.get('rev_24h', False):
                    dt_prev = dt_est + timedelta(days=1)
                    if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                        atraso = (hoje - dt_prev).days
                        pend.append({
                            "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                            "tipo": "Revisão 24h", "col": "rev_24h", "atraso": atraso, 
                            "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                            "dificuldade": dif,  # 🆕 Adicionar dificuldade
                            "taxa": tx
                        })
                
                # Lógica de Ciclos Longos (AGORA ADAPTATIVA)
                elif row.get('rev_24h', True):
                    # 🆕 Usar intervalo adaptativo baseado em dificuldade
                    intervalo = calcular_proximo_intervalo(dif, tx)  # ← 2 parâmetros
                    
                    # Determinar qual coluna atualizar (simplificado)
                    if intervalo == 3:
                        col_alv, lbl = "rev_07d", f"Revisão Curta (3d)"
                    elif intervalo == 5:
                        col_alv, lbl = "rev_07d", f"Revisão Média (5d)"
                    elif intervalo == 7:
                        col_alv, lbl = "rev_07d", "Revisão 7d"
                    else:  # 15+ dias
                        col_alv, lbl = "rev_15d", "Revisão Longa (15d+)"
                    
                    if not row.get(col_alv, False):
                        dt_prev = dt_est + timedelta(days=intervalo)
                        if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                            atraso = (hoje - dt_prev).days
                            pend.append({
                                "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                                "tipo": lbl, "col": col_alv, "atraso": atraso, 
                                "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                                "dificuldade": dif,  # 🆕 Adicionar dificuldade
                                "taxa": tx
                            })
        
        # 🆕 Filtrar por dificuldade
        if filtro_dif != "Todas":
            pend = [p for p in pend if p['dificuldade'] == filtro_dif]
        
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
                        
                        # 🆕 Mostrar dificuldade e recomendação de tempo
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
                    
                    # 🆕 NOVO: Classificação de Dificuldade
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
                                "dificuldade": dif_reg,  # 🆕 Novo campo
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

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("Ainda não há dados suficientes para gerar o dashboard.")
        else:
            # Métricas Principais
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q>0 else 0)
            horas = df['tempo'].sum()/60
            
            m1, m2, m3 = st.columns(3)
            with m1: render_metric_card("Total de Questões", int(t_q), "📝")
            with m2: render_metric_card("Precisão Média", f"{precisao:.1f}%", "🎯")
            with m3: render_metric_card("Horas Estudadas", f"{horas:.1f}h", "⏱️")
            
            st.write("")
            
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

# --- ABA: HOME (REFATORADA COMPLETAMENTE) ---
    elif menu == "Home":
        st.markdown('<h2 class="main-title">🏠 Painel Principal</h2>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("📚 Comece a registrar seus estudos para ver o painel em ação!")
        else:
            # ========== TOPO: MÉTRICAS PRINCIPAIS (4 COLUNAS) ==========
            st.markdown("#### 📊 Suas Métricas")
            
            col_tempo, col_precisao, col_streak, col_countdown = st.columns(4)
            
            # 1. Tempo Total
            with col_tempo:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                tempo_total = df['tempo'].sum()
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">⏱️ Tempo Total</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 5px;">{formatar_minutos(tempo_total)}</div>
                        <div style="color: #adb5bd; font-size: 0.7rem;">{len(df)} registros</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 2. Precisão Geral
            with col_precisao:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                total_q = int(df['total'].sum())
                acertos_q = int(df['acertos'].sum())
                taxa_geral = (acertos_q / total_q * 100) if total_q > 0 else 0
                cor_taxa, _, _ = get_badge_cor(taxa_geral)
                
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">🎯 Precisão</div>
                        <div style="font-size: 2rem; font-weight: 800; color: {cor_taxa}; margin-bottom: 5px;">{taxa_geral:.0f}%</div>
                        <div style="color: #adb5bd; font-size: 0.7rem;">{acertos_q}/{total_q} questões</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 3. Streak (Constância)
            with col_streak:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                streak = calcular_streak(df)
                
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">🔥 Constância</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #FF4B4B; margin-bottom: 5px;">{streak}</div>
                        <div style="color: #adb5bd; font-size: 0.7rem;">dias seguidos</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 4. Countdown para Prova
            with col_countdown:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                try:
                    data_prova = dados.get('data_prova', None)
                    dias_faltam, cor_urgencia = calcular_countdown(data_prova)
                    
                    if dias_faltam is not None:
                        st.markdown(f"""
                            <div style="text-align: center;">
                                <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">⏰ Para a Vitória</div>
                                <div style="font-size: 2rem; font-weight: 800; color: {cor_urgencia}; margin-bottom: 5px;">{dias_faltam}</div>
                                <div style="color: #adb5bd; font-size: 0.7rem;">dias faltam</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div style="text-align: center;">
                                <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">⏰ Para a Vitória</div>
                                <div style="font-size: 1rem; font-weight: 600; color: #FF8E8E;">Não config.</div>
                            </div>
                        """, unsafe_allow_html=True)
                except:
                    st.markdown(f"""
                        <div style="text-align: center;">
                            <div style="color: #adb5bd; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">⏰ Para a Vitória</div>
                            <div style="font-size: 0.9rem; color: #adb5bd;">Erro ao carregar</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # ========== METAS SEMANAIS COM EXPANSOR ==========
            st.markdown("#### 📋 Metas Semanais")
            
            with st.expander("⚙️ Ajustar Metas Semanais", expanded=False):
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                col_meta1, col_meta2 = st.columns(2)
                
                with col_meta1:
                    meta_horas_input = st.number_input(
                        "Meta de Horas (semanal)",
                        value=int(dados.get('meta_horas', 15)),
                        min_value=1,
                        max_value=168,
                        step=1,
                        key="meta_horas_input"
                    )
                
                with col_meta2:
                    meta_questoes_input = st.number_input(
                        "Meta de Questões (semanal)",
                        value=int(dados.get('meta_questoes', 100)),
                        min_value=1,
                        max_value=10000,
                        step=10,
                        key="meta_questoes_input"
                    )
                
                st.divider()
                
                if st.button("💾 SALVAR METAS", use_container_width=True, type="primary"):
                    try:
                        supabase.table("editais_materias").update({
                            "meta_horas": int(meta_horas_input),
                            "meta_questoes": int(meta_questoes_input)
                        }).eq("concurso", missao).execute()
                        
                        st.success("✅ Metas atualizadas com sucesso!")
                        dados['meta_horas'] = meta_horas_input
                        dados['meta_questoes'] = meta_questoes_input
                        time.sleep(1)
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar metas: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # ========== PROGRESSO DAS METAS (BARRAS) ==========
            st.markdown("##### 📈 Progresso da Semana")
            
            horas_semana, questoes_semana = obter_progresso_semana(df)
            meta_horas = dados.get('meta_horas', 15)
            meta_questoes = dados.get('meta_questoes', 100)
            
            progress_horas = min((horas_semana / meta_horas * 100) if meta_horas > 0 else 0, 100)
            progress_questoes = min((questoes_semana / meta_questoes * 100) if meta_questoes > 0 else 0, 100)
            
            col_prog1, col_prog2 = st.columns(2)
            
            with col_prog1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                cor_horas = "#00FF00" if progress_horas >= 100 else "#FFD700" if progress_horas >= 70 else "#FF4B4B"
                
                st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #adb5bd; font-size: 0.8rem; font-weight: 600;">⏱️ Horas de Estudo</span>
                            <span style="color: {cor_horas}; font-size: 0.9rem; font-weight: 700;">
                                {horas_semana:.1f}h / {meta_horas}h
                            </span>
                        </div>
                    </div>
                    <div class="modern-progress-container">
                        <div class="modern-progress-fill" style="width: {progress_horas}%; background: linear-gradient(90deg, {cor_horas}, #FF8E8E);"></div>
                    </div>
                    <div style="color: #adb5bd; font-size: 0.75rem; margin-top: 8px; text-align: right;">
                        {progress_horas:.0f}% da meta
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_prog2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                cor_questoes = "#00FF00" if progress_questoes >= 100 else "#FFD700" if progress_questoes >= 70 else "#FF4B4B"
                
                st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #adb5bd; font-size: 0.8rem; font-weight: 600;">📝 Questões Resolvidas</span>
                            <span style="color: {cor_questoes}; font-size: 0.9rem; font-weight: 700;">
                                {int(questoes_semana)} / {meta_questoes}
                            </span>
                        </div>
                    </div>
                    <div class="modern-progress-container">
                        <div class="modern-progress-fill" style="width: {progress_questoes}%; background: linear-gradient(90deg, {cor_questoes}, #FF8E8E);"></div>
                    </div>
                    <div style="color: #adb5bd; font-size: 0.75rem; margin-top: 8px; text-align: right;">
                        {progress_questoes:.0f}% da meta
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # ========== TABELA DE DISCIPLINAS (GRID COM HTML/CSS) ==========
            st.markdown("#### 📚 Resumo por Disciplina")
            
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
            df_disciplinas = df.groupby('materia').agg({
                'tempo': 'sum',
                'total': 'sum',
                'acertos': 'sum',
                'taxa': 'mean'
            }).reset_index().sort_values('total', ascending=False)
            
            # Header da tabela (Grid)
            st.markdown("""
                <div style="display: grid; grid-template-columns: 2.5fr 1.2fr 1.5fr 1fr 1.2fr; gap: 15px; margin-bottom: 15px; padding-bottom: 12px; border-bottom: 2px solid rgba(255,255,255,0.1);">
                    <div style="color: #adb5bd; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Disciplina</div>
                    <div style="color: #adb5bd; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Tempo</div>
                    <div style="color: #adb5bd; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Desempenho</div>
                    <div style="color: #adb5bd; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Taxa</div>
                    <div style="color: #adb5bd; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Status</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Linhas da tabela
            for _, disc in df_disciplinas.iterrows():
                tempo_formatado = formatar_minutos(disc['tempo'])
                acer_disc = int(disc['acertos'])
                total_disc = int(disc['total'])
                taxa_disc = disc['taxa']
                
                cor_taxa, badge_text, cor_bg_badge = get_badge_cor(taxa_disc)
                
                st.markdown(f"""
                    <div style="display: grid; grid-template-columns: 2.5fr 1.2fr 1.5fr 1fr 1.2fr; gap: 15px; align-items: center; margin-bottom: 15px; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div style="color: #fff; font-weight: 600; font-size: 0.95rem;">{disc['materia']}</div>
                        <div style="color: #adb5bd; font-size: 0.9rem;">{tempo_formatado}</div>
                        <div style="color: #adb5bd; font-size: 0.9rem;">{acer_disc}/{total_disc}</div>
                        <div style="color: {cor_taxa}; font-weight: 700; font-size: 0.9rem;">{taxa_disc:.0f}%</div>
                        <div>
                            <span class="badge" style="background: {cor_bg_badge}; color: {cor_taxa}; border: 1px solid {cor_taxa}80; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;">
                                {badge_text}
                            </span>
                        </div>
                    </div>
                    <div class="modern-progress-container" style="margin: 0 0 15px 0; height: 6px;">
                        <div class="modern-progress-fill" style="width: {taxa_disc}%; background: linear-gradient(90deg, {cor_taxa}, #FF8E8E);"></div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # ========== GRÁFICOS (LADO A LADO, REDUZIDOS) ==========
            st.markdown("#### 📊 Análise Visual")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Distribuição por Disciplina")
                
                fig_pie = px.pie(
                    df, 
                    values='total', 
                    names='materia', 
                    hole=0.6,
                    color_discrete_sequence=["#FF4B4B", "#FFD700", "#00FF00", "#4B90FF", "#FF8E8E"]
                )
                fig_pie.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0), 
                    showlegend=True,
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#fff", size=11),
                    height=300
                )
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_g2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Evolução de Desempenho")
                
                df_evo = df.sort_values('data_estudo').groupby('data_estudo')['taxa'].mean().reset_index()
                df_evo.columns = ['data_estudo', 'taxa']
                df_evo['data_estudo'] = pd.to_datetime(df_evo['data_estudo']).dt.strftime('%d/%m')
                
                fig_line = px.line(df_evo, x='data_estudo', y='taxa', markers=True)
                fig_line.update_traces(
                    line=dict(color='#FF4B4B', width=3), 
                    marker=dict(size=7, color='#FF4B4B')
                )
                fig_line.update_layout(
                    margin=dict(t=20, b=0, l=40, r=0),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#fff", size=11),
                    xaxis_title=None, 
                    yaxis_title="Taxa %",
                    hovermode='x unified',
                    height=300,
                    yaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
