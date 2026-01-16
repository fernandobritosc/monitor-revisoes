import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Monitor Pro", page_icon="🚀", layout="wide")

DB_FILE = "estudos_data.csv"

# --- FUNÇÕES DE DADOS ---
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

# --- INTERFACE ---
st.title("🚀 Dashboard de Performance")

if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()

df = st.session_state.df_dados

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        data_input = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
        materia = st.text_input("Matéria")
        assunto = st.text_input("Assunto")
        c1, c2 = st.columns(2)
        ac = c1.number_input("Acertos", min_value=0, step=1)
        tot = c2.number_input("Total", min_value=1, step=1)
        btn = st.form_submit_button("Salvar")

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
        st.success("Salvo!")
        st.rerun()

# --- PAINEL PRINCIPAL ---

if not st.session_state.df_dados.empty:
    df_calc = st.session_state.df_dados.copy()
    
    # Tratamento de dados para gráficos
    df_calc['Acertos'] = pd.to_numeric(df_calc['Acertos'], errors='coerce').fillna(0)
    df_calc['Total'] = pd.to_numeric(df_calc['Total'], errors='coerce').fillna(1)
    df_calc['Data_Ordenacao'] = pd.to_datetime(df_calc['Proxima_Revisao'], dayfirst=True, errors='coerce')

    # 1. KPIs
    total_q = df_calc['Total'].sum()
    media_g = (df_calc['Acertos'].sum() / total_q * 100) if total_q > 0 else 0
    hoje = pd.Timestamp.now().normalize()
    pendentes = df_calc[df_calc['Data_Ordenacao'] <= hoje].shape[0]

    k1, k2, k3 = st.columns(3)
    k1.metric("📚 Questões", int(total_q))
    k2.metric("🎯 Precisão Global", f"{media_g:.1f}%")
    k3.metric("🔥 Revisões Hoje", pendentes, delta="Atenção" if pendentes > 0 else "Em dia", delta_color="inverse")

    st.markdown("---")

    # 2. ABAS (Gráficos e Tabela)
    t1, t2 = st.tabs(["📊 Gráficos", "📝 Gestão de Registros"])
    
    with t1:
        g1, g2 = st.columns(2)
        
        # Gráfico de Barras (Matérias)
        with g1:
            st.caption("Desempenho por Matéria")
            df_g = df_calc.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
            fig_barras = px.bar(df_g, x="Materia", y="Nota", color="Nota", range_y=[0,100], color_continuous_scale="RdYlGn", text_auto='.0f')
            st.plotly_chart(fig_barras, use_container_width=True)
        
        # Gráfico de Linha (Ritmo) - AQUI ESTÁ A CORREÇÃO
        with g2:
            st.caption("Ritmo Diário")
            df_calc['Data_Real'] = pd.to_datetime(df_calc['Data_Estudo'], dayfirst=True, errors='coerce')
            df_t = df_calc.groupby("Data_Real")['Total'].sum().reset_index()
            
            fig_linha = px.line(df_t, x="Data_Real", y="Total", markers=True)
            
            # --- O COMANDO MÁGICO DE FORMATAÇÃO ---
            fig_linha.update_xaxes(
                tickformat="%d/%m",  # Mostra apenas Dia/Mês (ex: 16/01)
                dtick="D1"           # Força um traço por dia (evita horas quebradas)
            )
            
            st.plotly_chart(fig_linha, use_container_width=True)

    # 3. TABELA EDITÁVEL
    with t2:
        st.subheader("📝 Editar ou Excluir")
        st.info("Selecione a caixinha à esquerda da linha e pressione DEL no teclado para apagar.")
        
        df_editado = st.data_editor(
            st.session_state.df_dados,
            use_container_width=True,
            num_rows="dynamic",
            key="editor_dados"
        )

        if not df_editado.equals(st.session_state.df_dados):
            st.session_state.df_dados = df_editado
            salvar_dados(df_editado)
            st.rerun()

    # 4. DOWNLOAD
    csv = st.session_state.df_dados.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Baixar Excel", csv, "meus_estudos.csv", "text/csv")

else:
    st.info("Começa a registar na barra lateral!")
