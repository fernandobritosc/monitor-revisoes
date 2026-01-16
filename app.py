import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string
import version

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS ---

@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['dt_ordenacao'] = pd.to_datetime(df['data_estudo'])
        df['Data'] = df['dt_ordenacao'].dt.strftime('%d/%m/%Y')
        df = df.sort_values('dt_ordenacao', ascending=False)
    return df

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- LOGIN ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        with st.form("login_f"):
            u = st.selectbox("Guerreiro", list(users.keys()))
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                if p == users[u]['pin']:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else: st.error("Acesso Negado.")
    st.stop()

# --- AMBIENTE OPERACIONAL ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu Tático", menus, default_index=0)
    
    st.markdown("---")
    st.caption(f"🚀 Versão: {version.VERSION}")
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# 1. DASHBOARD COM ANALYTICS
if selected == "Dashboard":
    st.title("📊 Termômetro de Desempenho")
    if not df_meu.empty:
        # Métricas Gerais
        total_q = int(df_meu['total'].sum())
        total_a = int(df_meu['acertos'].sum())
        precisao_geral = (total_a / total_q * 100) if total_q > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Questões Totais", total_q, border=True)
        c2.metric("Precisão Geral", f"{precisao_geral:.1f}%", border=True)
        
        status_geral = "🟢 ELITE" if precisao_geral >= 80 else "🟡 ALERTA" if precisao_geral >= 50 else "🔴 CRÍTICO"
        c3.metric("Status do Squad", status_geral, border=True)

        st.markdown("---")
        
        # --- LÓGICA DO TERMÔMETRO POR MATÉRIA ---
        st.subheader("🔥 Performance por Matéria")
        
        # Agrupar dados por matéria
        df_mat = df_meu.groupby('materia').agg({'acertos': 'sum', 'total': 'sum'}).reset_index()
        df_mat['Precisão'] = (df_mat['acertos'] / df_mat['total'] * 100).round(1)
        
        # Definir cores
        def get_color(p):
            if p >= 80: return '#00E676' # Verde
            if p >= 50: return '#FFD600' # Amarelo
            return '#FF5252'             # Vermelho

        df_mat['Cor'] = df_mat['Precisão'].apply(get_color)
        df_mat = df_mat.sort_values('Precisão', ascending=False)

        # Gráfico de Barras Horizontal
        fig_mat = px.bar(df_mat, x='Precisão', y='materia', orientation='h',
                         text='Precisão',
                         color='Precisão',
                         color_continuous_scale=['#FF5252', '#FFD600', '#00E676'],
                         range_color=[0, 100])
        
        fig_mat.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_mat, use_container_width=True)

        # Tabela Detalhada com Ícones
        st.markdown("### 📋 Raio-X das Matérias")
        for index, row in df_mat.iterrows():
            p = row['Precisão']
            icone = "🟢" if p >= 80 else "🟡" if p >= 50 else "🔴"
            st.write(f"{icone} **{row['materia']}**: {p}% ({int(row['acertos'])}/{int(row['total'])} questões)")
            st.progress(p/100)

    else: st.info("Registre o seu primeiro estudo para ativar o termômetro.")

# (Manter os outros menus Novo Registro, Gestão Editais, Ranking, Histórico e Gestão de Sistema iguais à v12.0.1)
# ... [O restante do código permanece idêntico ao anterior para manter a estabilidade] ...
