import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE TEMA (MODO ESCURO FIXO E SEGURO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

# CSS FIXO: Garante legibilidade sem "blocos brancos"
st.markdown("""
    <style>
    .stMetric { background-color: #1E2129 !important; border: 1px solid #31333F !important; border-radius: 12px; padding: 15px; }
    div[data-testid="stExpander"] { background-color: #1E2129 !important; border: 1px solid #31333F !important; }
    .card-dashboard { background-color: #1E2129; border: 1px solid #31333F; padding: 20px; border-radius: 15px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# Função de tempo robusta para evitar erros no Supabase
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto).zfill(4)
    horas = numeros[:-2].zfill(2)
    minutos = numeros[-2:].zfill(2)
    return f"{horas}:{minutos}:00"

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

    # --- ABA DASHBOARD ---
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
                    k1.metric("Questões", int(tot_q)); k2.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
                    k3.metric("Matérias", len(df['materia'].unique())); k4.metric("Sessões", len(df))
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        fig_p = px.pie(df, values='total', names='materia', hole=0.5, template="plotly_dark")
                        st.plotly_chart(fig_p, use_container_width=True)
                    with col2:
                        df_r = df.groupby('materia')['taxa'].mean().reset_index()
                        fig_r = px.line_polar(df_r, r='taxa', theta='materia', line_close=True, template="plotly_dark")
                        st.plotly_chart(fig_r, use_container_width=True)

                elif sub_aba == "Matérias":
                    st.markdown("### 📚 Detalhes por Assunto")
                    df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                    for _, m in df_mat.iterrows():
                        with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                            df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                            for _, a in df_ass.iterrows():
                                c1, c2 = st.columns([3, 1])
                                c1.markdown(f"└ {a['assunto']}")
                                c2.markdown(f"**{a['taxa']:.0f}**% ({int(a['acertos'])}/{int(a['total'])})")
                                st.progress(a['taxa']/100)

    # --- ABA REVISÕES (DIAS DE ATRASO RESTAURADOS) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões (Modo Pós-Edital)")
        hoje = datetime.date.today()
        pend = []
        cores = {"Revisão 24h": "blue", "Revisão 7d": "orange", "Revisão 15d": "purple", "Revisão 20d": "green"}
        
        for _, row in df.iterrows():
            dt = pd.to_datetime(row['data_estudo']).date()
            dias = (hoje - dt).days
            tx = row.get('taxa', 0)
            
            # Regra de 24h
            if dias >= 1 and not row.get('rev_24h', False):
                pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row.get('comentarios', '')})
            
            # Regra de Desempenho (Pós-24h)
            if row.get('rev_24h', False):
                if tx <= 75: d, col, lbl = 7, "rev_07d", "Revisão 7d"
                elif 76 <= tx <= 79: d, col, lbl = 15, "rev_15d", "Revisão 15d"
                else: d, col, lbl = 20, "rev_30d", "Revisão 20d"
                
                if dias >= d and not row.get(col, False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": lbl, "col": col, "atraso": dias-d, "c": row.get('comentarios', '')})

        if not pend: st.success("✅ Tudo em dia!")
        else:
            for p in pend:
                with st.container(border=True):
                    c_info, c_action = st.columns([1.8, 1])
                    with c_info:
                        st.markdown(f"### {p['materia']}")
                        st.markdown(f"**Assunto:** {p['assunto']}")
                        st.markdown(f":{cores.get(p['tipo'], 'grey')}[**{p['tipo']}**]")
                        if p['c']: 
                            with st.expander("🔗 Ver Links/Anotações"): st.write(p['c'])
                    with c_action:
                        st.write("")
                        ca, ct = st.columns(2)
                        acr = ca.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['tipo']}")
                        tor = ct.number_input("Total", 0, key=f"to_{p['id']}_{p['tipo']}")
                        if st.button("CONCLUIR", key=f"btn_{p['id']}_{p['tipo']}", use_container_width=True, type="primary"):
                            supabase.table("registros_estudos").update({p['col']: True, "comentarios": f"{p['c']} | {p['tipo']}: {acr}/{tor}"}).eq("id", p['id']).execute()
                            st.rerun()
                        if p['atraso'] > 0: st.error(f"⚠️ {p['atraso']} dias de atraso")
                        else: st.success("🟢 No prazo")

    # --- ABA REGISTRAR (DATA FORMATO DD/MM/AAAA RESTAURADO) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro.")
        else:
            with st.container(border=True):
                c_date, c_time = st.columns([2, 1])
                # Formato DD/MM/YYYY na interface
                dt = c_date.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                tb = c_time.text_input("Tempo (HHMM)", value="0130")
                mat = st.selectbox("Disciplina", mats)
                ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2)
                ac = ca.number_input("Acertos", 0)
                to = ct.number_input("Total", 1)
                com = st.text_area("Comentários (Links TEC)")
                
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    t_formatado = formatar_tempo_estudo(tb)
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": to, 
                        "taxa": (ac/to*100), "comentarios": str(com), "tempo": t_formatado,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("✅ REGISTRO SALVO!"); time.sleep(0.5); st.rerun()

    # --- ABA HISTÓRICO (RESTAURADA TOTALMENTE) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty: st.info("Nenhum registro encontrado.")
        else:
            dfh = df.copy()
            dfh['data_estudo'] = pd.to_datetime(dfh['data_estudo']).dt.strftime('%d/%m/%Y')
            dfh['id'] = dfh['id'].astype(str)
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Questões", int(dfh['total'].sum()))
            k2.metric("Lançamentos", len(dfh))
            k3.metric("Média Geral", f"{dfh['taxa'].mean():.1f}%")
            st.divider()
            st.data_editor(dfh[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], 
                           use_container_width=True, hide_index=True)
            with st.popover("🗑️ Apagar Registro"):
                id_del = st.text_input("Digite o ID")
                if st.button("CONFIRMAR EXCLUSÃO"):
                    supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()

    # --- ABA CONFIGURAR ---
    elif menu == "Configurar":
        st.subheader("⚙️ Estrutura do Edital")
        with st.form("add_m"):
            nm = st.text_input("Nova Disciplina")
            if st.form_submit_button("➕ ADICIONAR"):
                if nm: supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos", value="\n".join(t), key=f"tx_{m}")
                    if st.button("💾 SALVAR TÓPICOS", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
