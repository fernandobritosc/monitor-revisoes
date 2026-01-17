import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
from streamlit_option_menu import option_menu
from database import supabase
from logic import get_edit Pipais, calcular_pendencias
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
            n_n = st.text_input("Nome do Concurso (Ex: TJRJ)")
            n_c = st.text_input("Cargo (Ex: Técnico)")
            if st.form_submit_button("CRIAR MISSÃO"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.success("Concurso criado com sucesso!"); time.sleep(1); st.rerun()

# --- PAINEL DE MISSÃO (DENTRO DO CONCURSO) ---
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

    if menu == "Registrar":
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
                if st.button("💾 SALVAR REGISTRO", type="primary"):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute()
                    st.toast("Missão Registrada!"); time.sleep(0.5); st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        nm = st.text_input("Adicionar Matéria")
        if st.button("Add"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        
        st.info("Copie e cole seus tópicos abaixo. Um por linha.")
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos", "\n".join(t), key=f"t_{m}", height=200)
                c_s, c_d = st.columns([4, 1])
                if c_s.button("Salvar Matéria", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                if c_d.button("🗑️", key=f"d_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()
