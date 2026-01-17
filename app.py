import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE TEMA (FIXO ESCURO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    .stMetric { background-color: #1E2129 !important; border: 1px solid #31333F !important; border-radius: 12px; padding: 15px; }
    div[data-testid="stExpander"] { background-color: #1E2129 !important; border: 1px solid #31333F !important; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# Função de tempo blindada: Garante HH:MM:SS
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    horas = numeros[:-2][-2:].zfill(2)
    minutos = numeros[-2:].zfill(2)
    return f"{horas}:{minutos}:00"

# --- 2. NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    ed = get_editais(supabase)
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    with tabs[0]:
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()
    with tabs[1]:
        with st.form("f_novo"):
            n_n, n_c = st.text_input("Nome"), st.text_input("Cargo")
            if st.form_submit_button("CRIAR"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.rerun()
else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["grid", "arrow-repeat", "pencil", "gear", "list"], default_index=2)

    # --- ABA REGISTRAR (CORREÇÃO DE ERRO API) ---
    if menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.form("form_registro"):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                tb = c2.text_input("Tempo (HHMM)", value="0100")
                
                mat = st.selectbox("Disciplina", mats)
                ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                
                ca, ct = st.columns(2)
                ac = ca.number_input("Acertos", min_value=0, value=0)
                tot = ct.number_input("Total", min_value=1, value=1)
                
                com = st.text_area("Comentários (Links TEC)")
                
                if st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True):
                    try:
                        tempo_limpo = formatar_tempo_estudo(tb)
                        taxa_calculada = float((ac / tot) * 100)
                        
                        payload = {
                            "concurso": str(missao),
                            "materia": str(mat),
                            "assunto": str(ass),
                            "data_estudo": dt.strftime('%Y-%m-%d'),
                            "acertos": int(ac),
                            "total": int(tot),
                            "taxa": taxa_calculada,
                            "comentarios": str(com),
                            "tempo": tempo_limpo,
                            "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }
                        
                        supabase.table("registros_estudos").insert(payload).execute()
                        st.success("✅ Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    # --- ABA REVISÕES (DIAS DE ATRASO) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias-1, "c": row['comentarios']})
                if row.get('rev_24h', False):
                    # Lógica 7/15/20
                    d_alvo, col_alvo, lbl = (7, "rev_07d", "Revisão 7d") if tx <= 75 else (15, "rev_15d", "Revisão 15d") if tx <= 79 else (20, "rev_30d", "Revisão 20d")
                    if dias >= d_alvo and not row.get(col_alvo, False):
                        pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": lbl, "col": col_alvo, "atraso": dias-d_alvo, "c": row['comentarios']})

        if not pend: st.success("✅ Nada para revisar hoje!")
        else:
            for p in pend:
                with st.container(border=True):
                    c_i, c_a = st.columns([2, 1])
                    c_i.markdown(f"### {p['materia']}\n**{p['assunto']}**\n{p['tipo']}")
                    if p['atraso'] > 0: c_a.error(f"⚠️ {p['atraso']}d de atraso")
                    if c_a.button("CONCLUIR", key=f"rv_{p['id']}_{p['col']}"):
                        supabase.table("registros_estudos").update({p['col']: True}).eq("id", p['id']).execute(); st.rerun()

    # --- ABA HISTÓRICO ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            df_h = df.copy()
            df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_h[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], use_container_width=True, hide_index=True)

    # --- DEMAIS ABAS ---
    elif menu == "Dashboard":
        st.write("Dashboard ativado.")
    elif menu == "Configurar":
        st.subheader("⚙️ Configurar")
        with st.form("add_mat"):
            nm = st.text_input("Disciplina")
            if st.form_submit_button("ADD"):
                supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
