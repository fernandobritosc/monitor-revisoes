import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# Configuração da página
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

st.title("🚀 Meu Monitor de Estudos")

# 1. Estabelecer conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Ler os dados (ttl=0 para ler sempre o mais recente)
try:
    df = conn.read(ttl="0")
    # Remover linhas totalmente vazias que o Google Sheets às vezes cria
    df = df.dropna(how="all")
except Exception:
    df = pd.DataFrame(columns=["Materia", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

# --- LÓGICA DE REVISÃO ---
def calcular_proxima(taxa):
    hoje = datetime.date.today()
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return hoje + datetime.timedelta(days=dias)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        materia = st.text_input("Assunto/Matéria")
        col1, col2 = st.columns(2)
        ac = col1.number_input("Acertos", min_value=0, step=1)
        tot = col2.number_input("Total", min_value=1, step=1)
        botao = st.form_submit_button("Salvar Estudo")

    if botao:
        taxa_calc = (ac/tot)*100
        prox_data = calcular_proxima(taxa_calc)
        
        # Criar nova linha formatada
        nova_linha = pd.DataFrame([{
            "Materia": materia,
            "Acertos": ac,
            "Total": tot,
            "Taxa": f"{taxa_calc:.1f}%",
            "Proxima_Revisao": str(prox_data)
        }])
        
        # Atualizar a folha
        df_final = pd.concat([df, nova_linha], ignore_index=True)
        conn.update(data=df_final)
        st.success(f"Registado! Revisão em: {prox_data}")
        st.balloons()
        st.rerun()

# --- EXIBIÇÃO ---
st.subheader("📋 Painel de Revisões")
if not df.empty:
    # Mostra o que é prioridade (datas passadas ou hoje)
    hoje_str = str(datetime.date.today())
    
    st.dataframe(
        df.sort_values(by="Proxima_Revisao"),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Ainda não há dados. Começa a registar na barra lateral!")
