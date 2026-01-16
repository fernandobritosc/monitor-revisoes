import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Concursos", page_icon="💀", layout="wide")

DB_FILE = "estudos_data.csv"
META_QUESTOES = 2000 

# --- FUNÇÕES ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

# Inicializar
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()

df = st.session_state.df_dados

# --- BARRA LATERAL ---
with st.sidebar:
    c_logo, c_text = st.columns([1, 2])
    
    with c_logo:
        try:
            st.image("2498586-caveira-com-facas-gratis-vetor.jpg", width=80)
        except:
            st.warning("Imagem?")
            st.image("https://cdn-icons-png.flaticon.com/512/9203/9203029.png", width=70)

    with c_text:
        st.markdown("""
            <div style="padding-top: 10px;">
                <h3 style='margin: 0; padding: 0; font-size: 20px;'><b>Faca na Caveira</b></h3>
                <span style='color: #00E676; font-size: 14px; font-weight: bold; display: block; margin-top: -3px;'>Concursos</span>
            </div>
            """, unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title="Navegação",
        options=["Dashboard", "Novo Registro", "Histórico"], 
        icons=["bar-chart-line-fill", "plus-circle-fill", "table"], 
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
        df_calc = df.copy()
        df_calc['Acertos'] = pd.to_numeric(df_calc['Acertos'], errors='coerce').fillna(0)
        df_calc['Total'] = pd.to_numeric(df_calc['Total'], errors='coerce').fillna(1)
        df_calc['Data_Ordenacao'] = pd.to_datetime(df_calc['Proxima_Revisao'], dayfirst=True, errors='coerce')

        total_q = df_calc['Total'].sum()
        media_g = (df_calc['Acertos'].sum() / total_q * 100) if total_q > 0 else 0
        hoje = pd.Timestamp.now().normalize()
        pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje].shape[0]

        # 1. BARRA DE META
        progresso = min(total_q / META_QUESTOES, 1.0)
        st.caption(f"🚀 Meta: {int(total_q)} / {META_QUESTOES} Questões")
        st.progress(progresso, text=f"{progresso*100:.1f}% Concluído")
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Questões Feitas", int(total_q), border=True)
        col2.metric("Precisão Geral", f"{media_g:.1f}%", border=True)
        col3.metric("Revisões Pendentes", pendentes, delta="Atenção" if pendentes > 0 else "Em dia", delta_color="inverse", border=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 3. GRÁFICOS
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Desempenho por Matéria")
            df_g = df_calc.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
            fig = px.bar(df_g, x="Materia", y="Nota", color="Nota", range_y=[0,100], color_continuous_scale="RdYlGn", text_auto='.0f', labels={"Nota": "% Acerto"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            
        with g2:
            st.subheader("Consistência Diária")
            df_calc['Data_Real'] = pd.to_datetime(df_calc['Data_Estudo'], dayfirst=True, errors='coerce')
            df_t = df_calc.groupby("Data_Real")['Total'].sum().reset_index()
            fig2 = px.line(df_t, x="Data_Real", y="Total", markers=True, labels={"Data_Real": "Data", "Total": "Questões"})
            fig2.update_xaxes(tickformat="%d/%m", dtick="D1")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        # 4. MAPA DA VERGONHA (FILTRADO < 80%)
        st.markdown("---")
        st.subheader("🗺️ Mapa da Vergonha")
        
        try:
            # Agrupa e calcula
            df_resumo = df_calc.groupby(["Materia", "Assunto"])[["Acertos", "Total"]].sum().reset_index()
            df_resumo["Aproveitamento"] = (df_resumo["Acertos"] / df_resumo["Total"] * 100)
            
            # FILTRO: Só mostra quem está abaixo de 80%
            df_piores = df_resumo[df_resumo["Aproveitamento"] < 80].copy()
            
            # Ordena do pior para o "menos pior"
            df_piores = df_piores.sort_values(by="Aproveitamento", ascending=True)
            
            if not df_piores.empty:
                # Mensagem de "Puxão de Orelha"
                st.error("🚨 ALERTA: Estes assuntos vão te reprovar. TOMA RUMO e estuda isso hoje!")
                
                # Formatação
                df_piores["Aproveitamento"] = df_piores["Aproveitamento"].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(
                    df_piores[["Materia", "Assunto", "Total", "Aproveitamento"]].rename(columns={"Total": "Qtd. Feitas"}),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                # Se tudo estiver > 80%
                st.success("🏆 Nada no Mapa da Vergonha! Todos os teus assuntos estão acima de 80%. Mantém o foco!")

        except Exception as e:
            st.error(f"Erro ao calcular mapa: {e}")

    else:
        st.info("Sistema pronto. Comece pelo menu 'Novo Registro'.")

# === NOVO REGISTRO ===
elif selected == "Novo Registro":
    st.title("📝 Lançamento Operacional")
    
    with st.container(border=True):
        st.subheader("Relatório de Estudo")
        with st.form("form_estudo", clear_on_submit=True):
            c_data, c_materia = st.columns([1, 2])
            data_input = c_data.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            materia = c_materia.text_input("Disciplina")
            assunto = st.text_input("Assunto Específico")
            
            c1, c2 = st.columns(2)
            ac = c1.number_input("Qtd. Acertos", min_value=0, step=1)
            tot = c2.number_input("Qtd. Total", min_value=1, step=1)
            
            btn = st.form_submit_button("✅ Confirmar Lançamento", use_container_width=True)

        if btn and materia:
            taxa_calc = (ac/tot)*100
            data_rev = calcular_revisao(data_input, taxa_calc)
            
            nova = pd.DataFrame([{
                "Data_Estudo": data_input.strftime('%d/%m/%Y'),
                "Materia": materia,
                "Assunto": assunto,
                "Acertos": str(ac),
                "Total": str(tot),
                "Taxa": f"{taxa_calc:.1f}%",
                "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
            }])
            
            st.session_state.df_dados = pd.concat([df, nova], ignore_index=True)
            salvar_dados(st.session_state.df_dados)
            st.success(f"Registrado! Próxima missão: {data_rev.strftime('%d/%m/%Y')}")

# === HISTÓRICO ===
elif selected == "Histórico":
    st.title("🗂️ Base de Dados Tática")
    
    if not df.empty:
        col_filtro, col_dl = st.columns([4, 1])
        with col_filtro:
            filtro = st.multiselect("Filtrar Disciplina:", df['Materia'].unique())
        
        df_view = df.copy()
        if filtro:
            df_view = df_view[df_view['Materia'].isin(filtro)]
            
        st.caption("Dica: Use a tecla 'Delete' para remover linhas selecionadas.")
        df_edit = st.data_editor(df_view, use_container_width=True, num_rows="dynamic", key="editor_hist")

        if not df_edit.equals(df_view):
            st.session_state.df_dados = df_edit
            salvar_dados(df_edit)
            st.rerun()
            
        with col_dl:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Extrair Dados", csv, "backup_estudos.csv", "text/csv", use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado.")
