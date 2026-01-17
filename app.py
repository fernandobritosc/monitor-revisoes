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

# FUNÇÃO AJUSTADA: 0130 -> 01:30:00
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto) # Mantém apenas números
    if not numeros: return "00:00:00"
    
    # Garante que temos pelo menos 4 dígitos (HHMM)
    numeros = numeros.zfill(4)
    
    # Pega os 2 primeiros como Hora e os 2 seguintes como Minutos
    horas = numeros[:2]
    minutos = numeros[2:4]
    
    # Se houver mais números, seriam os segundos, senão fixa 00
    segundos = numeros[4:6] if len(numeros) > 4 else "00"
    
    return f"{horas.zfill(2)}:{minutos.zfill(2)}:{segundos.zfill(2)}"

# --- 2. TELA INICIAL: CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    
    with tabs[0]:
        ed = get_editais(supabase)
        if not ed: 
            st.info("Nenhum concurso cadastrado.")
        
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 0.5])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()
                
                if c3.button("🗑️", key=f"del_btn_{nome}"):
                    st.session_state[f"confirm_del_{nome}"] = True

                if st.session_state.get(f"confirm_del_{nome}", False):
                    st.warning(f"Excluir **{nome}**?")
                    cs, cn = st.columns(2)
                    if cs.button("✅ SIM", key=f"y_{nome}"):
                        if excluir_concurso_completo(supabase, nome):
                            st.toast("Missão removida!")
                            del st.session_state[f"confirm_del_{nome}"]; st.rerun()
                    if cn.button("❌ NÃO", key=f"n_{nome}"):
                        del st.session_state[f"confirm_del_{nome}"]; st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro de Nova Missão")
        with st.form("form_novo"):
            n_n, n_c = st.text_input("Nome do Concurso"), st.text_input("Cargo")
            if st.form_submit_button("CRIAR MISSÃO"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.success("Missão Criada!"); time.sleep(0.8); st.rerun()

# --- 3. PAINEL DE ESTUDOS ---
else:
    missao = st.session_state.missao_ativa
    res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res.data)
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"):
            st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], 
                           default_index=2)

    if menu == "Registrar":
        st.subheader("📝 Novo Registro de Estudo")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                c_data, c_tempo = st.columns([2, 1])
                with c_data:
                    data_sel = st.radio("Data", ["HOJE", "ONTEM", "OUTRO"], horizontal=True)
                    if data_sel == "HOJE": dt = datetime.date.today()
                    elif data_sel == "ONTEM": dt = datetime.date.today() - datetime.timedelta(days=1)
                    else: dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                
                with c_tempo:
                    # IMPLEMENTAÇÃO DA SUA REGRA
                    t_bruto = st.text_input("Tempo (ex: 0130 para 1h30)", placeholder="HHMM")
                    t_final = formatar_tempo_estudo(t_bruto)
                    st.info(f"Tempo registrado: **{t_final}**")
                
                mat = st.selectbox("Disciplina", mats)
                ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                
                st.divider()
                c1, c2 = st.columns(2)
                acertos = c1.number_input("Acertos", 0)
                total_q = c2.number_input("Total", 1)
                coment = st.text_area("Comentários")
                
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": acertos, "total": total_q, 
                        "taxa": (acertos/total_q*100), "comentarios": coment, "tempo": t_final,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("Registrado!"); time.sleep(1); st.rerun()

    elif menu == "Dashboard":
        st.subheader("📊 Performance")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            st.metric("Precisão Geral", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            df_g = df.copy(); df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            st.plotly_chart(px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626']), use_container_width=True)

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
