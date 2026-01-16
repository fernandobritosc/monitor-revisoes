import streamlit as st
import pandas as pd
import datetime
import os

# Configuração da página
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide")

DB_FILE = "estudos_data.csv"

# Função para carregar os dados
def carregar_dados():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Materia", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

# Função para guardar os dados
def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False)

# Lógica de Revisão Espaçada
def calcular_revisao(taxa):
    hoje = datetime.date.today()
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return hoje + datetime.timedelta(days=dias)

st.title("🎯 Sistema de Revisão Blindado")

df = carregar_dados()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        mat = st.text_input("Matéria/Assunto")
        c1, c2 = st.columns(2)
        ac = c1.number_input("Acertos", min_value=0, step=1)
        tot = c2.number_input("Total", min_value=1, step=1)
        btn = st.form_submit_button("Salvar Estudo")

    if btn and mat:
        taxa_calc = (ac/tot)*100
        data_rev = calcular_revisao(taxa_calc)
        
        nova_linha = pd.DataFrame([{
            "Materia": mat, "Acertos": ac, "Total": tot, 
            "Taxa": f"{taxa_calc:.1f}%", "Proxima_Revisao": str(data_rev)
        }])
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success(f"Salvo! Revisar em: {data_rev}")
        st.balloons()
        st.rerun()

# --- PAINEL PRINCIPAL ---
st.subheader("📋 Cronograma de Estudos")
if not df.empty:
    # Destacar o que é para hoje
    hoje = str(datetime.date.today())
    def highlight_hoje(s):
        return ['background-color: #ff4b4b' if v <= hoje else '' for v in s]
    
    st.dataframe(df.style.apply(highlight_hoje, subset=['Proxima_Revisao']), use_container_width=True)
else:
    st.info("Ainda não há dados. Começa a registar agora!")
