import streamlit as st
import pandas as pd
import datetime
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad", page_icon="💀", layout="wide")

DB_FILE = "estudos_data.csv"
EDITAIS_FILE = "editais_db.json"
META_QUESTOES = 2000 
# LISTA DE AMIGOS (Edita aqui os nomes da tua equipa)
GUERREIROS = ["Fernando", "Lucas", "André", "Tiago"]

# --- FUNÇÕES ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

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

# --- INICIALIZAÇÃO E LOGIN ---
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()
if 'editais' not in st.session_state:
    st.session_state.editais = carregar_editais()

# VACINA DE DADOS (Compatibilidade com versões anteriores)
mudou = False
if "Concurso" not in st.session_state.df_dados.columns:
    st.session_state.df_dados["Concurso"] = "Geral"
    mudou = True
if "Usuario" not in st.session_state.df_dados.columns:
    # Se não tinha usuário antes, assume que tudo é do dono (primeiro da lista)
    st.session_state.df_dados["Usuario"] = GUERREIROS[0]
    mudou = True

if mudou:
    salvar_dados(st.session_state.df_dados)
    st.rerun()

# --- TELA DE LOGIN ---
if 'usuario_logado' not in st.session_state:
    c_log1, c_log2, c_log3 = st.columns([1, 2, 1])
    with c_log2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("2498586-caveira-com-facas-gratis-vetor.jpg", width=150)
        st.markdown("## 💀 Identifique-se, Guerreiro!")
        
        usuario_selecionado = st.selectbox("Selecione o seu perfil:", GUERREIROS)
        
        if st.button("ENTRAR NA BASE", type="primary", use_container_width=True):
            st.session_state.usuario_logado = usuario_selecionado
            st.rerun()
    st.stop() # Para a execução aqui se não estiver logado

# --- SE ESTIVER LOGADO, CONTINUA ---
usuario_atual = st.session_state.usuario_logado
df = st.session_state.df_dados
editais = st.session_state.editais

# Filtra os dados APENAS do usuário logado para uso pessoal
df_user = df[df['Usuario'] == usuario_atual].copy()

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
                <span style='color: #00E676; font-size: 14px; font-weight: bold; display: block; margin-top: -3px;'>Squad Edition</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.info(f"👤 Logado como: **{usuario_atual}**")
    if st.button("Sair / Trocar"):
        del st.session_state.usuario_logado
        st.rerun()

    selected = option_menu(
        menu_title="Painel Tático",
        options=["Dashboard", "Novo Registro", "Ranking do Squad", "Gestão de Editais", "Histórico"], 
        icons=["bar-chart-line-fill", "plus-circle-fill", "trophy-fill", "journal-bookmark-fill", "table"], 
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

# --- CONTEÚDO ---

# === DASHBOARD (DADOS PESSOAIS) ===
if selected == "Dashboard":
    st.title(f"📊 Painel de {usuario_atual}")
    
    if not df_user.empty:
        lista_concursos = ["Todos"] + sorted(list(df_user['Concurso'].unique()))
        filtro_concurso = st.selectbox("Visualizar dados de:", lista_concursos)
        
        df_view = df_user.copy()
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
            df_pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje]
            qtd_pendentes = df_pendentes.shape[0]
            
            streak_atual, recorde_hist = calcular_metricas_streak(df_user) # Streak Pessoal

            meta_local = META_QUESTOES if filtro_concurso == "Todos" else int(META_QUESTOES / 2)
            progresso = min(total_q / meta_local, 1.0)
            st.caption(f"🚀 Meta ({filtro_concurso}): {int(total_q)} / {meta_local}")
            st.progress(progresso, text=f"{progresso*100:.1f}%")
            st.markdown("<br>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões", int(total_q), border=True)
            c2.metric("Precisão", f"{media_g:.1f}%", border=True)
            c3.metric("Revisões", qtd_pendentes, delta="Fazer Hoje!" if qtd_pendentes > 0 else "Em dia", delta_color="inverse", border=True)
            c4.metric("🔥 Streak", f"{streak_atual} dias", delta=f"Recorde: {recorde_hist}", border=True)

            st.markdown("---")
            t_missoes, t_cobertura = st.tabs(["📅 Missões", "🛡️ Cobertura"])
            
            with t_missoes:
                if qtd_pendentes > 0:
                    st.error(f"🚨 {qtd_pendentes} Revisões Pendentes!")
                    st.dataframe(df_pendentes[["Concurso", "Materia", "Assunto", "Proxima_Revisao"]], use_container_width=True, hide_index=True)
                else:
                    st.success("Tudo pago por hoje! 💀")

            with t_cobertura:
                if not editais:
                    st.info("Cadastre um edital.")
                else:
                    conc_analise = filtro_concurso if filtro_concurso != "Todos" else st.selectbox("Selecione:", list(editais.keys()))
                    if conc_analise in editais:
                        dados_edital = editais[conc_analise]
                        for mat, topicos in dados_edital.get("materias", {}).items():
                            total = len(topicos)
                            if total > 0:
                                df_mat = df_user[(df_user['Concurso'] == conc_analise) & (df_user['Materia'] == mat)]
                                validos = [t for t in df_mat['Assunto'].unique() if t in topicos]
                                perc = len(validos) / total
                                st.write(f"**{mat}** ({len(validos)}/{total})")
                                st.progress(perc)

            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("🕸️ Radar Tático")
                df_r = df_calc.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
                if not df_r.empty:
                    fig = go.Figure(data=go.Scatterpolar(r=df_r['Nota'], theta=df_r['Materia'], fill='toself', line_color='#00E676', mode='lines+markers+text', text=[f"{n:.0f}%" for n in df_r['Nota']], textposition='top center', textfont=dict(color="#00E676", size=11, weight="bold")))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)), showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=40,r=40,t=20,b=20))
                    st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.subheader("📈 Evolução")
                df_calc['Data_Real'] = pd.to_datetime(df_calc['Data_Estudo'], dayfirst=True, errors='coerce')
                df_t = df_calc.groupby("Data_Real")['Total'].sum().reset_index()
                fig2 = px.line(df_t, x="Data_Real", y="Total", markers=True)
                fig2.update_traces(line_color='#00E676')
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info(f"Bem-vindo, {usuario_atual}. Comece um registo para ver as estatísticas.")

# === NOVO REGISTRO ===
elif selected == "Novo Registro":
    st.title("📝 Lançamento")
    st.caption(f"Registrando estudo para: **{usuario_atual}**")
    
    if not editais:
        st.warning("Cadastre Editais primeiro.")
        concurso_sel = "Avulso"
        materias_possiveis, topicos_possiveis = [], []
    else:
        concurso_sel = st.selectbox("Concurso:", list(editais.keys()))
        materias_possiveis = list(editais[concurso_sel].get("materias", {}).keys())
        materia_sel = st.selectbox("Disciplina:", materias_possiveis) if materias_possiveis else None
        topicos_possiveis = editais[concurso_sel]["materias"][materia_sel] if materia_sel else []

    with st.container(border=True):
        with st.form("form_estudo", clear_on_submit=True):
            c_data, c_assunto = st.columns([1, 2])
            data_input = c_data.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            
            if topicos_possiveis:
                assunto = c_assunto.selectbox("Assunto:", topicos_possiveis)
            else:
                assunto = c_assunto.text_input("Assunto")
            
            c1, c2 = st.columns(2)
            ac = c1.number_input("Acertos", min_value=0, step=1)
            tot = c2.number_input("Total", min_value=1, step=1)
            
            if st.form_submit_button("✅ Salvar para Mim", use_container_width=True):
                if not materia_sel and concurso_sel != "Avulso":
                    st.error("Erro: Matéria inválida.")
                else:
                    mat_final = materia_sel if materia_sel else "Geral"
                    taxa = (ac/tot)*100
                    rev = calcular_revisao(data_input, taxa)
                    nova = pd.DataFrame([{
                        "Data_Estudo": data_input.strftime('%d/%m/%Y'),
                        "Usuario": usuario_atual, # SALVA COM O NOME DO USUARIO ATUAL
                        "Concurso": concurso_sel, 
                        "Materia": mat_final,
                        "Assunto": assunto,
                        "Acertos": str(ac), "Total": str(tot), "Taxa": f"{taxa:.1f}%",
                        "Proxima_Revisao": rev.strftime('%d/%m/%Y')
                    }])
                    st.session_state.df_dados = pd.concat([df, nova], ignore_index=True)
                    salvar_dados(st.session_state.df_dados)
                    st.success("Salvo com sucesso!")

# === RANKING DO SQUAD (A NOVIDADE) ===
elif selected == "Ranking do Squad":
    st.title("🏆 Ranking dos Caveiras")
    st.markdown("Quem está pagando o preço da aprovação?")
    
    if not df.empty:
        # Prepara dados globais (converte numeros)
        df_rank = df.copy()
        df_rank['Total'] = pd.to_numeric(df_rank['Total'], errors='coerce').fillna(0)
        df_rank['Acertos'] = pd.to_numeric(df_rank['Acertos'], errors='coerce').fillna(0)
        
        # 1. Ranking por Volume de Questões
        st.subheader("🔥 Volume Total de Questões")
        rank_vol = df_rank.groupby("Usuario")['Total'].sum().reset_index().sort_values("Total", ascending=False)
        rank_vol['Rank'] = range(1, len(rank_vol) + 1) # Adiciona posição 1º, 2º...
        
        # Gráfico de Barras Horizontal
        fig_rank = px.bar(rank_vol, x="Total", y="Usuario", orientation='h', text="Total", color="Usuario", 
                          color_discrete_sequence=px.colors.qualitative.Dark24)
        fig_rank.update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_rank, use_container_width=True)

        # 2. Tabela Detalhada com Precisão e Streak
        st.subheader("📊 Detalhes Táticos")
        
        # Calcula metricas complexas por usuario
        detalhes = []
        for u in df_rank['Usuario'].unique():
            df_u = df_rank[df_rank['Usuario'] == u]
            total = df_u['Total'].sum()
            acertos = df_u['Acertos'].sum()
            media = (acertos / total * 100) if total > 0 else 0
            streak, _ = calcular_metricas_streak(df_u)
            detalhes.append({"Guerreiro": u, "Questões": int(total), "Precisão": f"{media:.1f}%", "Streak Atual": f"{streak} dias"})
        
        df_detalhes = pd.DataFrame(detalhes).sort_values("Questões", ascending=False)
        st.dataframe(df_detalhes, use_container_width=True, hide_index=True)
        
    else:
        st.info("Ainda não há dados suficientes para o ranking.")

# === GESTÃO DE EDITAIS (COMPARTILHADA) ===
elif selected == "Gestão de Editais":
    st.title("📑 Edital Compartilhado")
    st.info("💡 Nota: Os editais são compartilhados entre todos os usuários.")
    
    with st.expander("➕ Criar Novo Concurso"):
        c1, c2, c3 = st.columns(3)
        novo_nome = c1.text_input("Nome")
        novo_cargo = c2.text_input("Cargo")
        nova_data = c3.date_input("Data", format="DD/MM/YYYY") 
        if st.button("Criar"):
            if novo_nome and novo_nome not in editais:
                editais[novo_nome] = {"cargo": novo_cargo, "data_prova": nova_data.strftime('%Y-%m-%d'), "materias": {}}
                salvar_editais(editais)
                st.rerun()

    if editais:
        conc = st.selectbox("Editar:", list(editais.keys()))
        dados = editais[conc]
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("#### Add Matéria")
            nm = st.text_input("Nome Matéria")
            if st.button("Salvar Matéria") and nm:
                if nm not in dados["materias"]:
                    dados["materias"][nm] = []
                    salvar_editais(editais)
                    st.rerun()
        
        with c2:
            st.markdown("#### Tópicos")
            for mat, topicos in dados.get("materias", {}).items():
                with st.expander(f"{mat} ({len(topicos)})"):
                    txt = st.text_area(f"Importar para {mat}:", height=68, key=f"t_{mat}")
                    if st.button("Importar", key=f"b_{mat}") and txt:
                        novos = [x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()]
                        topicos.extend(novos)
                        salvar_editais(editais)
                        st.rerun()
                    st.dataframe(pd.DataFrame(topicos, columns=["Tópicos"]), hide_index=True)

# === HISTÓRICO (APENAS O MEU) ===
elif selected == "Histórico":
    st.title("🗂️ Meus Registros")
    if not df_user.empty:
        df_edit = st.data_editor(df_user, use_container_width=True, num_rows="dynamic", key="editor_hist")
        if not df_edit.equals(df_user):
            # Atualiza apenas as linhas deste usuario no DF original
            # (Simplificação: Removemos as antigas deste usuario e colocamos as novas)
            # Obs: Em produção real, usariamos IDs, mas para CSV local isso funciona se nao mudarem o nome.
            df_outros = df[df['Usuario'] != usuario_atual]
            df_final = pd.concat([df_outros, df_edit], ignore_index=True)
            st.session_state.df_dados = df_final
            salvar_dados(df_final)
            st.rerun()
    else:
        st.warning("Sem dados.")
