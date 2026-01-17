import streamlit as st
import pandas as pd
import time
import plotly.express as px
from streamlit_option_menu import option_menu
from database import supabase
from logic import get_editais, calcular_pendencias

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="COMMANDER ELITE", page_icon="💀", layout="wide")
st.markdown("<style>body { background-color: #0A0A0B; color: #E2E8F0; }</style>", unsafe_allow_html=True) # Exemplo simples de CSS

# --- FLUXO PRINCIPAL ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões", "➕ Novo Edital"])
    
    with tabs[0]:
        ed = get_editais(supabase)
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro de Concurso")
        n_n = st.text_input("Nome")
        n_c = st.text_input("Cargo")
        if st.button("CRIAR") and n_n:
            supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
            st.success("Criado!"); time.sleep(1); st.rerun()

else:
    missao = st.session_state.missao_ativa
    res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res.data)
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear"], default_index=2)

    if menu == "Registrar":
        st.subheader("📝 Registrar")
        mats = list(dados.get('materias', {}).keys())
        if mats:
            mat = st.selectbox("Matéria", mats)
            ass = st.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
            ac = st.number_input("Acertos", 0); tot = st.number_input("Total", 1)
            if st.button("💾 SALVAR"):
                supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": str(datetime.date.today()), "acertos": ac, "total": tot, "taxa": (ac/tot*100)}).execute()
                st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Add"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos (um por linha)", "\n".join(t), key=f"t_{m}")
                if st.button("Salvar", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
