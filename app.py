import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    .stMetric { background-color: #1A1C23 !important; border: 1px solid #2D303E !important; border-radius: 8px !important; padding: 15px !important; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700 !important; }
    .progress-container { width: 100%; background-color: #FF4B4B; border-radius: 4px; height: 6px; margin: 8px 0; overflow: hidden; }
    .progress-bar-fill { background-color: #00FF00; height: 100%; }
    .small-text { font-size: 13px; color: #adb5bd; }
    /* Estilo para a data no título */
    .date-label { font-size: 12px; color: #6c757d; font-weight: normal; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    return (int(numeros[:-2]) * 60) + int(numeros[-2:])

# --- 2. LOGICA DE NAVEGAÇÃO ---
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
                           default_index=0)

    # --- ABA: REVISÕES (DATA INCLUÍDA) ---
    if menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                # Lógica 24h (simplificada para o exemplo)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "data_f": dt_est.strftime('%d/%m/%Y'), "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "coment": row.get('comentarios', '')})
        
        if not pend: st.success("✅ Tudo em dia!")
        else:
            for p in pend:
                with st.container(border=True):
                    c_txt, c_vals, c_btn = st.columns([1.5, 1, 0.8])
                    with c_txt:
                        # DATA DO ESTUDO ADICIONADA AQUI
                        st.markdown(f"**{p['materia']}** <span class='date-label'>({p['data_f']})</span>", unsafe_allow_html=True)
                        st.markdown(f"<span class='small-text'>{p['assunto']} • {p['tipo']}</span>", unsafe_allow_html=True)
                        if p['coment']: 
                            with st.expander("📝 Ver Anotações"): st.info(p['coment'])
                    with c_vals:
                        ca, ct = st.columns(2)
                        r_ac = ca.number_input("Acertos", 0, key=f"rev_ac_{p['id']}")
                        r_to = ct.number_input("Total", 0, key=f"rev_to_{p['id']}")
                    with c_btn:
                        st.write("")
                        if p['atraso'] > 0: st.markdown(f"<p style='color:#FF4B4B;font-size:11px;text-align:center;'>⚠️ {p['atraso']}d atraso</p>", unsafe_allow_html=True)
                        if st.button("CONCLUIR", key=f"btn_{p['id']}", use_container_width=True, type="primary"):
                            res_db = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                            n_ac = res_db.data[0]['acertos'] + r_ac
                            n_to = res_db.data[0]['total'] + r_to
                            supabase.table("registros_estudos").update({p['col']: True, "acertos": n_ac, "total": n_to, "taxa": (n_ac/n_to*100 if n_to > 0 else 0)}).eq("id", p['id']).execute()
                            st.rerun()

    # --- ABA: REGISTRAR (SINC DINÂMICA) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            dt_reg = c1.date_input("Data", format="DD/MM/YYYY")
            tm_reg = c2.text_input("Tempo (HHMM)", value="0100")
            mat_reg = st.selectbox("Disciplina", mats)
            ass_reg = st.selectbox("Assunto", dados['materias'].get(mat_reg, ["Geral"]), key=f"sel_reg_{mat_reg}")
            ca_reg, ct_reg = st.columns(2)
            ac_reg = ca_reg.number_input("Acertos", 0)
            to_reg = ct_reg.number_input("Total", 1)
            com_reg = st.text_area("Comentários")
            if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                t_b = formatar_tempo_para_bigint(tm_reg)
                payload = {"concurso": missao, "materia": mat_reg, "assunto": ass_reg, "data_estudo": dt_reg.strftime('%Y-%m-%d'), "acertos": ac_reg, "total": to_reg, "taxa": (ac_reg/to_reg*100), "comentarios": com_reg, "tempo": t_b, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}
                supabase.table("registros_estudos").insert(payload).execute(); st.rerun()

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard":
        if df.empty: st.info("Sem dados.")
        else:
            k1, k2, k3 = st.columns(3)
            t_q, a_q = df['total'].sum(), df['acertos'].sum()
            k1.metric("Questões", int(t_q))
            k2.metric("Precisão", f"{(a_q/t_q*100 if t_q>0 else 0):.1f}%")
            k3.metric("Horas", f"{(df['tempo'].sum()/60):.1f}h")
            st.divider()
            df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index()
            for _, m in df_mat.iterrows():
                with st.expander(f"📁 {m['materia'].upper()}"):
                    df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'taxa': 'mean', 'total': 'sum', 'acertos': 'sum'}).reset_index()
                    for _, a in df_ass.iterrows():
                        c_a1, c_a2 = st.columns([3, 1])
                        c_a1.markdown(f"<span class='small-text'>└ {a['assunto']}</span>", unsafe_allow_html=True)
                        c_a2.markdown(f"<p style='text-align: right; font-size: 11px;'>{int(a['acertos'])}/{int(a['total'])}</p>", unsafe_allow_html=True)
                        st.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width: {a["taxa"]}%;"></div></div>', unsafe_allow_html=True)

    # --- ABAS SECUNDÁRIAS ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if not df.empty:
            df_h = df.copy(); df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.data_editor(df_h[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], use_container_width=True, hide_index=True)

    elif menu == "Configurar":
        st.subheader("⚙️ Edital")
        with st.form("add_mat"):
            nm = st.text_input("Nova Matéria")
            if st.form_submit_button("➕ ADD"):
                supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
