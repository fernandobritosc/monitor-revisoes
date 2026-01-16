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
EDITAIS_FILE = "editais_db.json" # <--- NOVO ARQUIVO PARA GUARDAR OS EDITAIS
META_QUESTOES = 2000 

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            # Garante que a coluna Concurso existe (para compatibilidade com dados antigos)
            if "Concurso" not in df.columns:
                df["Concurso"] = "Geral"
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

# Função Streak (Mantida)
def calcular_metricas_streak(df):
    if df.empty: return 0, 0
    try:
        dates = pd.to_datetime(df['Data_Estudo'], dayfirst=True).dt.normalize().unique()
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

# Inicializar Estado
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()
if 'editais' not in st.session_state:
    st.session_state.editais = carregar_editais()

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

# === PÁGINA 1: DASHBOARD ===
if selected == "Dashboard":
    st.title("📊 Painel de Performance")
    
    if not df.empty:
        # Filtro Global por Concurso no Dashboard
        lista_concursos = ["Todos"] + sorted(list(df['Concurso'].unique()))
        filtro_concurso = st.selectbox("Visualizar dados de:", lista_concursos)
        
        df_view = df.copy()
        if filtro_concurso != "Todos":
            df_view = df_view[df_view['Concurso'] == filtro_concurso]

        if df_view.empty:
            st.warning("Sem dados para este concurso ainda.")
        else:
            df_calc = df_view.copy()
            df_calc['Acertos'] = pd.to_numeric(df_calc['Acertos'], errors='coerce').fillna(0)
            df_calc['Total'] = pd.to_numeric(df_calc['Total'], errors='coerce').fillna(1)
            df_calc['Data_Ordenacao'] = pd.to_datetime(df_calc['Proxima_Revisao'], dayfirst=True, errors='coerce')

            total_q = df_calc['Total'].sum()
            media_g = (df_calc['Acertos'].sum() / total_q * 100) if total_q > 0 else 0
            hoje = pd.Timestamp.now().normalize()
            pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje].shape[0]
            streak_atual, recorde_hist = calcular_metricas_streak(df) # Streak conta estudo global

            # Barra de Meta (Ajustada se filtrar concurso)
            meta_local = META_QUESTOES if filtro_concurso == "Todos" else int(META_QUESTOES / 2) # Exemplo de meta dinamica
            progresso = min(total_q / meta_local, 1.0)
            st.caption(f"🚀 Meta ({filtro_concurso}): {int(total_q)} / {meta_local} Questões")
            st.progress(progresso, text=f"{progresso*100:.1f}%")
            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões", int(total_q), border=True)
            c2.metric("Precisão", f"{media_g:.1f}%", border=True)
            c3.metric("Revisões", pendentes, delta="Atenção" if pendentes > 0 else "Em dia", delta_color="inverse", border=True)
            if streak_atual > 0:
                c4.metric("🔥 Streak Global", f"{streak_atual} dias", delta="Focado!", delta_color="normal", border=True)
            else:
                c4.metric("❄️ Streak Global", "0 dias", delta=f"Recorde: {recorde_hist}", delta_color="off", border=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
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

            st.markdown("---")
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
        st.info("Comece registando um edital e depois um estudo.")

# === PÁGINA 2: NOVO REGISTRO (INTEGRADO AO EDITAL) ===
elif selected == "Novo Registro":
    st.title("📝 Lançamento Inteligente")
    
    if not editais:
        st.warning("⚠️ Nenhum Edital cadastrado. Vá em 'Gestão de Editais' primeiro.")
        # Fallback para manual
        opcoes_concurso = ["Avulso"]
    else:
        opcoes_concurso = list(editais.keys())

    with st.container(border=True):
        with st.form("form_estudo", clear_on_submit=True):
            c_data, c_conc = st.columns([1, 2])
            data_input = c_data.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            
            # --- O SEGREDO: SELEÇÃO EM CASCATA ---
            # O Streamlit recarrega ao mudar o selectbox se usarmos session_state, 
            # mas dentro de Form ele não atualiza dinamicamente. 
            # Solução: Selecionar Edital FORA do form ou usar lógica simples.
            # Aqui usaremos uma abordagem simplificada para o form funcionar:
            
            # Nota: Para interatividade total (escolhe Edital -> Muda Matéria), teríamos de tirar do st.form.
            # Mas vamos manter o form e usar caixas de seleção.
            
            concurso_sel = c_conc.selectbox("Concurso / Edital", options=opcoes_concurso)
            
            # Lógica para preencher matérias baseado no concurso escolhido
            # Obs: Dentro do form, ele vai pegar o estado atual.
            lista_materias = []
            if concurso_sel in editais:
                lista_materias = list(editais[concurso_sel].keys())
            
            # Se não houver matérias cadastradas ou for avulso, deixa digitar? 
            # Para "Concurseiro Bruto", forçamos o cadastro. Mas vamos deixar um input híbrido.
            if lista_materias:
                materia_sel = st.selectbox("Disciplina", options=lista_materias)
            else:
                materia_sel = st.text_input("Disciplina (Cadastre no Edital para aparecer na lista)")

            assunto = st.text_input("Assunto Específico")
            
            c1, c2 = st.columns(2)
            ac = c1.number_input("Acertos", min_value=0, step=1)
            tot = c2.number_input("Total", min_value=1, step=1)
            
            btn = st.form_submit_button("✅ Salvar Estudo", use_container_width=True)

        if btn:
            if not materia_sel:
                st.error("Preencha a matéria.")
            else:
                taxa_calc = (ac/tot)*100
                data_rev = calcular_revisao(data_input, taxa_calc)
                
                nova = pd.DataFrame([{
                    "Data_Estudo": data_input.strftime('%d/%m/%Y'),
                    "Concurso": concurso_sel, # Nova Coluna
                    "Materia": materia_sel,
                    "Assunto": assunto,
                    "Acertos": str(ac),
                    "Total": str(tot),
                    "Taxa": f"{taxa_calc:.1f}%",
                    "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
                }])
                
                st.session_state.df_dados = pd.concat([df, nova], ignore_index=True)
                salvar_dados(st.session_state.df_dados)
                st.success(f"Registrado para {concurso_sel}! Revisão: {data_rev.strftime('%d/%m/%Y')}")

# === PÁGINA 3: GESTÃO DE EDITAIS (NOVA) ===
elif selected == "Gestão de Editais":
    st.title("📑 Cadastro de Editais")
    st.markdown("Aqui você monta a sua estratégia. Cadastre os concursos e as matérias que vai estudar.")

    col_add, col_view = st.columns([1, 1])

    with col_add:
        with st.container(border=True):
            st.subheader("Adicionar Novo")
            novo_concurso = st.text_input("Nome do Concurso (ex: PF 2026)")
            nova_materia = st.text_input("Matéria (ex: Raciocínio Lógico)")
            
            if st.button("💾 Adicionar ao Sistema"):
                if novo_concurso and nova_materia:
                    # Carrega estado atual
                    editais_atuais = st.session_state.editais
                    
                    # Lógica de dicionário
                    if novo_concurso not in editais_atuais:
                        editais_atuais[novo_concurso] = {}
                    
                    # Adiciona matéria se não existir (inicializa com lista vazia de assuntos futuramente)
                    if nova_materia not in editais_atuais[novo_concurso]:
                        editais_atuais[novo_concurso][nova_materia] = []
                        st.session_state.editais = editais_atuais
                        salvar_editais(editais_atuais)
                        st.success(f"Adicionado: {nova_materia} em {novo_concurso}")
                        st.rerun()
                    else:
                        st.warning("Matéria já existe neste concurso.")
                else:
                    st.error("Preencha o nome e a matéria.")

    with col_view:
        st.subheader("Editais Cadastrados")
        if not editais:
            st.info("Nenhum edital cadastrado.")
        else:
            for conc, mats in editais.items():
                with st.expander(f"📁 {conc}"):
                    st.write("**Matérias:**")
                    for m in mats.keys():
                        st.text(f"- {m}")
                    
                    if st.button(f"Excluir {conc}", key=f"del_{conc}"):
                        del st.session_state.editais[conc]
                        salvar_editais(st.session_state.editais)
                        st.rerun()

# === PÁGINA 4: HISTÓRICO ===
elif selected == "Histórico":
    st.title("🗂️ Base de Dados Completa")
    
    if not df.empty:
        col_filtro, col_dl = st.columns([4, 1])
        with col_filtro:
            concursos_un = df['Concurso'].unique()
            filtro_conc = st.multiselect("Filtrar Concurso:", concursos_un, default=concursos_un)
        
        df_view = df.copy()
        if filtro_conc:
            df_view = df_view[df_view['Concurso'].isin(filtro_conc)]
            
        df_edit = st.data_editor(df_view, use_container_width=True, num_rows="dynamic", key="editor_hist")

        if not df_edit.equals(df_view):
            st.session_state.df_dados = df_edit
            salvar_dados(df_edit)
            st.rerun()
            
        with col_dl:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Excel", csv, "backup_full.csv", "text/csv", use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado.")
