import streamlit as st
import pandas as pd
import datetime
import os

# Configuração da página
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide")

DB_FILE = "estudos_data.csv"

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Garante que as datas são lidas como texto para não haver confusão de formato
        return df
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False)

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

# --- INTERFACE ---
st.title("🎯 Monitor de Revisão Espaçada")

df = carregar_dados()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        # Novo campo de Data de Estudo
        data_estudo = st.date_input("Data do Estudo", datetime.date.today())
        
        materia = st.text_input("Matéria (Ex: Direito Constitucional)")
        assunto = st.text_input("Assunto (Ex: Direitos Fundamentais)")
        
        col1, col2 = st.columns(2)
        ac = col1.number_input("Acertos", min_value=0, step=1)
        tot = col2.number_input("Total Questões", min_value=1, step=1)
        
        btn = st.form_submit_button("Salvar Estudo")

    if btn and materia and assunto:
        taxa_calc = (ac/tot)*100
        # Calcula a revisão com base na data que escolheste no seletor
        data_rev = calcular_revisao(data_estudo, taxa_calc)
        
        # Formatação das datas para o padrão 15/01/2026
        nova_linha = pd.DataFrame([{
            "Data_Estudo": data_estudo.strftime('%d/%m/%Y'),
            "Materia": materia,
            "Assunto": assunto,
            "Acertos": ac,
            "Total": tot,
            "Taxa": f"{taxa_calc:.1f}%",
            "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
        }])
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success(f"Salvo! Próxima revisão em: {data_rev.strftime('%d/%m/%Y')}")
        st.balloons()
        st.rerun()

# --- PAINEL PRINCIPAL ---
st.subheader("📋 Histórico e Cronograma")

if not df.empty:
    # Exibir a tabela com as colunas organizadas
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Botão de Backup
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descarregar Backup (Excel/CSV)",
        data=csv,
        file_name=f"revisoes_{datetime.date.today()}.csv",
        mime="text/csv",
    )
else:
    st.info("Ainda não há dados. Começa a registar os teus estudos!")
