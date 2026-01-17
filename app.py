import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
from streamlit_option_menu import option_menu

# Importação dos Módulos Independentes
from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

# --- 1. INICIALIZAÇÃO ---
apply_styles()

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# --- 2. FLUXO TELA INICIAL: CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    
    with tabs[0]:
        ed = get_editais(supabase)
        if not ed: 
            st.info("Nenhum concurso cadastrado.")
        
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 0.5])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()
                
                if c3.button("🗑️", key=f"del_btn_{nome}", help="Excluir este concurso"):
                    st.session_state[f"confirm_del_{nome}"] = True

                # Trava de Segurança (Confirmação)
                if st.session_state.get(f"confirm_del_{nome}", False):
                    st.warning(f"Excluir **{nome}** e todo o seu histórico?")
                    col_sim, col_nao = st.columns(2)
                    
                    if col_sim.button("✅ SIM", key=f"yes_{nome}"):
                        if excluir_concurso_completo(supabase, nome):
                            st.success("Removido!")
                            time.sleep(0.5)
                            del st.session_state[f"confirm_del_{nome}"]
                            st.rerun()
                    
                    if col_nao.button("❌ NÃO", key=f"no_{nome}"):
                        del st.session_state[f"confirm_del_{nome}"]
                        st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro de Nova Missão")
        with st.form("form_novo"):
            n_n = st.text_input("Nome do Concurso")
            n_c = st.text_input("Cargo")
            if st.form_submit_button("CRIAR MISSÃO"):
                if n_n:
                    supabase.table("editais_materias").insert({
                        "concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []
                    }).execute()
                    st.success("Missão Criada!")
                    time.sleep(0.8); st.rerun()

# --- 3. FLUXO INTERNO: PAINEL DE ESTUDOS ---
else:
    missao = st.session_state.missao_ativa
    res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res.data)
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR À CENTRAL"):
            st.session_state.missao_ativa = None
            st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], 
                           default_index=2)

    if menu == "Dashboard":
        st.subheader("📊 Performance")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            c1, c2 = st.columns(2)
            c1.metric("Questões Totais", int(tot))
            c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            
            df_g = df.copy(); df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            st.plotly_chart(px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), 
                                    x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626']), use_container_width=True)

    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        df_p = calcular_pendencias(df)
        if df_p.empty: st.success("✅ Tudo revisado!")
        else:
            for _, row in df_p.iterrows():
                with st.container(border=True):
                    st.write(f"**{row['Label']}** - {row['Mat']}")
                    st.caption(row['Ass'])
                    if st.button("Concluir Revisão", key=f"rev_{row['id']}_{row['Fase']}"):
                        supabase.table("registros_estudos").update({f"rev_{row['Fase']}": True}).eq("id", row['id']).execute()
                        st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Novo Registro de Estudo")
        mats = list(dados.get('materias', {}).keys())
        if not mats:
            st.warning("Cadastre matérias no menu Configurar primeiro.")
        else:
            with st.container(border=True):
                # CABEÇALHO: DATA E TEMPO
                c_data, c_tempo = st.columns([2, 1])
                with c_data:
                    data_sel = st.radio("Data do Estudo", ["HOJE", "ONTEM", "OUTRO"], horizontal=True)
                    if data_sel == "HOJE": dt = datetime.date.today()
                    elif data_sel == "ONTEM": dt = datetime.date.today() - datetime.timedelta(days=1)
                    else: dt = st.date_input("Data", datetime.date.today())
                
                with c_tempo:
                    tempo_estudo = st.text_input("Tempo (HH:MM:SS)", value="01:00:00")

                st.divider()
                # SELEÇÃO DE MATÉRIA
                c1, c2 = st.columns(2)
                mat = c1.selectbox("Disciplina", mats)
                ass = c2.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))

                st.divider()
                # PERFORMANCE: QUESTÕES, PÁGINAS E VÍDEOS
                col_q, col_p, col_v = st.columns(3)
                with col_q:
                    st.markdown("#### 🎯 Questões")
                    acertos = st.number_input("Acertos", min_value=0, value=0)
                    total_q = st.number_input("Total", min_value=0, value=0)
                with col_p:
                    st.markdown("#### 📖 Páginas")
                    p_ini = st.number_input("Início", min_value=0, value=0)
                    p_fim = st.number_input("Fim", min_value=0, value=0)
                with col_v:
                    st.markdown("#### 🎬 Videoaula")
                    v_tit = st.text_input("Título/ID", value="Aula 01")
                    v_dur = st.text_input("Duração", value="00:30:00")

                st.divider()
                coment = st.text_area("Comentários / Anotações")
                
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    taxa = (acertos/total_q*100) if total_q > 0 else 0
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": acertos, "total": total_q, 
                        "taxa": taxa, "comentarios": coment, "paginas": f"{p_ini}-{p_fim}",
                        "videoaula": v_tit, "tempo": tempo_estudo,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("Registrado!")
                    time.sleep(1); st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Adicionar"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos", "\n".join(t), key=f"t_{m}", height=150)
                if st.button("Salvar", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Vazio.")
        else:
            ed = st.data_editor(df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']], hide_index=True)
            if st.button("💾 ATUALIZAR"):
                for _, r in ed.iterrows():
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "taxa": (r['acertos']/r['total']*100) if r['total']>0 else 0}).eq("id", r['id']).execute()
                st.rerun()
