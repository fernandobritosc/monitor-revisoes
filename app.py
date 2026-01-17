import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
import re
from streamlit_option_menu import option_menu

# Importação dos Módulos Independentes
from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

# --- 1. INICIALIZAÇÃO ---
apply_styles()

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# FUNÇÃO: 0130 -> 01:30:00
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto) 
    if not numeros: return "00:00:00"
    numeros = numeros.zfill(4)
    horas = numeros[:-2].zfill(2)
    minutos = numeros[-2:].zfill(2)
    return f"{horas}:{minutos}:00"

# --- 2. TELA INICIAL: CENTRAL DE COMANDO ---
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
                    st.session_state[f"confirm_del_{nome}"] = True

                if st.session_state.get(f"confirm_del_{nome}", False):
                    st.warning(f"Excluir **{nome}**?")
                    cs, cn = st.columns(2)
                    if cs.button("✅ SIM", key=f"y_{nome}"):
                        if excluir_concurso_completo(supabase, nome):
                            st.toast("Removido!"); del st.session_state[f"confirm_del_{nome}"]; st.rerun()
                    if cn.button("❌ NÃO", key=f"n_{nome}"):
                        del st.session_state[f"confirm_del_{nome}"]; st.rerun()

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
    # Tenta buscar os dados reais
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()
        
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=4)

    # --- ABA HISTÓRICO COM VISUAL PREVENTIVO ---
    if menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        
        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado para esta missão.")
            st.info("Abaixo está o modelo de como seus dados serão exibidos após o primeiro registro:")
            # Criamos um DataFrame fictício (Mock) apenas para visualização
            mock_data = {
                "Data": ["16/01/2026", "15/01/2026"],
                "Matéria": ["DIREITO CONSTITUCIONAL", "PORTUGUÊS"],
                "Assunto": ["Direitos Fundamentais", "Sintaxe"],
                "Qtd": [20, 15],
                "Acertos": [18, 12],
                "%": ["90%", "80%"],
                "Tempo": ["01:30:00", "00:45:00"]
            }
            st.table(pd.DataFrame(mock_data)) # st.table é estático e cinza, ideal para exemplo
        else:
            # Se houver dados reais, exibe o editor interativo
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo']
            
            # Garante que as colunas existem antes de exibir
            for c in cols_show:
                if c not in df_hist.columns: df_hist[c] = ""
                
            ed = st.data_editor(df_hist[cols_show], hide_index=True, use_container_width=True)
            
            if st.button("💾 ATUALIZAR REGISTROS"):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], 
                        "data_estudo": dt_iso, "tempo": r['tempo']
                    }).eq("id", r['id']).execute()
                st.success("Histórico atualizado!"); st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                # REGRA FERNANDO: 0130 -> 01:30:00
                t_bruto = c2.text_input("Tempo (ex: 0130)", placeholder="HHMM")
                t_final = formatar_tempo_estudo(t_bruto)
                st.info(f"Tempo que será salvo: **{t_final}**")
                
                mat = st.selectbox("Matéria", mats)
                ass = st.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
                
                st.divider()
                c_ac, c_tot = st.columns(2)
                ac, tot = c_ac.number_input("Acertos", 0), c_tot.number_input("Total", 1)
                coment = st.text_area("Comentários")
                
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100), "comentarios": coment, "tempo": t_final,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("Salvo!"); time.sleep(1); st.rerun()
