import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE PÁGINA E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

# CSS Customizado para Refinamento Visual
st.markdown("""
    <style>
    /* Suavização de Fontes e Background */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #E0E0E0; }
    
    /* Metrics Compactas e Alinhadas */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; color: #FFFFFF; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #9E9E9E !important; }
    
    /* Cards de Revisão e Dashboard com Design Clean */
    .stMetric, .card-dashboard, div[data-testid="stExpander"] {
        background-color: #1A1C23 !important;
        border: 1px solid #2D303E !important;
        border-radius: 8px !important;
        padding: 12px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Ajuste de Espaçamento entre Colunas */
    [data-testid="column"] { padding: 0 10px !important; }
    
    /* Estilo para Títulos e Subtítulos */
    h3 { font-size: 1.2rem !important; font-weight: 600 !important; margin-bottom: 1rem !important; }
    
    /* Botões mais finos e elegantes */
    .stButton>button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    horas = int(numeros[:-2]); minutos = int(numeros[-2:])
    return (horas * 60) + minutos

# --- 2. LOGICA DE NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.title("🎯 Central de Comando")
    ed = get_editais(supabase)
    tabs = st.tabs(["Missões Ativas", "Novo Cadastro"])
    with tabs[0]:
        if not ed: st.info("Nenhuma missão ativa.")
        for nome, d_concurso in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{nome}** — {d_concurso['cargo']}")
                if c2.button("Acessar", key=f"ac_{nome}", use_container_width=True):
                    st.session_state.missao_ativa = nome; st.rerun()
else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"### {missao}")
        if st.button("← Voltar à Central", use_container_width=True): st.session_state.missao_ativa = None; st.rerun()
        st.write("---")
        menu = option_menu(None, ["Revisões", "Registrar", "Dashboard", "Histórico", "Configurar"], 
                           icons=["arrow-repeat", "pencil-square", "grid-3x3-gap", "list-ul", "gear"], 
                           default_index=0, styles={"nav-link": {"font-size": "14px", "text-align": "left", "margin":"0px"}})

    # --- ABA: REVISÕES (ALINHADO E COMPACTO) ---
    if menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row.get('comentarios', '')})
        
        if not pend: st.success("Tudo em dia!")
        else:
            for p in pend:
                with st.container(border=False):
                    st.markdown(f"<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                    c_info, c_atraso, c_btn = st.columns([3, 1, 1])
                    with c_info:
                        st.markdown(f"**{p['materia']}**")
                        st.markdown(f"<small style='color: #9E9E9E;'>{p['assunto']} • {p['tipo']}</small>", unsafe_allow_html=True)
                    with c_atraso:
                        if p['atraso'] > 0: st.markdown(f"<p style='color: #FF5252; font-size: 13px; margin-top: 10px;'>⚠️ {p['atraso']}d de atraso</p>", unsafe_allow_html=True)
                    with c_btn:
                        if st.button("CONCLUIR", key=f"r_{p['id']}", use_container_width=True, type="primary"):
                            supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute(); st.rerun()
                    st.divider()

    # --- ABA: REGISTRAR (ALINHAMENTO EM ESQUADRO) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Configure o edital primeiro.")
        else:
            with st.container(border=True):
                with st.form("reg_form", border=False):
                    c1, c2, c3 = st.columns([1.5, 1, 1.5])
                    dt = c1.date_input("Data", format="DD/MM/YYYY")
                    tb = c2.text_input("Tempo (HHMM)", value="0100")
                    mat = c3.selectbox("Disciplina", mats)
                    
                    ass = st.selectbox("Tópico/Assunto", dados['materias'].get(mat, ["Geral"]))
                    
                    c4, c5, c6 = st.columns([1, 1, 2])
                    ac = c4.number_input("Acertos", 0)
                    to = c5.number_input("Total", 1)
                    com = c6.text_input("Comentários / Links")
                    
                    if st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True):
                        try:
                            t_int = formatar_tempo_para_bigint(tb)
                            payload = {"concurso": str(missao), "materia": str(mat), "assunto": str(ass), "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": int(ac), "total": int(to), "taxa": float((ac/to)*100), "comentarios": str(com), "tempo": t_int, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}
                            supabase.table("registros_estudos").insert(payload).execute()
                            st.success("Salvo!"); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

    # --- ABA: DASHBOARD (VISUAL CLEAN) ---
    elif menu == "Dashboard":
        if df.empty: st.info("Sem dados.")
        else:
            st.markdown("### 📊 Performance")
            k1, k2, k3, k4 = st.columns(4)
            tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
            k1.metric("Questões", int(tot_q)); k2.metric("Acertos", int(acc_q))
            k3.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
            k4.metric("Horas", f"{(df['tempo'].sum()/60):.1f}h")
            
            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Distribuição por Matéria**")
                fig_p = px.pie(df, values='total', names='materia', hole=0.6, template="plotly_dark")
                fig_p.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)
            with c2:
                st.markdown("**Análise por Assunto**")
                df_mat = df.groupby('materia').agg({'taxa': 'mean', 'total': 'sum'}).reset_index()
                for _, m in df_mat.iterrows():
                    st.markdown(f"<small>{m['materia']} ({int(m['total'])} qts)</small>", unsafe_allow_html=True)
                    st.progress(m['taxa']/100)

    # --- ABA: HISTÓRICO E CONFIGURAR (MANTIDOS E ALINHADOS) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if not df.empty:
            df_h = df.copy(); df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.data_editor(df_h[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo']], use_container_width=True, hide_index=True)

    elif menu == "Configurar":
        st.subheader("⚙️ Configurações")
        with st.form("add_mat"):
            nm = st.text_input("Nova Matéria")
            if st.form_submit_button("Adicionar"):
                supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
