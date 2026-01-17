import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
import re
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

apply_styles()

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# REGRA OK: 0130 -> 01:30:00
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
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=1)

    # --- ABA REVISÕES (REGRA PÓS-EDITAL OK) ---
    if menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        if df.empty:
            st.info("Nenhum registro para gerar revisões.")
        else:
            hoje = datetime.date.today()
            pendencias = []
            for _, row in df.iterrows():
                dt_estudo = pd.to_datetime(row['data_estudo']).date()
                dias_desde = (hoje - dt_estudo).days
                taxa = row.get('taxa', 0)
                if dias_desde >= 1 and not row.get('rev_24h', False):
                    pendencias.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias_desde - 1})
                if row.get('rev_24h', False):
                    if taxa <= 75: d, col, label = 7, "rev_07d", "Revisão 7d"
                    elif 76 <= taxa <= 79: d, col, label = 15, "rev_15d", "Revisão 15d"
                    else: d, col, label = 20, "rev_30d", "Revisão 20d"
                    if dias_desde >= d and not row.get(col, False):
                        pendencias.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": label, "col": col, "atraso": dias_desde - d})
            if not pendencias: st.success("✅ Tudo revisado!")
            else:
                for p in pendencias:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1.5, 1])
                        c1.markdown(f"**{p['materia']}**\n\n*{p['assunto']}*")
                        cor = ":red" if p['atraso'] > 0 else ":green"
                        c2.markdown(f"{cor}[{p['tipo']}]")
                        if c3.button("CONCLUIR", key=f"rev_{p['id']}_{p['col']}"):
                            supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute(); st.rerun()

    # --- ABA CONFIGURAR (RESTAURADA) ---
    elif menu == "Configurar":
        st.subheader("⚙️ Gerenciar Disciplinas do Edital")
        
        # Inserir Nova Matéria
        with st.form("add_materia"):
            c1, c2 = st.columns([3, 1])
            nova_m = c1.text_input("Nome da Nova Disciplina")
            if c2.form_submit_button("➕ ADICIONAR"):
                if nova_m:
                    supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nova_m, "topicos": []}).execute()
                    st.success(f"{nova_m} adicionada!"); time.sleep(0.5); st.rerun()

        st.divider()
        
        # Gerenciar Matérias Existentes
        if not dados.get('materias'):
            st.info("Nenhuma disciplina cadastrada ainda.")
        else:
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    # Campo para editar tópicos
                    tx = st.text_area("Tópicos (um por linha)", value="\n".join(t), key=f"tx_{m}", height=150)
                    col_s, col_d = st.columns([1, 4])
                    
                    if col_s.button("💾 SALVAR", key=f"save_{m}"):
                        novos_t = [l.strip() for l in tx.split('\n') if l.strip()]
                        supabase.table("editais_materias").update({"topicos": novos_t}).eq("concurso", missao).eq("materia", m).execute()
                        st.toast("Tópicos atualizados!"); time.sleep(0.5); st.rerun()
                    
                    if col_d.button("🗑️ EXCLUIR DISCIPLINA", key=f"del_mat_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.error(f"{m} removida!"); time.sleep(0.5); st.rerun()

    # --- ABA REGISTRAR (REGRA HHMM OK) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                t_bruto = c2.text_input("Tempo (HHMM)", placeholder="0130")
                t_final = formatar_tempo_estudo(t_bruto)
                st.info(f"Tempo: **{t_final}**")
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                c_ac, c_tot = st.columns(2)
                ac, tot = c_ac.number_input("Acertos", 0), c_tot.number_input("Total", 1)
                coment = st.text_area("Comentários")
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "comentarios": str(coment), "tempo": str(t_final), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute()
                    st.success("✅ SALVO!"); time.sleep(0.8); st.rerun()

    # --- ABA HISTÓRICO (KPIs OK) ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            df_hist['id'] = df_hist['id'].astype(str)
            df_hist['taxa'] = pd.to_numeric(df_hist['taxa'], errors='coerce').fillna(0).astype(float)
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Questões", int(df_hist['total'].sum()))
            k2.metric("Precisão Média", f"{df_hist['taxa'].mean():.1f}%")
            k3.metric("Lançamentos", len(df_hist))
            st.divider()
            cols = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']
            ed = st.data_editor(df_hist[cols], hide_index=True, use_container_width=True, column_config={"taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%")})
            c_s, c_d = st.columns([4, 1])
            if c_s.button("💾 CONFIRMAR ALTERAÇÕES"):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso, "tempo": r['tempo'], "comentarios": r['comentarios'], "taxa": (r['acertos']/r['total']*100)}).eq("id", r['id']).execute()
                st.rerun()
            with c_d.popover("🗑️ APAGAR"):
                id_del = st.text_input("ID")
                if st.button("CONFIRMAR"):
                    supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()
