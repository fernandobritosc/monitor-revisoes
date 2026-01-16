import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Monitor Pro", page_icon="📚", layout="wide")

DB_FILE = "estudos_data.csv"

# --- FUNÇÕES (Mantidas iguais) ---
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

# Carregar dados
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()

df = st.session_state.df_dados

# --- MENU LATERAL (Versão Vibrante) ---
with st.sidebar:
    # Um logo opcional no topo (podes trocar o link se quiseres)
    st.image("https://cdn-icons-png.flaticon.com/512/2232/2232688.png", width=60)
    st.markdown("## **Estudei Pro**") # Título em negrito para destacar
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Novo Registro", "Histórico"], 
        icons=["graph-up-arrow", "plus-circle-fill", "table"], 
        menu_icon="cast", 
        default_index=0,
        styles={
            # Fundo do menu (branco/cinza claro para destacar os botões)
            "container": {"padding": "5!important", "background-color": "#f8f9fa"},
            
            # Ícones (Verde escuro para contraste forte)
            "icon": {"color": "#1b5e20", "font-size": "20px"}, 
            
            # O texto dos botões não selecionados
            "nav-link": {
                "font-size": "18px", 
                "text-align": "left", 
                "margin": "5px", 
                "--hover-color": "#e8f5e9" # Um verde bem clarinho ao passar o rato
            },
            
            # A COR VIBRANTE (Botão Selecionado)
            "nav-link-selected": {"background-color": "#00C853"}, 
        }
    )
    
    st.markdown("---")
    st.caption("v. 2.1 - Foco Total 🚀")

# --- LÓGICA DAS PÁGINAS ---

# === PÁGINA 1: DASHBOARD ===
if selected == "Dashboard":
    st.title("📊 Painel Geral")
    
    if not df.empty:
        df_calc = df.copy()
        df_calc['Acertos'] = pd.to_numeric(df_calc['Acertos'], errors='coerce').fillna(0)
        df_calc['Total'] = pd.to_numeric(df_calc['Total'], errors='coerce').fillna(1)
        df_calc['Data_Ordenacao'] = pd.to_datetime(df_calc['Proxima_Revisao'], dayfirst=True, errors='coerce')

        # KPIs
        total_q = df_calc['Total'].sum()
        media_g = (df_calc['Acertos'].sum() / total_q * 100) if total_q > 0 else 0
        hoje = pd.Timestamp.now().normalize()
        pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje].shape[0]

        k1, k2, k3 = st.columns(3)
        k1.metric("Questões Resolvidas", int(total_q))
        k2.metric("Precisão Global", f"{media_g:.1f}%")
        k3.metric("Revisões Pendentes", pendentes, delta="Atenção" if pendentes > 0 else "Em dia", delta_color="inverse")

        st.markdown("---")
        
        # Gráficos Lado a Lado
        g1, g2 = st.columns(2)
        
        with g1:
            st.subheader("Desempenho por Matéria")
            df_g = df_calc.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
            fig_barras = px.bar(
                df_g, x="Materia", y="Nota", color="Nota", 
                range_y=[0,100], color_continuous_scale="RdYlGn", text_auto='.0f',
                labels={"Nota": "Aproveitamento (%)"}
            )
            st.plotly_chart(fig_barras, use_container_width=True)
            
        with g2:
            st.subheader("Ritmo de Estudos")
            df_calc['Data_Real'] = pd.to_datetime(df_calc['Data_Estudo'], dayfirst=True, errors='coerce')
            df_t = df_calc.groupby("Data_Real")['Total'].sum().reset_index()
            
            fig_linha = px.line(
                df_t, x="Data_Real", y="Total", markers=True,
                labels={"Data_Real": "Data", "Total": "Questões"}
            )
            fig_linha.update_xaxes(tickformat="%d/%m", dtick="D1")
            st.plotly_chart(fig_linha, use_container_width=True)
            
    else:
        st.info("Ainda não há dados. Vá ao menu 'Novo Registro' para começar!")

# === PÁGINA 2: NOVO REGISTRO ===
elif selected == "Novo Registro":
    st.title("📝 Lançar Novo Estudo")
    st.markdown("Preencha os dados abaixo para alimentar suas estatísticas.")
    
    with st.container(border=True):
        with st.form("form_estudo", clear_on_submit=True):
            c_data, c_materia = st.columns([1, 2])
            data_input = c_data.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            materia = c_materia.text_input("Matéria (Ex: Direito Constitucional)")
            
            assunto = st.text_input("Assunto (Ex: Direitos Fundamentais)")
            
            c1, c2, c3 = st.columns(3)
            ac = c1.number_input("Acertos", min_value=0, step=1)
            tot = c2.number_input("Total", min_value=1, step=1)
            
            # Botão de envio grande
            btn = st.form_submit_button("💾 Salvar Registro", use_container_width=True)

        if btn and materia:
            taxa_calc = (ac/tot)*100
            data_rev = calcular_revisao(data_input, taxa_calc)
            
            nova_linha = pd.DataFrame([{
                "Data_Estudo": data_input.strftime('%d/%m/%Y'),
                "Materia": materia,
                "Assunto": assunto,
                "Acertos": str(ac),
                "Total": str(tot),
                "Taxa": f"{taxa_calc:.1f}%",
                "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
            }])
            
            st.session_state.df_dados = pd.concat([df, nova_linha], ignore_index=True)
            salvar_dados(st.session_state.df_dados)
            st.success(f"✅ Registro salvo! Próxima revisão agendada para: {data_rev.strftime('%d/%m/%Y')}")
            # Não usamos rerun aqui para permitir lançar vários seguidos rapidamente

# === PÁGINA 3: HISTÓRICO ===
elif selected == "Histórico":
    st.title("🗂️ Histórico Completo")
    
    if not df.empty:
        # Filtros no topo
        col_filtro, col_download = st.columns([3, 1])
        with col_filtro:
            filtro_materia = st.multiselect("Filtrar por Matéria:", df['Materia'].unique())
        
        df_view = df.copy()
        if filtro_materia:
            df_view = df_view[df_view['Materia'].isin(filtro_materia)]
        
        # Tabela Editável
        st.info("💡 Edite os valores diretamente na tabela. Selecione a linha e pressione 'Delete' para apagar.")
        df_editado = st.data_editor(
            df_view,
            use_container_width=True,
            num_rows="dynamic",
            key="editor_historico",
            column_config={
                "Taxa": st.column_config.TextColumn("Aproveitamento", disabled=True),
                "Proxima_Revisao": st.column_config.TextColumn("Revisão", disabled=True)
            }
        )

        if not df_editado.equals(df_view):
            # Lógica complexa de atualização para manter a integridade se houver filtros
            # Por segurança, neste modo simples, atualizamos o estado global
            st.session_state.df_dados = df_editado
            salvar_dados(df_editado)
            st.success("Alterações salvas!")
            st.rerun()
            
        # Botão Download
        with col_download:
            st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
            csv = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar Excel", csv, "historico.csv", "text/csv", use_container_width=True)
            
    else:
        st.warning("Nenhum registro encontrado.")
