import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px  # Nova biblioteca para gráficos

# Configuração da página
st.set_page_config(page_title="Monitor Pro", page_icon="🚀", layout="wide")

DB_FILE = "estudos_data.csv"

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            # Converter colunas numéricas para fazer contas
            df['Acertos'] = pd.to_numeric(df['Acertos'], errors='coerce').fillna(0)
            df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(1)
            # Data para ordenação
            df['Data_Ordenacao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True, errors='coerce')
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    df_save = dataframe.copy()
    if 'Data_Ordenacao' in df_save.columns:
        df_save = df_save.drop(columns=['Data_Ordenacao'])
    df_save.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

# --- INÍCIO DA INTERFACE ---
st.title("🚀 Dashboard de Performance")

df = carregar_dados()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Novo Registro")
    with st.form("form_estudo", clear_on_submit=True):
        data_input = st.date_input("Data do Estudo", datetime.date.today(), format="DD/MM/YYYY")
        materia = st.text_input("Matéria")
        assunto = st.text_input("Assunto")
        
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
            "Acertos": ac,
            "Total": tot,
            "Taxa": f"{taxa_calc:.1f}%",
            "Proxima_Revisao": data_rev.strftime('%d/%m/%Y')
        }])
        
        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)
        st.success("Salvo!")
        st.rerun()

    st.markdown("---")
    if st.button("🗑️ Apagar Último"):
        if not df.empty:
            df = df.drop(df.index[-1])
            salvar_dados(df)
            st.warning("Apagado!")
            st.rerun()

# --- PAINEL PRINCIPAL ---

if not df.empty:
    # 1. KPIs
    total_questoes = df['Total'].sum()
    total_acertos = df['Acertos'].sum()
    media_global = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0
    
    hoje = pd.Timestamp.now().normalize()
    df['Data_Ordenacao'] = pd.to_datetime(df['Proxima_Revisao'], dayfirst=True, errors='coerce')
    pendentes = df[df['Data_Ordenacao'] <= hoje].shape[0]

    k1, k2, k3 = st.columns(3)
    k1.metric("📚 Questões", int(total_questoes))
    k2.metric("🎯 Precisão Global", f"{media_global:.1f}%")
    k3.metric("🔥 Revisões Hoje", pendentes, delta_color="inverse")

    st.markdown("---")

    # 2. GRÁFICOS (NOVA SECÇÃO)
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("📊 Desempenho por Matéria")
        # Agrupar dados para calcular média por matéria
        df_agrupado = df.groupby("Materia").apply(
            lambda x: (x['Acertos'].sum() / x['Total'].sum() * 100)
        ).reset_index(name="Precisão")
        
        fig_barras = px.bar(
            df_agrupado, 
            x="Materia", 
            y="Precisão", 
            color="Precisão",
            range_y=[0, 100],
            color_continuous_scale="RdYlGn", # Vermelho para baixo, Verde para alto
            text_auto='.1f'
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    with g2:
        st.subheader("📈 Ritmo de Estudos")
        # Contar questões por data (precisamos converter a string de data para objeto data real)
        df['Data_Real'] = pd.to_datetime(df['Data_Estudo'], dayfirst=True, errors='coerce')
        df_tempo = df.groupby("Data_Real")['Total'].sum().reset_index()
        
        fig_linha = px.line(
            df_tempo, 
            x="Data_Real", 
            y="Total", 
            markers=True
        )
        st.plotly_chart(fig_linha, use_container_width=True)

    st.markdown("---")

    # 3. TABELA COM FILTROS
    st.subheader("🔎 Detalhes")
    
    materias = df['Materia'].unique().tolist()
    filtro = st.multiselect("Filtrar Matéria:", materias)
    
    df_view = df.copy()
    if filtro:
        df_view = df_view[df_view['Materia'].isin(filtro)]
    
    df_view = df_view.sort_values(by="Data_Ordenacao")
    
    # Função de destaque
    def style_rows(row):
        try:
            d = pd.to_datetime(row['Proxima_Revisao'], dayfirst=True)
            if d <= hoje:
                return ['background-color: #ff4b4b20'] * len(row) # Vermelho suave
        except: pass
        return [''] * len(row)

    cols = ["Data_Estudo", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"]
    st.dataframe(
        df_view[cols].style.apply(style_rows, axis=1), 
        use_container_width=True, 
        hide_index=True
    )

    # 4. DOWNLOAD
    csv = df_view[cols].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Baixar Excel", csv, "estudos.csv", "text/csv")

else:
    st.info("Regista o teu primeiro estudo para veres os gráficos!")
