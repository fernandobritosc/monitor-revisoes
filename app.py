import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM PREMIUM ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    /* Alinhamento do Sub-menu lateral */
    [data-testid="column"]:nth-child(1) > div {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 15px !important;
    }
    
    /* Cards e Containers */
    .stMetric, .card-dashboard, div[data-testid="stExpander"] {
        background-color: #1A1C23 !important;
        border: 1px solid #2D303E !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }

    /* Barras Bicolores (Verde/Vermelho) */
    .progress-container {
        width: 100%;
        background-color: #FF4B4B; /* Erro */
        border-radius: 4px;
        height: 6px;
        margin: 8px 0;
        overflow: hidden;
    }
    .progress-bar-fill {
        background-color: #00FF00; /* Acerto */
        height: 100%;
    }
    
    .small-text { font-size: 13px; color: #adb5bd; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    return (int(numeros[:-2]) * 60) + int(numeros[-2:])

# --- 2. NAVEGAÇÃO CENTRAL ---
if st.session_state.missao_ativa is None:
    st.title("🎯 Central de Comando")
    ed = get_editais(supabase)
    tabs = st.tabs(["Missões Ativas", "Novo Cadastro"])
    with tabs[0]:
        for nome, d_concurso in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{nome}** — {d_concurso['cargo']}")
                if c2.button("Acessar", key=f"ac_{nome}", use_container_width=True):
                    st.session_state.missao_ativa = nome; st.rerun()
    with tabs[1]:
        with st.form("f_novo"):
            n_n, n_c = st.text_input("Nome do Concurso"), st.text_input("Cargo")
            if st.form_submit_button("CRIAR MISSÃO"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.rerun()

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
                           icons=["arrow-repeat", "pencil-square", "grid", "list", "gear"], 
                           default_index=0, styles={"nav-link": {"font-size": "14px", "padding": "10px"}})

    # --- ABA: DASHBOARD (v150.0 - LIMPO) ---
    if menu == "Dashboard":
        if df.empty: st.info("Sem dados para análise.")
        else:
            c_side, c_main = st.columns([0.15, 2.5])
            with c_side:
                sub = option_menu(None, ["Geral", "Matérias"], icons=["house", "layers"], default_index=0, 
                                styles={"container": {"padding": "0!important", "background-color": "transparent"},
                                        "nav-link": {"font-size": "0px", "margin":"15px 0px"},
                                        "nav-link-selected": {"background-color": "#FF4B4B"}})
            with c_main:
                if sub == "Geral":
                    k1, k2, k3, k4 = st.columns(4)
                    tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
                    k1.metric("Questões", int(tot_q)); k2.metric("Acertos", int(acc_q))
                    k3.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
                    k4.metric("Horas", f"{(df['tempo'].sum()/60):.1f}h")
                    st.divider()
                    col_g1, col_g2 = st.columns(2)
                    with col_g1: st.plotly_chart(px.pie(df, values='total', names='materia', hole=0.5, template="plotly_dark"), use_container_width=True)
                    with col_g2:
                        df_r = df.groupby('materia')['taxa'].mean().reset_index()
                        fig_r = px.line_polar(df_r, r='taxa', theta='materia', line_close=True, template="plotly_dark")
                        st.plotly_chart(fig_r, use_container_width=True)
                else:
                    df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                    for _, m in df_mat.iterrows():
                        with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                            # BARRA MESTRA REMOVIDA AQUI PARA LIMPEZA VISUAL
                            df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                            for _, a in df_ass.iterrows():
                                c_a1, c_a2 = st.columns([3, 1])
                                c_a1.markdown(f"<span class='small-text'>└ {a['assunto']}</span>", unsafe_allow_html=True)
                                c_a2.markdown(f"<p style='text-align: right; font-size: 11px; color: #adb5bd;'>{int(a['acertos'])}/{int(a['total'])}</p>", unsafe_allow_html=True)
                                st.markdown(f'<div class="progress-container" style="margin-left:15px;"><div class="progress-bar-fill" style="width: {a["taxa"]}%;"></div></div>', unsafe_allow_html=True)

    # --- ABA: REVISÕES (MANTIDO COMPACTO) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row.get('comentarios', '')})
        
        if not pend: st.success("Tudo em dia!")
        else:
            for p in pend:
                with st.container(border=True):
                    c_txt, c_vals, c_btn = st.columns([1.5, 1, 0.8])
                    with c_txt:
                        st.markdown(f"**{p['materia']}**\n\n<span class='small-text'>{p['assunto']} • {p['tipo']}</span>", unsafe_allow_html=True)
                    with c_vals:
                        c_ac, c_to = st.columns(2)
                        acr = c_ac.number_input("Acertos", 0, key=f"ac_{p['id']}")
                        tor = c_to.number_input("Total", 0, key=f"to_{p['id']}")
                    with c_btn:
                        st.write("")
                        if st.button("CONCLUIR", key=f"btn_{p['id']}", use_container_width=True, type="primary"):
                            supabase.table("registros_estudos").update({p['col']: True, "comentarios": f"{p['c']} | {p['tipo']}: {acr}/{tor}"}).eq("id", p['id']).execute(); st.rerun()

    # --- ABAS: REGISTRAR, HISTÓRICO, CONFIGURAR (INALTERADAS) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.form("form_reg"):
                c1, c2, c3 = st.columns([1.5, 0.8, 1.5])
                dt = c1.date_input("Data", format="DD/MM/YYYY")
                tb = c2.text_input("Tempo (HHMM)", value="0100")
                mat = c3.selectbox("Disciplina", mats); ass = st.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2); ac = ca.number_input("Acertos", 0); to = ct.number_input("Total", 1)
                com = st.text_area("Comentários")
                if st.form_submit_button("💾 SALVAR", use_container_width=True):
                    try:
                        t_b = formatar_tempo_para_bigint(tb)
                        payload = {"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": to, "taxa": (ac/to*100), "comentarios": com, "tempo": t_b, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}
                        supabase.table("registros_estudos").insert(payload).execute(); st.success("Salvo!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        with st.form("add_mat"):
            nm = st.text_input("Nova Matéria")
            if st.form_submit_button("➕ ADICIONAR"):
                supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos", value="\n".join(t), key=f"tx_{m}")
                    c_s, c_d = st.columns(2)
                    if c_s.button("💾 SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                    if c_d.button("🗑️ EXCLUIR", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if not df.empty:
            df_h = df.copy(); df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.data_editor(df_h[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], use_container_width=True, hide_index=True)
