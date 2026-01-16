import streamlit as st
import pandas as pd
import datetime
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Concursos", page_icon="💀", layout="wide")

DB_FILE = "estudos_data.csv"
EDITAIS_FILE = "editais_db.json"
META_QUESTOES = 2000 

# --- FUNÇÕES ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def carregar_editais():
    if os.path.exists(EDITAIS_FILE):
        try:
            with open(EDITAIS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_editais(editais_dict):
    with open(EDITAIS_FILE, "w", encoding="utf-8") as f:
        json.dump(editais_dict, f, indent=4, ensure_ascii=False)

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

def calcular_metricas_streak(df):
    if df.empty: return 0, 0
    try:
        if 'Data_Estudo' not in df.columns: return 0, 0
        dates = pd.to_datetime(df['Data_Estudo'], dayfirst=True, errors='coerce').dt.normalize().dropna().unique()
        dates = sorted(dates)
        if not len(dates): return 0, 0
        
        max_streak = 1
        current_run = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                current_run += 1
            else:
                max_streak = max(max_streak, current_run)
                current_run = 1
        max_streak = max(max_streak, current_run)

        hoje = pd.Timestamp.now().normalize()
        streak_atual = 0
        dates_reverse = sorted(dates, reverse=True)
        if hoje in dates:
            streak_atual = 1
            check_date = hoje - pd.Timedelta(days=1)
        elif (hoje - pd.Timedelta(days=1)) in dates:
            streak_atual = 0
            check_date = hoje - pd.Timedelta(days=1)
        else:
            return 0, max_streak
        for d in dates_reverse:
            if d == hoje: continue
            if d == check_date:
                streak_atual += 1
                check_date -= pd.Timedelta(days=1)
            else:
                break
        return streak_atual, max_streak
    except:
        return 0, 0

# Inicializar
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()
if 'editais' not in st.session_state:
    st.session_state.editais = carregar_editais()

# Vacina
if "Concurso" not in st.session_state.df_dados.columns:
    st.session_state.df_dados["Concurso"] = "Geral"
    salvar_dados(st.session_state.df_dados)
    st.rerun()

df = st.session_state.df_dados
editais = st.session_state.editais

# --- BARRA LATERAL ---
with st.sidebar:
    c_logo, c_text = st.columns([1, 2])
    with c_logo:
        try:
            st.image("2498586-caveira-com-facas-gratis-vetor.jpg", width=80)
        except:
            st.image("https://cdn-icons-png.flaticon.com/512/9203/9203029.png", width=70)

    with c_text:
        st.markdown("""
            <div style="padding-top: 10px;">
                <h3 style='margin: 0; padding: 0; font-size: 20px;'><b>Faca na Caveira</b></h3>
                <span style='color: #00E676; font-size: 14px; font-weight: bold; display: block; margin-top: -3px;'>Concursos</span>
            </div>
            """, unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title="Painel Tático",
        options=["Dashboard", "Novo Registro", "Gestão de Editais", "Histórico"], 
        icons=["bar-chart-line-fill", "plus-circle-fill", "journal-bookmark-fill", "table"], 
        menu_icon="compass", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent", "margin-top": "20px"},
            "icon": {"color": "#00E676", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"5px", "--hover-color": "#262730"},
            "nav-link-selected": {"background-color": "#00C853"}, 
            "menu-title": {"color": "#6c757d", "font-size": "12px", "font-weight": "bold", "margin-bottom": "5px"}
        }
    )
    
    st.markdown("---")
    col_avatar, col_user = st.columns([1, 3])
    with col_avatar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=40)
    with col_user:
        st.markdown("""
            <div style="padding-top: 5px;">
                <b style="font-size: 14px;">Fernando</b><br>
                <span style="font-size: 11px; color: gray;">Rumo à Aprovação</span>
            </div>
        """, unsafe_allow_html=True)

# --- CONTEÚDO ---

# === DASHBOARD ===
if selected == "Dashboard":
    st.title("📊 Painel de Performance")
    
    if not df.empty:
        lista_concursos = ["Todos"] + sorted(list(df['Concurso'].unique()))
        filtro_concurso = st.selectbox("Visualizar dados de:", lista_concursos)
        
        df_view = df.copy()
        if filtro_concurso != "Todos":
            df_view = df_view[df_view['Concurso'] == filtro_concurso]

        if df_view.empty:
            st.warning("Sem dados.")
        else:
            df_calc = df_view.copy()
            df_calc['Acertos'] = pd.to_numeric(df_calc['Acertos'], errors='coerce').fillna(0)
            df_calc['Total'] = pd.to_numeric(df_calc['Total'], errors='coerce').fillna(1)
            df_calc['Data_Ordenacao'] = pd.to_datetime(df_calc['Proxima_Revisao'], dayfirst=True, errors='coerce')

            total_q = df_calc['Total'].sum()
            media_g = (df_calc['Acertos'].sum() / total_q * 100) if total_q > 0 else 0
            hoje = pd.Timestamp.now().normalize()
            # Pendentes: filtra datas <= hoje
            df_pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje]
            qtd_pendentes = df_pendentes.shape[0]
            
            streak_atual, recorde_hist = calcular_metricas_streak(df)

            # Barra de Meta Global
            meta_local = META_QUESTOES if filtro_concurso == "Todos" else int(META_QUESTOES / 2)
            progresso = min(total_q / meta_local, 1.0)
            st.caption(f"🚀 Meta Geral ({filtro_concurso}): {int(total_q)} / {meta_local} Questões")
            st.progress(progresso, text=f"{progresso*100:.1f}%")
            st.markdown("<br>", unsafe_allow_html=True)

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões", int(total_q), border=True)
            c2.metric("Precisão", f"{media_g:.1f}%", border=True)
            c3.metric("Revisões Hoje", qtd_pendentes, delta="Atenção" if qtd_pendentes > 0 else "Em dia", delta_color="inverse", border=True)
            if streak_atual > 0:
                c4.metric("🔥 Streak", f"{streak_atual} dias", delta="Focado!", delta_color="normal", border=True)
            else:
                c4.metric("❄️ Streak", "0 dias", delta=f"Recorde: {recorde_hist}", delta_color="off", border=True)

            # --- NOVO BLOCO: MISSÕES E COBERTURA ---
            st.markdown("---")
            t_missoes, t_cobertura = st.tabs(["📅 Missões (Revisão)", "🛡️ Cobertura do Edital"])
            
            with t_missoes:
                if qtd_pendentes > 0:
                    st.error(f"Você tem {qtd_pendentes} revisões pendentes!")
                    st.dataframe(
                        df_pendentes[["Data_Estudo", "Concurso", "Materia", "Assunto", "Proxima_Revisao"]].sort_values("Proxima_Revisao"),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.success("Nada para revisar hoje. Avance no conteúdo!")

            with t_cobertura:
                # Lógica de Cobertura de Edital
                if not editais:
                    st.info("Cadastre um edital para ver a cobertura.")
                else:
                    # Se selecionou um concurso no filtro, mostra só ele. Se "Todos", avisa.
                    if filtro_concurso == "Todos":
                        concurso_para_analise = st.selectbox("Selecione um Edital para ver o progresso:", list(editais.keys()))
                    else:
                        concurso_para_analise = filtro_concurso

                    if concurso_para_analise in editais:
                        dados_edital = editais[concurso_para_analise]
                        materias_edital = dados_edital.get("materias", {})
                        
                        if not materias_edital:
                            st.warning("Este edital não tem matérias cadastradas.")
                        else:
                            st.subheader(f"Progresso: {concurso_para_analise}")
                            for mat, topicos_lista in materias_edital.items():
                                total_topicos = len(topicos_lista)
                                if total_topicos == 0:
                                    continue
                                
                                # Conta quantos tópicos únicos desta matéria já foram estudados no registro
                                # Filtra DF pelo concurso e matéria
                                df_mat = df[ (df['Concurso'] == concurso_para_analise) & (df['Materia'] == mat) ]
                                topicos_estudados = df_mat['Assunto'].unique()
                                # Interseção para garantir que só conta tópicos que estão no edital
                                estudados_validos = [t for t in topicos_estudados if t in topicos_lista]
                                qtd_estudados = len(estudados_validos)
                                
                                perc = qtd_estudados / total_topicos
                                
                                st.write(f"**{mat}** ({qtd_estudados}/{total_topicos})")
                                st.progress(perc, text=f"{perc*100:.1f}% Concluído")
                    else:
                        st.warning("Concurso não encontrado nos editais.")

            st.markdown("---")
            
            # Gráficos
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("🕸️ Radar Tático")
                df_radar = df_calc.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
                if not df_radar.empty:
                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(
                        r=df_radar['Nota'], theta=df_radar['Materia'], fill='toself', name='Desempenho',
                        line_color='#00E676', mode='lines+markers+text',
                        text=[f"{n:.0f}%" for n in df_radar['Nota']], textposition='top center',
                        textfont=dict(color="#00E676", size=11, weight="bold")
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)),
                        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=40, r=40, t=20, b=20)
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

            with g2:
                st.subheader("📈 Evolução")
                df_calc['Data_Real'] = pd.to_datetime(df_calc['Data_Estudo'], dayfirst=True, errors='coerce')
                df_t = df_calc.groupby("Data_Real")['Total'].sum().reset_index()
                fig2 = px.line(df_t, x="Data_Real", y="Total", markers=True, labels={"Data_Real": "Data", "Total": "Questões"})
                fig2.update_traces(line_color='#00E676')
                fig2.update_xaxes(tickformat="%d/%m", dtick="D1")
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

            # Mapa da Vergonha
            st.subheader("🗺️ Mapa da Vergonha")
            try:
                df_resumo = df_calc.groupby(["Materia", "Assunto"])[["Acertos", "Total"]].sum().reset_index()
                df_resumo["Aproveitamento"] = (df_resumo["Acertos"] / df_resumo["Total"] * 100)
                df_resumo["Erros"] = df_resumo["Total"] - df_resumo["Acertos"]
                df_piores = df_resumo[df_resumo["Aproveitamento"] < 80].sort_values(by="Aproveitamento").copy()
                
                if not df_piores.empty:
                    st.error("🚨 TOMA RUMO! Melhora estas matérias:")
                    df_piores["Aproveitamento"] = df_piores["Aproveitamento"].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(df_piores[["Materia", "Assunto", "Total", "Erros", "Aproveitamento"]], use_container_width=True, hide_index=True)
                else:
                    st.success("🏆 Tudo acima de 80%!")
            except: pass
    else:
        st.info("Registe o seu primeiro edital.")

# === NOVO REGISTRO ===
elif selected == "Novo Registro":
    st.title("📝 Lançamento Inteligente")
    
    if not editais:
        st.warning("⚠️ Nenhum Edital cadastrado. Vá em 'Gestão de Editais' primeiro.")
        concurso_sel = "Avulso"
        materias_possiveis = []
        topicos_possiveis = []
    else:
        concurso_sel = st.selectbox("Selecione o Concurso:", list(editais.keys()))
        dados_concurso = editais[concurso_sel]
        materias_possiveis = list(dados_concurso.get("materias", {}).keys())
        materia_sel = st.selectbox("Disciplina:", materias_possiveis) if materias_possiveis else None
        
        topicos_possiveis = []
        if materia_sel:
            topicos_possiveis = dados_concurso["materias"][materia_sel]

    st.markdown("---")
    
    with st.container(border=True):
        st.subheader("Relatório de Estudo")
        with st.form("form_estudo", clear_on_submit=True):
            c_data, c_vazio = st.columns([1, 2])
            data_input = c_data.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            
            if topicos_possiveis:
                assunto = st.selectbox("Assunto do Edital:", topicos_possiveis)
            else:
                assunto = st.text_input("Assunto (Sem tópicos cadastrados)")
            
            c1, c2 = st.columns(2)
            ac = c1.number_input("Acertos", min_value=0, step=1)
            tot = c2.number_input("Total", min_value=1, step=1)
            
            btn = st.form_submit_button("✅ Salvar Estudo", use_container_width=True)

        if btn:
            if not materia_sel and concurso_sel != "Avulso":
                st.error("Cadastre matérias no edital antes de estudar.")
            else:
                mat_final = materia_sel if materia_sel else "Geral"
                taxa_calc = (ac/tot)*100
                data_rev = calcular_revisao(data_input, taxa_calc)
                
                nova = pd.DataFrame([{
                    "Data_Estudo": data_input.strftime('%d/%m/%Y'),
                    "Concurso": concurso_sel, 
                    "Materia": mat_final,
                    "Assunto": assunto,
                    "Acertos": str(ac),
                    "Total": str(tot),
                    "Taxa": f"{taxa_calc:.1f}%",
                    "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
                }])
                
                st.session_state.df_dados = pd.concat([df, nova], ignore_index=True)
                salvar_dados(st.session_state.df_dados)
                st.success(f"Registrado! Revisão: {data_rev.strftime('%d/%m/%Y')}")

# === GESTÃO DE EDITAIS ===
elif selected == "Gestão de Editais":
    st.title("📑 Edital Verticalizado")
    
    with st.expander("➕ Criar Novo Concurso", expanded=not bool(editais)):
        with st.form("form_novo_concurso"):
            c1, c2, c3 = st.columns(3)
            novo_nome = c1.text_input("Nome (ex: PF 2026)")
            novo_cargo = c2.text_input("Cargo (ex: Agente)")
            nova_data = c3.date_input("Data da Prova", format="DD/MM/YYYY") 
            
            if st.form_submit_button("Criar Concurso"):
                if novo_nome:
                    if novo_nome not in editais:
                        editais[novo_nome] = {
                            "cargo": novo_cargo,
                            "data_prova": nova_data.strftime('%Y-%m-%d'), 
                            "materias": {} 
                        }
                        salvar_editais(editais)
                        st.success(f"Concurso {novo_nome} criado!")
                        st.rerun()
                    else:
                        st.error("Já existe.")

    st.markdown("---")

    if editais:
        concurso_ativo = st.selectbox("📂 Selecione o Concurso para Editar:", list(editais.keys()))
        dados = editais[concurso_ativo]
        
        data_banco = dados.get('data_prova', '-')
        try:
            d = datetime.datetime.strptime(data_banco, "%Y-%m-%d")
            data_visual = d.strftime("%d/%m/%Y")
        except:
            data_visual = data_banco
        
        st.info(f"**Cargo:** {dados.get('cargo', '-')} | **Prova:** {data_visual}")

        col_add_mat, col_view_mat = st.columns([1, 2])

        with col_add_mat:
            with st.container(border=True):
                st.markdown("#### 1. Adicionar Matéria")
                nova_mat_input = st.text_input("Disciplina (ex: Português)")
                if st.button("Salvar Matéria"):
                    if nova_mat_input:
                        if nova_mat_input not in dados["materias"]:
                            dados["materias"][nova_mat_input] = []
                            salvar_editais(editais)
                            st.success("Adicionada!")
                            st.rerun()
                        else:
                            st.warning("Já existe.")

        with col_view_mat:
            st.markdown("#### 2. Estrutura Verticalizada")
            materias = dados.get("materias", {})
            if not materias:
                st.warning("Nenhuma matéria cadastrada.")
            
            for mat, topicos in materias.items():
                with st.expander(f"📚 {mat} ({len(topicos)} tópicos)"):
                    
                    st.caption("🚀 Importação Rápida: Cole os tópicos separados por ponto e vírgula (;) ou Enter.")
                    texto_importacao = st.text_area(f"Colar Tópicos para {mat}:", height=100, key=f"txt_{concurso_ativo}_{mat}")
                    
                    c_btn_imp, c_btn_limp = st.columns([2, 1])
                    
                    if c_btn_imp.button(f"📥 Importar Lista em {mat}", key=f"btn_imp_{concurso_ativo}_{mat}"):
                        if texto_importacao:
                            texto_unificado = texto_importacao.replace("\n", ";")
                            novos_itens = texto_unificado.split(";")
                            novos_limpos = [item.strip() for item in novos_itens if item.strip()]
                            
                            if novos_limpos:
                                topicos.extend(novos_limpos)
                                salvar_editais(editais)
                                st.success(f"{len(novos_limpos)} tópicos importados!")
                                st.rerun()
                    
                    if topicos:
                        df_topicos = pd.DataFrame(topicos, columns=["Assuntos do Edital"])
                        st.dataframe(df_topicos, use_container_width=True, hide_index=True)
                        
                        if c_btn_limp.button("🗑️ Limpar Tudo", key=f"clean_{concurso_ativo}_{mat}"):
                            dados["materias"][mat] = []
                            salvar_editais(editais)
                            st.rerun()
                    else:
                        st.info("Lista vazia.")
