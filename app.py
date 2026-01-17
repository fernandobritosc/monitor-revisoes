import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. GESTÃO DE TEMA E CONFIGURAÇÃO ---
if 'tema_escuro' not in st.session_state:
    st.session_state.tema_escuro = True  # Padrão é escuro

st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

# Ajuste Dinâmico de Cores baseado no Tema
t = {
    "bg": "#0E1117" if st.session_state.tema_escuro else "#F8F9FA",
    "card": "#1E2129" if st.session_state.tema_escuro else "#FFFFFF",
    "text": "#FFFFFF" if st.session_state.tema_escuro else "#212529",
    "border": "#31333F" if st.session_state.tema_escuro else "#DEE2E6"
}

st.markdown(f"""
    <style>
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
    .stMetric {{ 
        background-color: {t['card']} !important; 
        border: 1px solid {t['border']} !important; 
        border-radius: 12px; 
        padding: 15px;
    }}
    div[data-testid="stExpander"] {{
        background-color: {t['card']} !important;
        border: 1px solid {t['border']} !important;
    }}
    .card-dashboard {{
        background-color: {t['card']};
        border: 1px solid {t['border']};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
    }}
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto).zfill(4)
    return f"{numeros[:-2].zfill(2)}:{numeros[-2:].zfill(2)}:00"

# --- 2. CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    ed = get_editais(supabase)
    
    with tabs[0]:
        if not ed: st.info("Nenhum concurso cadastrado.")
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        with st.form("f_novo"):
            n_n, n_c = st.text_input("Nome"), st.text_input("Cargo")
            if st.form_submit_button("CRIAR"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.rerun()

# --- 3. PAINEL INTERNO ---
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

    # --- ABA DASHBOARD (v139.0 - CORRIGIDO) ---
    if menu == "Dashboard":
        if df.empty: st.info("Sem dados para análise.")
        else:
            c_menu, c_conteudo = st.columns([0.15, 2.5])
            with c_menu:
                sub_aba = option_menu(None, ["Geral", "Matérias"], icons=["house", "layers"], default_index=0,
                    styles={"container": {"padding": "0!important", "background-color": "transparent"}, "nav-link": {"font-size": "0px", "margin":"15px 0px"}})

            with c_conteudo:
                if sub_aba == "Geral":
                    st.markdown("### 🏠 Resumo de Performance")
                    k1, k2, k3, k4 = st.columns(4)
                    tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
                    k1.metric("Questões", int(tot_q))
                    k2.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
                    k3.metric("Matérias", len(df['materia'].unique()))
                    k4.metric("Sessões", len(df))
                    
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"<div class='card-dashboard'><strong>Distribuição</strong>", unsafe_allow_html=True)
                        fig_p = px.pie(df, values='total', names='materia', hole=0.5, template="plotly_dark" if st.session_state.tema_escuro else "plotly")
                        st.plotly_chart(fig_p, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='card-dashboard'><strong>Competências</strong>", unsafe_allow_html=True)
                        df_r = df.groupby('materia')['taxa'].mean().reset_index()
                        fig_r = px.line_polar(df_r, r='taxa', theta='materia', line_close=True, template="plotly_dark" if st.session_state.tema_escuro else "plotly")
                        st.plotly_chart(fig_r, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                elif sub_aba == "Matérias":
                    st.markdown("### 📚 Detalhes por Assunto")
                    df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                    for _, m in df_mat.iterrows():
                        with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                            df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                            for _, a in df_ass.iterrows():
                                c1, c2 = st.columns([3, 1])
                                c1.markdown(f"└ {a['assunto']}")
                                c2.markdown(f"**{a['taxa']:.0f}%** ({int(a['acertos'])}/{int(a['total'])})")
                                st.progress(a['taxa']/100)

    # --- ABA CONFIGURAR (MODO CLARO/ESCURO) ---
    elif menu == "Configurar":
        st.subheader("⚙️ Configurações do Sistema")
        
        # Opção de Tema
        st.write("---")
        st.write("**Personalização**")
        novo_tema = st.toggle("Modo Escuro Ativo", value=st.session_state.tema_escuro)
        if novo_tema != st.session_state.tema_escuro:
            st.session_state.tema_escuro = novo_tema
            st.rerun()
            
        st.write("---")
        st.write("**Estrutura do Edital**")
        with st.form("add_m"):
            nm = st.text_input("Nova Disciplina")
            if st.form_submit_button("➕ ADICIONAR"):
                if nm: supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos", value="\n".join(t), key=f"tx_{m}")
                    if st.button("💾 SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    # --- ABA REVISÕES (MANTIDA) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        for _, row in df.iterrows():
            dt = pd.to_datetime(row['data_estudo']).date()
            dias = (hoje - dt).days
            if dias >= 1 and not row.get('rev_24h', False):
                pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "c": row.get('comentarios', '')})
        if not pend: st.success("✅ Tudo revisado!")
        else:
            for p in pend:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    c1.markdown(f"### {p['materia']}\n**{p['assunto']}**")
                    acr = c2.number_input("Acertos", 0, key=f"ac_{p['id']}")
                    tor = c2.number_input("Total", 0, key=f"to_{p['id']}")
                    if c2.button("CONCLUIR", key=f"b_{p['id']}", type="primary"):
                        txr = (acr/tor*100) if tor > 0 else 0
                        supabase.table("registros_estudos").update({p['col']: True, "comentarios": f"{p['c']} | Rev: {acr}/{tor}"}).eq("id", p['id']).execute(); st.rerun()

    # --- ABA REGISTRAR (MANTIDA) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today())
                tb = c2.text_input("Tempo (HHMM)", placeholder="0130")
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2); ac = ca.number_input("Acertos", 0); to = ct.number_input("Total", 1)
                com = st.text_area("Comentários")
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": to, "taxa": (ac/to*100), "comentarios": str(com), "tempo": formatar_tempo_estudo(tb), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute(); st.rerun()

    # --- ABA HISTÓRICO (MANTIDA) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            dfh = df.copy(); dfh['data_estudo'] = pd.to_datetime(dfh['data_estudo']).dt.strftime('%d/%m/%Y'); dfh['id'] = dfh['id'].astype(str)
            st.data_editor(dfh[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo']], use_container_width=True, hide_index=True)
