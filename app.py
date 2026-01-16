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
        # Lemos com o separador ';' para garantir compatibilidade com Excel
        df = pd.read_csv(DB_FILE, sep=';')
        return df
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    # Salvamos com ';' para o Excel abrir direto em colunas
    dataframe.to_csv(DB_FILE, index=False, sep=';')

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
        # Seletor de data (Calendário)
        data_input = st.date_input("Data do Estudo", datetime.date.today())
        
        materia = st.text_input("Matéria")
        assunto = st.text_input("Assunto")
        
        col1, col2 = st.columns(2)
        ac = col1.number_input("Acertos", min_value=0, step=1)
        tot = col2.number_input("Total Questões", min_value=1, step=1)
        
        btn = st.form_submit_button("Salvar Estudo")

    if btn and materia:
        taxa_calc = (ac/tot)*100
        data_rev = calcular_revisao(data_input, taxa_calc)
        
        # Guardamos as datas no formato DD/MM/YYYY para exibição e Excel
        nova_linha = pd.DataFrame([{
            "Data_Estudo": data_input.strftime('%d/%m/%Y'),
            "Materia": materia,
            "Assunto": assunto,
            "Acertos": ac,
            "Total": tot,
            "Taxa": f"{taxa_calc:.1f}%",
            "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
        }])
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success(f"Registado! Próxima revisão: {data_rev.strftime('%d/%m/%Y')}")
        st.balloons()
        st.rerun()

# --- PAINEL PRINCIPAL ---
st.subheader("📋 Histórico de Estudos")

if not df.empty:
    # Exibir a tabela organizada
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Botão de Backup ajustado para Excel
    st.markdown("---")
    # Para o backup, usamos o formato CSV mas com separador de ponto e vírgula
    csv_excel = df.to_csv(index=False, sep=';').encode('utf-8-sig') # 'utf-8-sig' ajuda o Excel com acentos
    st.download_button(
        label="📥 Baixar para Excel (CSV)",
        data=csv_excel,
        file_name=f"meus_estudos_{datetime.date.today()}.csv",
        mime="text/csv",
    )
else:
    st.info("Ainda não há registros. Use a barra lateral para começar!")
