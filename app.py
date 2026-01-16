import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# Configuração de elite da página
st.set_page_config(page_title="Monitor de Revisões", page_icon="📚", layout="wide")

st.title("🚀 Meu Monitor de Estudos")

# 1. Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Função para carregar dados de forma segura
def carregar_dados():
    try:
        # ttl=0 garante que lê sempre o dado mais fresco da nuvem
        dados = conn.read(ttl="0")
        return dados.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=["Materia", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

df = carregar_dados()

# 3. Lógica de Spaced Repetition (Revisão Espaçada)
def calcular_intervalo(taxa):
    hoje = datetime.date.today()
    if taxa < 70:
        return hoje + datetime.timedelta(days=1)  # Revisa amanhã
    elif taxa < 90:
        return hoje + datetime.timedelta(days=7)  # Revisa em 1 semana
    else:
        return hoje + datetime.timedelta(days=21) # Revisa em 3 semanas

# --- BARRA LATERAL: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📥 Novo Registro")
    # O uso de 'with st.form' evita que a página recarregue a cada clique
    with st.form("meu_formulario", clear_on_submit=True):
        materia = st.text_input("Assunto/Matéria")
        col1, col2 = st.columns(2)
        acertos = col1.number_input("Acertos", min_value=0, step=1)
        total = col2.number_input("Total Questões", min_value=1, step=1)
        botao_salvar = st.form_submit_button("Salvar Estudo")

    if botao_salvar:
        if materia:
            taxa_perc = (acertos / total) * 100
            data_prox = calcular_intervalo(taxa_perc)
            
            # Criar nova linha
            nova_linha = pd.DataFrame([{
                "Materia": materia,
                "Acertos": acertos,
                "Total": total,
                "Taxa": f"{taxa_perc:.1f}%",
                "Proxima_Revisao": str(data_prox)
            }])
            
            # Unir dados antigos com o novo
            df_final = pd.concat([df, nova_linha], ignore_index=True)
            
            # Gravar na nuvem
            try:
                conn.update(data=df_final)
                st.success(f"Registado! Revisão agendada para: {data_prox}")
                st.balloons() # Celebração visual
                st.rerun()
            except Exception as e:
                st.error("Erro ao gravar. Verifique se a folha está em modo 'Editor' no Google Sheets.")
        else:
            st.warning("Por favor, introduz o nome da matéria.")

# --- PAINEL PRINCIPAL: VISUALIZAÇÃO ---
st.subheader("📋 Minhas Revisões Agendadas")

if not df.empty:
    # Ordenar por data para mostrar o mais urgente primeiro
    df['Proxima_Revisao'] = pd.to_datetime(df['Proxima_Revisao']).dt.date
    df_sorted = df.sort_values(by="Proxima_Revisao")
    
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)
else:
    st.info("Ainda não existem dados. Faz o teu primeiro registo na barra lateral!")
