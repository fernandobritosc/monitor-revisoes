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

    # --- ABA REVISÕES (LÓGICA PÓS-EDITAL) ---
    if menu == "Revisões":
        st.subheader("🔄 Radar de Revisões (Modo Pós-Edital)")
        if df.empty:
            st.info("Nenhum registro para gerar revisões.")
        else:
            hoje = datetime.date.today()
            pendencias = []
            
            for _, row in df.iterrows():
                dt_estudo = pd.to_datetime(row['data_estudo']).date()
                dias_desde = (hoje - dt_estudo).days
                taxa = row.get('taxa', 0)
                
                # 1. REGRA 24H (Sempre ocorre para todos)
                if dias_desde >= 1 and not row.get('rev_24h', False):
                    pendencias.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias_desde - 1})
                
                # 2. LÓGICA DE PERFORMANCE (7d, 15d ou 20d)
                # Só entra no radar de longo prazo se a de 24h já foi concluída
                if row.get('rev_24h', False):
                    if taxa <= 75:
                        d, col, label = 7, "rev_07d", "Revisão 7d (Reforço)"
                    elif 76 <= taxa <= 79:
                        d, col, label = 15, "rev_15d", "Revisão 15d (Manutenção)"
                    else: # 80 a 100%
                        d, col, label = 20, "rev_30d", "Revisão 20d (Excelência)" # Reutilizamos a coluna 30d para os 20d
                    
                    if dias_desde >= d and not row.get(col, False):
                        pendencias.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": label, "col": col, "atraso": dias_desde - d})

            if not pendencias:
                st.success("✅ Tudo revisado!")
            else:
                st.warning(f"Tens {len(pendencias)} revisões pendentes.")
                for p in pendencias:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1.5, 1])
                        c1.markdown(f"**{p['materia']}**")
                        c1.caption(f"Tópico: {p['assunto']}")
                        
                        cor = ":red" if p['atraso'] > 0 else ":green"
                        c2.markdown(f"{cor}[{p['tipo']}]")
                        if p['atraso'] > 0: c2.caption(f"⚠️ {p['atraso']} dias de atraso")
                            
                        if c3.button("CONCLUIR", key=f"rev_{p['id']}_{p['col']}"):
                            supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute()
                            st.toast("Concluído!"); time.sleep(0.5); st.rerun()

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
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                c_ac, c_tot = st.columns(2)
                ac, tot = c_ac.number_input("Acertos", 0), c_tot.number_input("Total", 1)
                coment = st.text_area("Comentários")
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100) if tot > 0 else 0,
                        "comentarios": str(coment), "tempo": str(t_final),
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("✅ SALVO!"); time.sleep(1); st.rerun()

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
            ed = st.data_editor(df_hist[cols], hide_index=True, use_container_width=True,
                column_config={"taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%")})
            c_save, c_del = st.columns([4, 1])
            if c_save.button("💾 CONFIRMAR ALTERAÇÕES", use_container_width=True):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso,
                        "tempo": r['tempo'], "comentarios": r['comentarios'],
                        "taxa": (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    }).eq("id", r['id']).execute()
                st.rerun()
            with c_del.popover("🗑️ APAGAR"):
                id_del = st.text_input("ID")
                if st.button("CONFIRMAR"):
                    supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()
