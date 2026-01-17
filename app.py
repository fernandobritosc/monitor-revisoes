import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
import re
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE PÁGINA (LAYOUT AMPLO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

# Importação dos Módulos Independentes
from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

# Aplica o visual CSS
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
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("id", desc=True).execute()
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

    # --- ABA HISTÓRICO ---
    if menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            df_hist['id'] = df_hist['id'].astype(str)
            df_hist['taxa'] = pd.to_numeric(df_hist['taxa'], errors='coerce').fillna(0).astype(float)
            
            # Filtro por Disciplina
            filtro_mat = st.multiselect("Filtrar por Disciplina", options=df_hist['materia'].unique())
            if filtro_mat:
                df_hist = df_hist[df_hist['materia'].isin(filtro_mat)]
            
            # --- PAINEL DE MÉTRICAS (KPIs) ---
            st.divider()
            kpi1, kpi2, kpi3 = st.columns(3)
            total_q = df_hist['total'].sum()
            precisao_media = df_hist['taxa'].mean()
            kpi1.metric("Questões", f"{int(total_q)}")
            kpi2.metric("Precisão Média", f"{precisao_media:.1f}%")
            kpi3.metric("Lançamentos", len(df_hist))
            st.divider()

            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']
            
            ed = st.data_editor(
                df_hist[cols_show], 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%"),
                    "acertos": "✅",
                    "total": "📊",
                    "tempo": "⏱️",
                    "comentarios": st.column_config.TextColumn("Comentários", width="large")
                }
            )
            
            # --- BOTÕES DE AÇÃO ---
            c_save, c_del = st.columns([4, 1])
            
            if c_save.button("💾 CONFIRMAR ALTERAÇÕES NA TABELA", use_container_width=True):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso,
                        "tempo": r['tempo'], "comentarios": r['comentarios'],
                        "taxa": (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    }).eq("id", r['id']).execute()
                st.success("Alterações salvas!"); time.sleep(1); st.rerun()

            with c_del.popover("🗑️ APAGAR REGISTRO"):
                st.write("Digite o ID do lançamento que deseja remover:")
                id_del = st.text_input("Número do ID", key="id_to_del")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary"):
                    if id_del:
                        supabase.table("registros_estudos").delete().eq("id", id_del).execute()
                        st.error(f"Registro {id_del} removido com sucesso!")
                        time.sleep(1); st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                t_bruto = c2.text_input("Tempo (ex: 0130)", placeholder="HHMM")
                t_final = formatar_tempo_estudo(t_bruto)
                st.info(f"Tempo: **{t_final}**")
                mat = st.selectbox("Disciplina", mats)
                ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
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

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Add"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos", "\n".join(t), key=f"t_{m}")
                if st.button("Salvar", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
