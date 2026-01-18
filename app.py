import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu
from notion_client import Client # Biblioteca necessária para o Notion

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# CONFIGURAÇÃO DO NOTION (Dados obtidos nas suas capturas)
NOTION_TOKEN = "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" #
DATABASE_ID = "2ec82bc022d780a592dcea3616f520c0" #

notion = Client(auth=NOTION_TOKEN)

def get_notion_errors_count():
    """Busca no Notion a quantidade de erros pendentes (Revisado = Falso)"""
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "property": "Revisado",
                "checkbox": {"equals": False}
            }
        )
        return len(response.get("results", []))
    except Exception as e:
        return 0

# Aplicar estilos base
apply_styles()

# Inicializar estados do Pomodoro e Missão
if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_active' not in st.session_state:
    st.session_state.pomodoro_active = False
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Foco"

# CSS Customizado para Layout Moderno
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .modern-card {
        background: rgba(26, 28, 35, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px; padding: 20px; margin-bottom: 15px;
        transition: transform 0.2s ease, border 0.2s ease;
    }
    .modern-card:hover { border: 1px solid rgba(255, 75, 75, 0.4); transform: translateY(-2px); }
    .main-title {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 1rem;
    }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-red { background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.3); }
    .badge-green { background: rgba(0, 255, 0, 0.1); color: #00FF00; border: 1px solid rgba(0, 255, 0, 0.2); }
    .modern-progress-container { width: 100%; background-color: rgba(255, 255, 255, 0.05); border-radius: 10px; height: 8px; overflow: hidden; }
    .modern-progress-fill { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #FF4B4B, #FF8E8E); }
    .timer-display { font-size: 5rem; font-weight: 800; color: #fff; text-align: center; margin: 20px 0; text-shadow: 0 0 20px rgba(255, 75, 75, 0.3); }
    </style>
""", unsafe_allow_html=True)

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
if st.session_state.missao_ativa is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 Missões Ativas", "➕ Novo Cadastro"])
    
    with tabs[0]:
        if not ed: st.info("Nenhuma missão ativa no momento.")
        else:
            cols = st.columns(2)
            for i, (nome, d_concurso) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f'<div class="modern-card"><h3 style="margin:0; color:#FF4B4B;">{nome}</h3><p style="color:#adb5bd;">{d_concurso["cargo"]}</p></div>', unsafe_allow_html=True)
                    if st.button(f"Acessar Missão", key=f"ac_{nome}", use_container_width=True, type="primary"):
                        st.session_state.missao_ativa = nome
                        st.rerun()
    
    with tabs[1]:
        with st.form("form_novo_concurso"):
            nome_concurso = st.text_input("Nome do Concurso")
            cargo_concurso = st.text_input("Cargo")
            if st.form_submit_button("🚀 INICIAR MISSÃO"):
                if nome_concurso and cargo_concurso:
                    supabase.table("editais_materias").insert({"concurso": nome_concurso, "cargo": cargo_concurso, "materia": "Geral", "topicos": ["Introdução"]}).execute()
                    st.session_state.missao_ativa = nome_concurso
                    st.rerun()

else:
    missao = st.session_state.missao_ativa
    res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res.data)
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"<h2 style='color:#FF4B4B;'>{missao}</h2>", unsafe_allow_html=True)
        if st.button("← Voltar à Central", use_container_width=True): 
            st.session_state.missao_ativa = None
            st.rerun()
        menu = option_menu(None, ["Revisões", "Registrar", "Foco", "Dashboard", "Histórico", "Configurar"], 
                           icons=["arrow-repeat", "pencil-square", "clock", "grid", "list", "gear"], default_index=0)

    # --- ABA: REVISÕES ---
    if menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                if not row.get('rev_24h', False):
                    dt_prev = dt_est + timedelta(days=1)
                    if dt_prev <= hoje:
                        pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "data_prevista": dt_prev})
        
        if not pend: st.success("✨ Tudo em dia!")
        else:
            for p in pend:
                with st.container():
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    st.write(f"**{p['materia']}** - {p['assunto']} ({p['tipo']})")
                    if st.button("CONCLUIR", key=f"btn_{p['id']}_{p['col']}"):
                        supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute()
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: REGISTRAR ---
    elif menu == "Registrar":
        st.markdown('<h2 class="main-title">📝 Novo Registro</h2>', unsafe_allow_html=True)
        mats = list(dados.get('materias', {}).keys())
        with st.form("form_registro"):
            mat_reg = st.selectbox("Disciplina", mats if mats else ["Nenhuma"])
            ac_reg = st.number_input("Acertos", 0)
            to_reg = st.number_input("Total", 1)
            if st.form_submit_button("💾 SALVAR"):
                payload = {"concurso": missao, "materia": mat_reg, "acertos": ac_reg, "total": to_reg, "taxa": (ac_reg/to_reg*100), "data_estudo": str(datetime.date.today())}
                supabase.table("registros_estudos").insert(payload).execute()
                st.rerun()

    # --- ABA: FOCO ---
    elif menu == "Foco":
        st.markdown('<h2 class="main-title">⏱️ Pomodoro</h2>', unsafe_allow_html=True)
        mins, secs = divmod(st.session_state.pomodoro_seconds, 60)
        st.markdown(f'<div class="timer-display">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        if st.button("▶️ INICIAR" if not st.session_state.pomodoro_active else "⏸️ PAUSAR"):
            st.session_state.pomodoro_active = not st.session_state.pomodoro_active
        if st.session_state.pomodoro_active and st.session_state.pomodoro_seconds > 0:
            time.sleep(1)
            st.session_state.pomodoro_seconds -= 1
            st.rerun()

    # --- ABA: DASHBOARD (Integração com Notion Aqui) ---
    elif menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        # Chamada em tempo real para o Notion
        erros_no_notion = get_notion_errors_count()
        
        if df.empty:
            st.info("Sem dados suficientes.")
        else:
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q>0 else 0)
            
            # 4 Colunas para incluir a métrica do Notion
            m1, m2, m3, m4 = st.columns(4)
            with m1: render_metric_card("Questões Totais", int(t_q), "📝")
            with m2: render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
            with m3: render_metric_card("Erros no Notion", erros_no_notion, "🔥") # NOVIDADE
            with m4: render_metric_card("Horas", f"{df['tempo'].sum()/60:.1f}h", "⏱️")

    # --- ABA: HISTÓRICO ---
    elif menu == "Histórico":
        st.markdown('<h2 class="main-title">📜 Histórico</h2>', unsafe_allow_html=True)
        st.table(df[['data_estudo', 'materia', 'acertos', 'total', 'taxa']] if not df.empty else pd.DataFrame())

    # --- ABA: CONFIGURAR ---
    elif menu == "Configurar":
        st.markdown('<h2 class="main-title">⚙️ Configurações</h2>', unsafe_allow_html=True)
        st.write("Gerencie suas disciplinas e tópicos aqui.")
