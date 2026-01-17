import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
from database import supabase
from logic import get_editais, calcular_pendencias
from styles import apply_styles

# --- INICIALIZAÇÃO ---
apply_styles()
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

# --- CENTRAL DE COMANDO (TELA INICIAL) ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    
    with tabs[0]:
        ed = get_editais(supabase)
        if not ed: st.info("Nenhum concurso cadastrado.")
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro Manual de Edital")
        with st.form("form_novo"):
            n_n = st.text_input("Nome do Concurso")
            n_c = st.text_input("Cargo")
            if st.form_submit_button("CRIAR MISSÃO"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.success("Concurso criado!"); time.sleep(1); st.rerun()

# --- PAINEL DE MISSÃO ---
else:
    missao = st.session_state.missao_ativa
    res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res.data)
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], 
                           default_index=2)

    if menu == "Dashboard":
        st.subheader("📊 Performance Geral")
        if df.empty: st.info("Sem dados para exibir.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", int(tot))
            c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            hrs = (df['tempo'].sum()/60) if 'tempo' in df.columns else 0
            c3.metric("Tempo", f"{int(hrs)}h")
            
            df_g = df.copy()
            df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            fig = px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), 
                          x='Data', y=['total', 'acertos'], 
                          color_discrete_sequence=['#2D2D35', '#DC2626'], height=350)
            st.plotly_chart(fig, use_container_width=True)

    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        df_p = calcular_pendencias(df)
        if df_p.empty: st.success("✅ Tudo revisado!")
        else:
            cols = st.columns(4); fases = [("24h", "🔥 D1"), ("07d", "📅 D7"), ("15d", "🧠 D15"), ("30d", "💎 D30")]
            for i, (fid, flabel) in enumerate(fases):
                with cols[i]:
                    st.markdown(f"#### {flabel}")
                    itens = df_p[df_p['Fase'] == fid]
                    for _, row in itens.iterrows():
                        st.markdown(f'''<div class="rev-card {row["CSS"]}">
                            <div style="font-weight:800;font-size:0.85rem;color:#FFF;">{row["Mat"]}</div>
                            <div style="font-size:0.75rem;color:#94A3B8;">{row["Ass"]}</div>
                            <div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-top:5px;">
                                <span>📅 {row["Data"]}</span><span class="score-badge">{row["Taxa"]:.0f}%</span>
                            </div></div>''', unsafe_allow_html=True)
                        if st.button("Ok", key=f"f_{row['id']}_{fid}"):
                            supabase.table("registros_estudos").update({f"rev_{fid}": True}).eq("id", row['id']).execute(); st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Registrar Questões")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                mat = c1.selectbox("Matéria", mats)
                ass = c1.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
                dt = c2.date_input("Data", datetime.date.today())
                st.divider()
                ac = st.number_input("Acertos", 0); tot = st.number_input("Total", 1)
                t1, t2 = st.columns(2); h = t1.selectbox("H", range(13)); m = t2.selectbox("M", range(60))
                if st.button("💾 SALVAR REGISTRO", type="primary"):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100), "tempo": (h*60+m),
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Edital")
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
        if df.empty: st.info("Sem registros.")
        else:
            ed = st.data_editor(df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total']], hide_index=True)
            if st.button("💾 ATUALIZAR"):
                for _, r in ed.iterrows():
                    tx = (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "taxa": tx}).eq("id", r['id']).execute()
                st.rerun()
