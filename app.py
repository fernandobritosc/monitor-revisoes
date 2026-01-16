import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# Configuração da página
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

st.title("🚀 Meu Monitor de Estudos")

# Tentar conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
    st.success("Conectado à nuvem com sucesso!")
except Exception as e:
    st.error("Erro de conexão: Verifique se o link da planilha está nos Secrets.")
    st.info("Acesse: Manage App -> Settings -> Secrets")
    df = pd.DataFrame(columns=["Materia", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

# --- Interface de Registro ---
with st.sidebar:
    st.header("📥 Novo Registro")
    materia = st.text_input("Matéria")
    ac = st.number_input("Acertos", min_value=0, step=1)
    tot = st.number_input("Total", min_value=1, step=1)
    
    if st.button("Salvar Estudo"):
        taxa = (ac/tot)*100
        prox = datetime.date.today() + datetime.timedelta(days=7) # Simplificado para teste
        
        nova_linha = pd.DataFrame([{"Materia": materia, "Acertos": ac, "Total": tot, "Taxa": taxa, "Proxima_Revisao": str(prox)}])
        df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
        
        conn.update(data=df_atualizado)
        st.success("Salvo!")
        st.rerun()

# --- Exibição ---
st.subheader("📋 Minhas Revisões")
st.dataframe(df, use_container_width=True)
