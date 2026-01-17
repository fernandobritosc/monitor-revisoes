import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
import re
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE PÁGINA (MUDANÇA PARA LAYOUT AMPLO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

# Importações dos Módulos
from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

apply_styles()

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# FUNÇÃO DE TEMPO: 0130 -> 01:30:00
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto) 
    if not numeros: return "00:00:00"
    numeros = numeros.zfill(4)
    horas = numeros[:-2].zfill(2)
    minutos = numeros[-2:].zfill(2)
    return f"{horas}:{minutos}:00"

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

# --- 3. PAINEL INTERNO (EXPANSÍVEL) ---
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
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=4)

    # --- HISTÓRICO MELHORADO ---
    if menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty:
            st.info("Nenhum dado real ainda.")
        else:
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            
            # Ordenação das colunas para o visual
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'tempo', 'comentarios']
            for col in cols_show:
                if col not in df_hist.columns: df_hist[col] = ""

            # O use_container_width=True faz a tabela esticar ao fechar o menu lateral
            ed = st.data_editor(
                df_hist[cols_show], 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "data_estudo": st.column_config.TextColumn("Data", width="medium"),
                    "materia": st.column_config.TextColumn("Matéria", width="large"),
                    "assunto": st.column_config.TextColumn("Assunto", width="large"),
                    "comentarios": st.column_config.TextColumn("Comentários", width="large")
                }
            )
            
            if st.button("💾 CONFIRMAR ALTERAÇÕES", use_container_width=True):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso,
                        "tempo": r['tempo'], "comentarios": r['comentarios']
                    }).eq("id", r['id']).execute()
                st.success("Alterações salvas!"); time.sleep(1); st.rerun()

    elif menu == "Registrar":
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
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100) if tot > 0 else 0,
                        "comentarios": str(coment), "tempo": str(t_final)
                    }).execute()
                    st.success("✅ SALVO!"); time.sleep(1); st.rerun()

    elif menu == "Dashboard":
        st.subheader("📊 Performance")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            c1, c2 = st.columns(2)
            c1.metric("Questões Totais", int(tot))
            c2.metric("Precisão Geral", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            
            df_g = df.copy(); df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            st.plotly_chart(px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626']), use_container_width=True)
