import streamlit as st
import pandas as pd
import datetime
import os

# Configuração da página
st.set_page_config(page_title="Monitor Pro", page_icon="🚀", layout="wide")

DB_FILE = "estudos_data.csv"

# --- FUNÇÕES DE DADOS (Mantidas e Blindadas) ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            # Criar coluna de data real para cálculos, mas mantendo a string original
            df['Data_Ordenacao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True, errors='coerce')
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    if 'Data_Ordenacao' in dataframe.columns:
        df_save = dataframe.drop(columns=['Data_Ordenacao'])
    else:
        df_save = dataframe
    df_save.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

# --- INÍCIO DA INTERFACE ---
st.title("🚀 Dashboard de Performance")

df = carregar_dados()

# --- BARRA LATERAL (Entrada de Dados) ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        data_input = st.date_input("Data do Estudo", datetime.date.today(), format="DD/MM/YYYY")
        materia = st.text_input("Matéria (Ex: Português)")
        assunto = st.text_input("Assunto (Ex: Crase)")
        
        c1, c2 = st.columns(2)
        ac = c1.number_input("Acertos", min_value=0, step=1)
        tot = c2.number_input("Total", min_value=1, step=1)
        
        btn = st.form_submit_button("Salvar Estudo")

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
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success(f"Salvo! Revisão: {data_rev.strftime('%d/%m/%Y')}")
        st.rerun()

    st.markdown("---")
    if st.button("🗑️ Apagar Último Registro"):
        if not df.empty:
            df = df.drop(df.index[-1])
            salvar_dados(df)
            st.warning("Apagado!")
            st.rerun()

# --- PAINEL PRINCIPAL (A Mágica Acontece Aqui) ---

if not df.empty:
    # 1. CÁLCULO DE MÉTRICAS (KPIs)
    # Converter para números para poder somar
    total_questoes = df['Total'].astype(int).sum()
    total_acertos = df['Acertos'].astype(int).sum()
    
    # Evitar divisão por zero
    media_global = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0
    
    # Contar revisões pendentes (Data de revisão <= Hoje)
    hoje = pd.Timestamp.now().normalize()
    # Garantir que Data_Ordenacao existe e é válida
    df['Data_Ordenacao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True, errors='coerce')
    pendentes = df[df['Data_Ordenacao'] <= hoje].shape[0]

    # Exibir os cartões
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("📚 Questões Resolvidas", total_questoes)
    col_kpi2.metric("🎯 Precisão Global", f"{media_global:.1f}%")
    col_kpi3.metric("🔥 Revisões Pendentes", pendentes, delta="Atenção" if pendentes > 0 else "Em dia", delta_color="inverse")

    st.markdown("---")

    # 2. ÁREA DE FILTROS E TABELA
    st.subheader("🔎 Filtros e Cronograma")
    
    # Filtro Multiselect
    lista_materias = df['Materia'].unique().tolist()
    filtro_materias = st.multiselect("Filtrar por Matéria:", options=lista_materias)
    
    # Aplicar o filtro na visualização (sem apagar os dados originais)
    df_view = df.copy()
    if filtro_materias:
        df_view = df_view[df_view['Materia'].isin(filtro_materias)]
    
    # Ordenação
    df_view = df_view.sort_values(by="Data_Ordenacao", ascending=True)
    
    # Visualização Limpa
    cols_display = ["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"]
    
    # Destaque condicional (Pintar de vermelho o que é urgente)
    def destacar_urgencia(val):
        try:
            data_val = pd.to_datetime(val, dayfirst=True)
            if data_val <= hoje:
                return 'color: red; font-weight: bold'
        except:
            pass
        return ''

    st.dataframe(
        df_view[cols_display].style.map(destacar_urgencia, subset=['Proxima_Revisao']),
        use_container_width=True,
        hide_index=True
    )

    # 3. EXPORTAÇÃO
    st.markdown("---")
    csv_excel = df_view[cols_display].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar Dados Filtrados (Excel)",
        data=csv_excel,
        file_name="meus_estudos_pro.csv",
        mime="text/csv"
    )

else:
    st.info("Começa a registar os teus estudos na barra lateral para veres as estatísticas!")
