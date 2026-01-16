import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="Monitor de Revisões", layout="wide")
st.title("🚀 Meu Monitor de Estudos")

# Conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0").dropna(how="all")
    st.success("Conectado à nuvem com sucesso!")
except Exception as e:
    st.error("Erro de conexão.")
    df = pd.DataFrame(columns=["Materia", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

# --- LÓGICA DE REVISÃO ---
def calcular_proxima_data(taxa):
    hoje = datetime.date.today()
    if taxa < 70:
        return hoje + datetime.timedelta(days=1)  # Revisa amanhã (reforço)
    elif taxa < 90:
        return hoje + datetime.timedelta(days=7)  # Revisa em 1 semana
    else:
        return hoje + datetime.timedelta(days=21) # Revisa em 3 semanas

# --- SIDEBAR ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("meu_form"):
        materia = st.text_input("Matéria")
        ac = st.number_input("Acertos", min_value=0, step=1)
        tot = st.number_input("Total", min_value=1, step=1)
        enviar = st.form_submit_button("Salvar Estudo")

    if enviar:
        taxa_calc = (ac/tot)*100
        prox_data = calcular_proxima_data(taxa_calc)
        
        nova_linha = pd.DataFrame([{
            "Materia": materia, 
            "Acertos": ac, 
            "Total": tot, 
            "Taxa": f"{taxa_calc:.2f}%", 
            "Proxima_Revisao": str(prox_data)
        }])
        
        df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
        conn.update(data=df_atualizado)
        st.balloons() # Comemoração visual!
        st.rerun()

# --- EXIBIÇÃO ---
st.subheader("📋 Minhas Revisões Agendadas")
if not df.empty:
    # Ordenar pela data mais próxima
    df_sorted = df.sort_values(by="Proxima_Revisao")
    st.dataframe(df_sorted, use_container_width=True)
else:
    st.info("Nenhum dado registado ainda.")
