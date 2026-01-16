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
            # Lemos com o separador ';' que é o padrão que o Excel BR/PT gosta
            df = pd.read_csv(DB_FILE, sep=';')
            # Converter colunas de data para o formato real do Python para podermos ordenar
            df['Data_Estudo'] = pd.to_datetime(df['Data_Estudo'], dayfirst=True)
            df['Proxima_Revisao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True)
            return df
        except:
            # Se o ficheiro antigo estiver corrompido ou em formato errado, recomeçamos
            return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    # Guardamos as datas de forma legível no CSV
    df_para_salvar = dataframe.copy()
    df_para_salvar['Data_Estudo'] = df_para_salvar['Data_Estudo'].dt.strftime('%d/%m/%Y')
    df_para_salvar['Proxima_Revisao'] = df_para_salvar['Proxima_Revisao'].dt.strftime('%d/%m/%Y')
    df_para_salvar.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    # Garante que somamos à data que o usuário escolheu
    return data_base + datetime.timedelta(days=dias)

# --- INTERFACE ---
st.title("🎯 Monitor de Revisão Espaçada")

df = carregar_dados()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        data_input = st.date_input("Data do Estudo", datetime.date.today())
        materia = st.text_input("Matéria")
        assunto = st.text_input("Assunto")
        
        col1, col2 = st.columns(2)
        ac = col1.number_input("Acertos", min_value=0, step=1)
        tot = col2.number_input("Total Questões", min_value=1, step=1)
        
        btn = st.form_submit_button("Salvar Estudo")

    if btn and materia:
        taxa_calc = (ac/tot)*100
        # O data_input já vem como objeto de data do Python
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
        st.success(f"Registado! Próxima revisão: {data_rev.strftime('%d/%m/%Y')}")
        st.balloons()
        st.rerun()

# --- PAINEL PRINCIPAL ---
st.subheader("📋 Histórico de Estudos")

if not df.empty:
    # Ordenar por data da próxima revisão (o mais urgente primeiro)
    df_view = df.sort_values(by="Proxima_Revisao").copy()
    
    # Formatar as datas apenas para exibição na tela
    df_view['Data_Estudo'] = df_view['Data_Estudo'].dt.strftime('%d/%m/%Y')
    df_view['Proxima_Revisao'] = df_view['Proxima_Revisao'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    
    # Botão de Backup para Excel
    st.markdown("---")
    csv_excel = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar para Excel (CSV)",
        data=csv_excel,
        file_name=f"meus_estudos_{datetime.date.today().strftime('%d_%m_%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("Ainda não há registros. Use a barra lateral para começar!")
