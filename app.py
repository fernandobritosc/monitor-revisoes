import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE TEMA (FIXO ESCURO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    .stMetric { background-color: #1E2129 !important; border: 1px solid #31333F !important; border-radius: 12px; padding: 15px; }
    div[data-testid="stExpander"] { background-color: #1E2129 !important; border: 1px solid #31333F !important; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# Função Blindada: Converte HHMM para minutos totais (Exigência do seu campo BIGINT)
def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    horas = int(numeros[:-2])
    minutos = int(numeros[-2:])
    return (horas * 60) + minutos

# --- 2. NAVEGAÇÃO CENTRAL ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    ed = get_editais(supabase)
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    with tabs[0]:
        if not ed: st.info("Sem missões cadastradas.")
        for nome, d_concurso in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{d_concurso['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
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
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["grid", "arrow-repeat", "pencil", "gear", "list"], default_index=0)

    # --- ABA DASHBOARD (RESTORED) ---
    if menu == "Dashboard":
        if df.empty: st.info("Sem dados para análise.")
        else:
            c_menu, c_conteudo = st.columns([0.15, 2.5])
            with c_menu:
                sub_aba = option_menu(None, ["Geral", "Matérias"], icons=["house", "layers"], default_index=0,
                    styles={"container": {"padding": "0!important", "background-color": "transparent"}, "nav-link": {"font-size": "0px", "margin":"15px 0px"}})

            with c_conteudo:
                if sub_aba == "Geral":
                    st.markdown("### 🏠 Resumo Geral")
                    k1, k2, k3, k4 = st.columns(4)
                    tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
                    k1.metric("Questões", int(tot_q)); k2.metric("Acertos", int(acc_q))
                    k3.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
                    k4.metric("Horas Totais", f"{(df['tempo'].sum()/60 if 'tempo' in df else 0):.1f}h")
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(px.pie(df, values='total', names='materia', hole=0.5, template="plotly_dark"), use_container_width=True)
                    with c2:
                        df_r = df.groupby('materia')['taxa'].mean().reset_index()
                        fig_r = px.line_polar(df_r, r='taxa', theta='materia', line_close=True, template="plotly_dark")
                        st.plotly_chart(fig_r, use_container_width=True)

                elif sub_aba == "Matérias":
                    st.markdown("### 📚 Detalhamento por Assunto")
                    df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                    for _, m in df_mat.iterrows():
                        with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                            df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                            for _, a in df_ass.iterrows():
                                c1, c2 = st.columns([3, 1])
                                c1.markdown(f"└ {a['assunto']}")
                                c2.markdown(f"**{a['taxa']:.0f}%** ({int(a['acertos'])}/{int(a['total'])})")
                                st.progress(a['taxa']/100)

    # --- ABA REVISÕES (RESTORED) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões (Modo Pós-Edital)")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row.get('comentarios', '')})
                if row.get('rev_24h', False):
                    d_alvo, col_alvo, lbl = (7, "rev_07d", "Revisão 7d") if tx <= 75 else (15, "rev_15d", "Revisão 15d") if tx <= 79 else (20, "rev_30d", "Revisão 20d")
                    if dias >= d_alvo and not row.get(col_alvo, False):
                        pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": lbl, "col": col_alvo, "atraso": dias-d_alvo, "c": row.get('comentarios', '')})

        if not pend: st.success("✅ Nada pendente!")
        else:
            for p in pend:
                with st.container(border=True):
                    ci, ca = st.columns([2, 1])
                    with ci:
                        st.markdown(f"### {p['materia']}\n**{p['assunto']}**\n{p['tipo']}")
                        if p['c']: 
                            with st.expander("🔗 Ver Links/Caderno"): st.write(p['c'])
                    with ca:
                        if st.button("CONCLUIR", key=f"r_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                            supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute(); st.rerun()
                        if p['atraso'] > 0: st.error(f"⚠️ {p['atraso']}d de atraso")

    # --- ABA REGISTRAR (CORRECTED) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.form("form_reg"):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                tb = c2.text_input("Tempo (HHMM)", value="0100")
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2); ac = ca.number_input("Acertos", 0); to = ct.number_input("Total", 1)
                com = st.text_area("Comentários (Links TEC)")
                if st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True):
                    try:
                        t_bigint = formatar_tempo_para_bigint(tb)
                        payload = {"concurso": str(missao), "materia": str(mat), "assunto": str(ass), "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": int(ac), "total": int(to), "taxa": float((ac/to)*100), "comentarios": str(com), "tempo": t_bigint, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}
                        supabase.table("registros_estudos").insert(payload).execute()
                        st.success("✅ Salvo!"); time.sleep(0.5); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    # --- ABA CONFIGURAR (RESTORED) ---
    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        with st.form("add_mat"):
            nm = st.text_input("Nome da Nova Disciplina")
            if st.form_submit_button("➕ ADICIONAR"):
                if nm: supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos (um por linha)", value="\n".join(t), key=f"tx_{m}")
                    c1, c2 = st.columns(2)
                    if c1.button("💾 SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                    if c2.button("🗑️ EXCLUIR", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    # --- ABA HISTÓRICO (RESTORED) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            df_h = df.copy(); df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y'); df_h['id'] = df_h['id'].astype(str)
            st.divider(); k1, k2 = st.columns(2); k1.metric("Questões", int(df_h['total'].sum())); k2.metric("Média", f"{df_h['taxa'].mean():.1f}%"); st.divider()
            st.data_editor(df_h[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], use_container_width=True, hide_index=True)
            with st.popover("🗑️ Apagar"):
                id_del = st.text_input("ID"); 
                if st.button("CONFIRMAR"): supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()
