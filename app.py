import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

# CSS para Conforto Visual (Fundo Suave e Cards Brancos)
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-grafico { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e9ecef; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #e9ecef !important; background-color: #ffffff !important; border-radius: 10px !important; margin-bottom: 10px !important; }
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
    
    with tabs[0]:
        ed = get_editais(supabase)
        if not ed: st.info("Nenhum concurso cadastrado.")
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 0.5])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()
                if c3.button("🗑️", key=f"del_{nome}"):
                    if excluir_concurso_completo(supabase, nome): st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro de Nova Missão")
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
    except:
        df = pd.DataFrame()
        
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["grid", "arrow-repeat", "pencil", "gear", "list"], default_index=0)

    # --- ABA DASHBOARD (v138.0 - CLEAN & PRO) ---
    if menu == "Dashboard":
        if df.empty:
            st.info("Aguardando dados para análise...")
        else:
            c_menu, c_conteudo = st.columns([0.15, 2.5])
            with c_menu:
                sub_aba = option_menu(None, ["Geral", "Evolução", "Matérias"], icons=["house", "activity", "layers"], default_index=0,
                    styles={"container": {"padding": "0!important", "background-color": "transparent"}, "nav-link": {"font-size": "0px", "margin":"15px 0px"}})

            with c_conteudo:
                df['minutos'] = df['tempo'].apply(lambda x: int(x.split(':')[0])*60 + int(x.split(':')[1]) if (isinstance(x, str) and ':' in x) else 0)

                if sub_aba == "Geral":
                    st.markdown("### 🎯 Resumo de Performance")
                    k1, k2, k3, k4 = st.columns(4)
                    tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
                    k1.metric("Questões", int(tot_q))
                    k2.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
                    k3.metric("Matérias", len(df['materia'].unique()))
                    k4.metric("Horas", f"{(df['minutos'].sum()/60):.1f}h")
                    
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("<div class='card-grafico'><strong>Distribuição de Questões</strong>", unsafe_allow_html=True)
                        st.plotly_chart(px.pie(df, values='total', names='materia', hole=0.6, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown("<div class='card-grafico'><strong>Mapa de Competências</strong>", unsafe_allow_html=True)
                        df_r = df.groupby('materia')['taxa'].mean().reset_index()
                        fig_r = px.line_polar(df_r, r='taxa', theta='materia', line_close=True)
                        fig_r.update_traces(fill='toself', line_color='#ff4b4b', fillcolor='rgba(255, 75, 75, 0.1)')
                        st.plotly_chart(fig_r, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                elif sub_aba == "Evolução":
                    st.markdown("### 📈 Evolução do Estudante")
                    df_ev = df.groupby('data_estudo').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index().sort_values('data_estudo')
                    st.plotly_chart(px.area(df_ev, x='data_estudo', y=['total', 'acertos'], color_discrete_map={"total": "#e9ecef", "acertos": "#ff4b4b"}), use_container_width=True)

                elif sub_aba == "Matérias":
                    st.markdown("### 📚 Detalhamento por Assunto")
                    df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                    for _, m in df_mat.iterrows():
                        with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                            st.markdown(f'<div style="width: 100%; background-color: #f1f3f5; border-radius: 10px; height: 6px; margin-bottom: 20px;"><div style="width: {m["taxa"]}%; background-color: #37b24d; border-radius: 10px; height: 6px;"></div></div>', unsafe_allow_html=True)
                            df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
                            for _, a in df_ass.iterrows():
                                c1, c2 = st.columns([3, 1])
                                c1.markdown(f"<span style='font-size: 14px; color: #495057;'>└ {a['assunto']}</span>", unsafe_allow_html=True)
                                c2.markdown(f"<p style='text-align: right; color: #adb5bd; font-size: 12px;'>{int(a['acertos'])}/{int(a['total'])} ({a['taxa']:.0f}%)</p>", unsafe_allow_html=True)
                                st.markdown(f'<div style="width: 100%; background-color: #f8f9fa; border-radius: 10px; height: 4px; margin-bottom: 12px;"><div style="width: {a["taxa"]}%; background-color: #74c0fc; border-radius: 10px; height: 4px;"></div></div>', unsafe_allow_html=True)

    # --- ABA REVISÕES (BLINDADA) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões (Modo Pós-Edital)")
        if df.empty: st.info("Sem registros para revisar.")
        else:
            hoje = datetime.date.today()
            pend = []
            cores = {"Revisão 24h": "blue", "Revisão 7d": "orange", "Revisão 15d": "purple", "Revisão 20d": "green"}
            for _, row in df.iterrows():
                dt = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt).days
                tx = row.get('taxa', 0)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row.get('comentarios', '')})
                if row.get('rev_24h', False):
                    if tx <= 75: d, col, lbl = 7, "rev_07d", "Revisão 7d"
                    elif 76 <= tx <= 79: d, col, lbl = 15, "rev_15d", "Revisão 15d"
                    else: d, col, lbl = 20, "rev_30d", "Revisão 20d"
                    if dias >= d and not row.get(col, False):
                        pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": lbl, "col": col, "atraso": dias-d, "c": row.get('comentarios', '')})
            
            if not pend: st.success("✅ Tudo revisado!")
            else:
                for p in pend:
                    with st.container(border=True):
                        ci, ca = st.columns([1.8, 1])
                        with ci:
                            st.markdown(f"### {p['materia']}\n**{p['assunto']}**\n\n:{cores.get(p['tipo'], 'grey')}[**{p['tipo']}**]")
                            if p['c']: 
                                with st.expander("🔗 Ver Links/Anotações"): st.write(p['c'])
                        with ca:
                            st.write(""); c_ac, c_to = st.columns(2)
                            acr = c_ac.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['col']}")
                            tor = c_to.number_input("Total", 0, key=f"to_{p['id']}_{p['col']}")
                            if st.button("CONCLUIR", key=f"b_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                                txr = (acr/tor*100) if tor > 0 else 0
                                nc = f"{p['c']} | {p['tipo']}: {acr}/{tor} ({txr:.1f}%)".strip(" | ")
                                supabase.table("registros_estudos").update({p['col']: True, "comentarios": nc}).eq("id", p['id']).execute(); st.rerun()
                            if p['atraso'] > 0: st.error(f"⚠️ {p['atraso']}d de atraso")

    # --- ABA REGISTRAR (BLINDADA) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro em Configurar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                tb = c2.text_input("Tempo (HHMM)", placeholder="0130")
                tf = formatar_tempo_estudo(tb); st.info(f"Tempo: **{tf}**")
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2); ac = ca.number_input("Acertos", 0); to = ct.number_input("Total", 1)
                com = st.text_area("Comentários (Links TEC)")
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": to, "taxa": (ac/to*100), "comentarios": str(com), "tempo": str(tf), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute(); st.success("Salvo!"); time.sleep(0.5); st.rerun()

    # --- ABA HISTÓRICO (BLINDADA) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            dfh = df.copy(); dfh['data_estudo'] = pd.to_datetime(dfh['data_estudo']).dt.strftime('%d/%m/%Y'); dfh['id'] = dfh['id'].astype(str); dfh['taxa'] = pd.to_numeric(dfh['taxa'], errors='coerce').fillna(0).astype(float)
            st.divider(); k1, k2, k3 = st.columns(3); k1.metric("Questões", int(dfh['total'].sum())); k2.metric("Precisão", f"{dfh['taxa'].mean():.1f}%"); k3.metric("Lançamentos", len(dfh)); st.divider()
            cols = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']
            ed = st.data_editor(dfh[cols], hide_index=True, use_container_width=True, column_config={"taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%")})
            cs, cd = st.columns([4, 1])
            if cs.button("💾 SALVAR ALTERAÇÕES", use_container_width=True):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso, "tempo": r['tempo'], "comentarios": r['comentarios'], "taxa": (r['acertos']/r['total']*100)}).eq("id", r['id']).execute(); st.rerun()
            with cd.popover("🗑️"):
                id_del = st.text_input("ID p/ apagar")
                if st.button("CONFIRMAR"): supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()

    # --- ABA CONFIGURAR (BLINDADA) ---
    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        with st.form("add_m"):
            nm = st.text_input("Nova Disciplina")
            if st.form_submit_button("➕ ADICIONAR"):
                if nm: supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos (um por linha)", value="\n".join(t), key=f"tx_{m}")
                    if st.button("💾 SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]; supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                    if st.button("🗑️ EXCLUIR DISCIPLINA", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()
