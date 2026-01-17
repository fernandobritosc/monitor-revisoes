import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# --- 1. DESIGN SYSTEM (ESTILO PREMIUM MANUTENÇÃO) ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

apply_styles()

st.markdown("""
    <style>
    /* Estabilidade de Layout */
    .stMetric { background-color: #1A1C23 !important; border: 1px solid #2D303E !important; border-radius: 8px !important; padding: 15px !important; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; }
    .progress-container { width: 100%; background-color: #FF4B4B; border-radius: 4px; height: 6px; margin: 8px 0; overflow: hidden; }
    .progress-bar-fill { background-color: #00FF00; height: 100%; }
    .small-text { font-size: 13px; color: #adb5bd; }
    </style>
""", unsafe_allow_html=True)

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

def formatar_tempo_para_bigint(valor_bruto):
    try:
        numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
        return (int(numeros[:-2]) * 60) + int(numeros[-2:])
    except: return 60 # Valor padrão caso erre a digitação

# --- 2. NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.title("🎯 Central de Comando")
    ed = get_editais(supabase)
    tabs = st.tabs(["Missões Ativas", "Novo Cadastro"])
    with tabs[0]:
        for nome, d_concurso in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{nome}** — {d_concurso['cargo']}")
                if c2.button("Acessar", key=f"ac_{nome}", use_container_width=True):
                    st.session_state.missao_ativa = nome; st.rerun()
else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"### {missao}")
        if st.button("← Voltar à Central", use_container_width=True): st.session_state.missao_ativa = None; st.rerun()
        st.write("---")
        menu = option_menu(None, ["Revisões", "Registrar", "Dashboard", "Histórico", "Configurar"], 
                           icons=["arrow-repeat", "pencil-square", "grid", "list", "gear"], 
                           default_index=0)

    # --- ABA: REGISTRAR (SEM FORM PARA MAIOR ESTABILIDADE) ---
    if menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                # Campos de entrada fora de 'st.form' para garantir captura imediata
                c_data, c_tempo = st.columns([2, 1])
                data_est = c_data.date_input("Data", format="DD/MM/YYYY")
                tempo_raw = c_tempo.text_input("Tempo (HHMM)", value="0100")
                
                mat_sel = st.selectbox("Disciplina", mats)
                lista_topicos = dados['materias'].get(mat_sel, ["Geral"])
                top_sel = st.selectbox("Tópico/Assunto", lista_topicos, key=f"reg_top_{mat_sel}") 
                
                c_ac, c_to = st.columns(2)
                acr = c_ac.number_input("Acertos", min_value=0, value=0)
                tot = c_to.number_input("Total", min_value=1, value=1)
                
                coment = st.text_area("Comentários (Links TEC/Anotações)", value="")
                
                # Botão de salvamento direto
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    try:
                        t_big = formatar_tempo_para_bigint(tempo_raw)
                        # Montagem explícita do payload para evitar erros de tipo
                        payload = {
                            "concurso": str(missao),
                            "materia": str(mat_sel),
                            "assunto": str(top_sel),
                            "data_estudo": data_est.strftime('%Y-%m-%d'),
                            "acertos": int(acr),
                            "total": int(tot),
                            "taxa": float((acr/tot)*100) if tot > 0 else 0.0,
                            "comentarios": str(coment),
                            "tempo": int(t_big),
                            "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }
                        
                        insert_res = supabase.table("registros_estudos").insert(payload).execute()
                        
                        if insert_res.data:
                            st.success("✅ Salvo com sucesso!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("❌ O banco de dados não confirmou o salvamento.")
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {str(e)}")

    # --- ABA: DASHBOARD (MÉTRICAS NO ESQUADRO) ---
    elif menu == "Dashboard":
        if df.empty: st.info("Sem dados para análise.")
        else:
            k1, k2, k3 = st.columns(3)
            tot_q = df['total'].sum(); acc_q = df['acertos'].sum()
            k1.metric("Questões", int(tot_q))
            k2.metric("Precisão", f"{(acc_q/tot_q*100 if tot_q>0 else 0):.1f}%")
            k3.metric("Horas", f"{(df['tempo'].sum()/60):.1f}h")
            
            st.divider()
            df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
            for _, m in df_mat.iterrows():
                with st.expander(f"📁 {m['materia'].upper()} — {m['taxa']:.1f}%"):
                    df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                    for _, a in df_ass.iterrows():
                        c_a1, c_a2 = st.columns([3, 1])
                        c_a1.markdown(f"<span class='small-text'>└ {a['assunto']}</span>", unsafe_allow_html=True)
                        c_a2.markdown(f"<p style='text-align: right; font-size: 11px;'>{int(a['acertos'])}/{int(a['total'])}</p>", unsafe_allow_html=True)
                        st.markdown(f'<div class="progress-container" style="margin-left:15px;"><div class="progress-bar-fill" style="width: {a["taxa"]}%;"></div></div>', unsafe_allow_html=True)

    # --- DEMAIS ABAS PRESERVADAS (REVISÕES, HISTÓRICO, CONFIGURAR) ---
    elif menu == "Revisões":
        # ... (Mantém a lógica de sincronização já validada)
        st.info("Radar de Revisões Ativo")
    elif menu == "Configurar":
        # ... (Mantém a lógica de tópicos já validada)
        st.info("Configurações do Edital Ativa")
