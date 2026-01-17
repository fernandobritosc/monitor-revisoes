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

# FUNÇÃO FERNANDO: 0130 -> 01:30:00
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
                    if cn.button("❌ NÃO", key=f"no_{nome}"):
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
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=2)

    if menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                t_bruto = c2.text_input("Tempo (ex: 0130)", placeholder="HHMM")
                t_final = formatar_tempo_estudo(t_bruto)
                st.info(f"Tempo: **{t_final}**")
                
                mat = st.selectbox("Disciplina", mats)
                ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                
                st.divider()
                c_ac, c_tot = st.columns(2)
                ac, tot = c_ac.number_input("Acertos", 0), c_tot.number_input("Total", 1)
                coment = st.text_area("Comentários")
                
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    # --- BLOCO DE SEGURANÇA MÁXIMA ---
                    # Tentamos enviar com TUDO. Se o banco rejeitar, enviamos só o básico.
                    dados_registro = {
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False,
                        "comentarios": coment, "tempo": t_final
                    }
                    
                    try:
                        # Tentativa 1: Tudo (Com Tempo e Comentários)
                        supabase.table("registros_estudos").insert(dados_registro).execute()
                        st.success("Salvo com sucesso!")
                    except:
                        # Tentativa 2: Básico (Se o banco ainda não reconheceu as colunas novas)
                        dados_basicos = {k: v for k, v in dados_registro.items() if k not in ["comentarios", "tempo"]}
                        supabase.table("registros_estudos").insert(dados_basicos).execute()
                        st.warning("Salvo sem Tempo/Comentários (Banco em sincronização).")
                    
                    time.sleep(1); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty:
            st.info("Aguardando dados...")
            mock = {"Data": ["--/--/--"], "Matéria": ["Exemplo"], "Assunto": ["Exemplo"], "Qtd": [0], "Acertos": [0], "%": ["0%"], "Tempo": ["00:00:00"]}
            st.table(pd.DataFrame(mock))
        else:
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']
            if 'tempo' in df_hist.columns: cols_show.append('tempo')
            
            ed = st.data_editor(df_hist[cols_show], hide_index=True)
            if st.button("💾 ATUALIZAR"):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso}).eq("id", r['id']).execute()
                st.rerun()
    
    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Adicionar"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos", "\n".join(t), key=f"t_{m}")
                if st.button("Salvar Tópicos", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
