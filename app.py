import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# --- 1. DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
    .stMetric, .card-dashboard, div[data-testid="stExpander"] {
        background-color: #1A1C23 !important;
        border: 1px solid #2D303E !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    .progress-container { width: 100%; background-color: #FF4B4B; border-radius: 4px; height: 6px; margin: 8px 0; overflow: hidden; }
    .progress-bar-fill { background-color: #00FF00; height: 100%; }
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
                           default_index=0)

    # --- ABA: REGISTRAR (CORREÇÃO DE TÓPICOS TRAVADOS) ---
    if menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            # Container de formulário para garantir esquadro
            with st.container(border=True):
                c_data, c_tempo = st.columns([2, 1])
                data_est = c_data.date_input("Data", format="DD/MM/YYYY")
                tempo_raw = c_tempo.text_input("Tempo (HHMM)", value="0100")
                
                # 1. Seleção da Disciplina
                mat_sel = st.selectbox("Disciplina", mats)
                
                # 2. Seleção do Tópico (KEY DINÂMICA PARA NÃO TRAVAR)
                lista_topicos = dados['materias'].get(mat_sel, ["Geral"])
                top_sel = st.selectbox("Tópico/Assunto", lista_topicos, key=f"topico_{mat_sel}") #
                
                c_ac, c_to = st.columns(2)
                acr = c_ac.number_input("Acertos", min_value=0, value=20)
                tot = c_to.number_input("Total", min_value=1, value=25)
                
                coment = st.text_area("Comentários (Links TEC/Anotações)", placeholder="teste")
                
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    try:
                        t_big = formatar_tempo_para_bigint(tempo_raw)
                        payload = {
                            "concurso": missao, "materia": mat_sel, "assunto": top_sel,
                            "data_estudo": data_est.strftime('%Y-%m-%d'), "acertos": int(acr),
                            "total": int(tot), "taxa": float((acr/tot)*100), "comentarios": str(coment),
                            "tempo": t_big, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }
                        supabase.table("registros_estudos").insert(payload).execute()
                        st.success("Salvo!") #
                        time.sleep(0.5); st.rerun()
                    except: st.error("Erro ao salvar.")

    # --- ABA: REVISÕES (COM SINCRONIZAÇÃO E ANOTAÇÕES) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias_desde = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                if dias_desde >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias_desde-1, "coment": row.get('comentarios', '')})
        
        if not pend: st.success("✅ Tudo revisado!")
        else:
            for p in pend:
                with st.container(border=True):
                    c_t, c_v, c_b = st.columns([1.5, 1, 0.8])
                    with c_t:
                        st.markdown(f"**{p['materia']}**\n\n<span class='small-text'>{p['assunto']}</span>", unsafe_allow_html=True)
                        if p['coment']: 
                            with st.expander("📝 Ver Anotações"): st.info(p['coment']) #
                    with c_v:
                        ca, ct = st.columns(2)
                        r_ac = ca.number_input("Acertos", 0, key=f"ac_{p['id']}")
                        r_to = ct.number_input("Total", 0, key=f"to_{p['id']}")
                    with c_b:
                        st.write("")
                        if p['atraso'] > 0: st.markdown(f"<p style='color:#FF4B4B;font-size:12px;text-align:center;'>⚠️ {p['atraso']}d atraso</p>", unsafe_allow_html=True) #
                        if st.button("CONCLUIR", key=f"btn_{p['id']}", use_container_width=True, type="primary"):
                            try:
                                res_db = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                                n_ac = res_db.data[0]['acertos'] + r_ac
                                n_to = res_db.data[0]['total'] + r_to
                                supabase.table("registros_estudos").update({p['col']: True, "comentarios": f"{p['coment']} | Rev: {r_ac}/{r_to}", "acertos": n_ac, "total": n_to, "taxa": (n_ac/n_to*100)}).eq("id", p['id']).execute()
                                st.success("Sincronizado!"); time.sleep(0.5); st.rerun() #
                            except: st.error("Erro.")

    # --- DEMAIS ABAS (DASHBOARD, HISTÓRICO, CONFIGURAR) ---
    elif menu == "Dashboard":
        if df.empty: st.info("Sem dados.")
        else:
            k1, k2, k3 = st.columns(3)
            k1.metric("Questões", int(df['total'].sum()))
            k2.metric("Precisão", f"{df['taxa'].mean():.1f}%")
            k3.metric("Horas", f"{(df['tempo'].sum()/60):.1f}h")
            st.divider()
            df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index()
            for _, m in df_mat.iterrows():
                with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                    df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'taxa': 'mean'}).reset_index()
                    for _, a in df_ass.iterrows():
                        st.markdown(f"<span class='small-text'>└ {a['assunto']}</span>", unsafe_allow_html=True)
                        st.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width: {a["taxa"]}%;"></div></div>', unsafe_allow_html=True) #

    elif menu == "Configurar":
        st.subheader("⚙️ Configurações")
        with st.form("add_mat"):
            nm = st.text_input("Nova Matéria")
            if st.form_submit_button("ADD"):
                supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos", value="\n".join(t), key=f"tx_{m}")
                    if st.button("SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if not df.empty:
            df_h = df.copy(); df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.data_editor(df_h[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], use_container_width=True, hide_index=True)
