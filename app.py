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
        try:
            df = pd.read_csv(DB_FILE, sep=';')
            df['Data_Estudo'] = pd.to_datetime(df['Data_Estudo'], dayfirst=True)
            df['Proxima_Revisao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True)
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    df_para_salvar = dataframe.copy()
    # Garante que salva no CSV como texto legível para o Excel
    df_para_salvar['Data_Estudo'] = df_para_salvar['Data_Estudo'].dt.strftime('%d/%m/%Y')
    df_para_salvar['Proxima_Revisao'] = df_para_salvar['Proxima_Revisao'].dt.strftime('%d/%m/%Y')
    df_para_salvar.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

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
        # O seletor de data agora tentará usar o formato local do seu sistema
        data_input = st.date_input("Data do Estudo (Dia/Mês/Ano)", datetime.date.today())
        
        materia = st.text_input("Matéria")
        assunto = st.text_input("Assunto")
        
        col1, col2 = st.columns(2)
        ac = col1.number_input("Acertos", min_value=0, step=1)
        tot = col2.number_input("Total Questões", min_value=1, step=1)
        
        btn = st.form_submit_button("Salvar Estudo")

    if btn and materia:
        taxa_calc = (ac/tot)*100
        data_rev = calcular_revisao(data_input, taxa_calc)
        
        nova_linha = pd.DataFrame([{
            "Data_Estudo": pd.to_datetime(data_input),
            "Materia": materia,
            "Assunto": assunto,
            "Acertos": ac,
            "Total": tot,
            "Taxa": f"{taxa_calc:.1f}%",
            "Proxima_Revisao": pd.to_datetime(data_rev)
        }])
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success(f"Registrado! Próxima revisão: {data_rev.strftime('%d/%m/%Y')}")
        st.balloons()
        st.rerun()

    # --- BOTÃO DE APAGAR (Fica fora do formulário) ---
    st.markdown("---")
    if st.button("🗑️ Apagar Último Registro"):
        if not df.empty:
            df = df.drop(df.index[-1])
            salvar_dados(df)
            st.warning("Último registro removido!")
            st.rerun()

# --- PAINEL PRINCIPAL ---
st.subheader("📋 Histórico de Estudos")

if not df.empty:
    df_view = df.sort_values(by="Proxima_Revisao", ascending=True).copy()
    
    # Formatação visual da tabela
    df_view['Data_Estudo'] = df_view['Data_Estudo'].dt.strftime('%d/%m/%Y')
    df_view['Proxima_Revisao'] = df_view['Proxima_Revisao'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    
    # Backup
    csv_excel = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar para Excel",
        data=csv_excel,
        file_name=f"meus_estudos_{datetime.date.today().strftime('%d_%m_%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("Ainda não há registros. Use a barra lateral para começar!")
