import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL PRO ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    header {visibility: hidden;}
    
    /* Botões */
    .stButton button {
        background-color: #1E1E1E;
        color: #E0E0E0;
        border: 1px solid #333;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    
    /* Métricas (Cards) */
    div[data-testid="stMetric"] {
        background-color: #0E0E0E;
        padding: 15px 20px;
        border-radius: 8px;
        border: 1px solid #222;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    /* Ajuste de Gráficos */
    .js-plotly-plot {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. FUNÇÕES DE DADOS ---

def get_data_countdown(data_iso):
    if not data_iso: return "A definir", None
    try:
        dt_prova = datetime.datetime.strptime(data_iso, '%Y-%m-%d').date()
        hoje = datetime.date.today()
        dias = (dt_prova - hoje).days
        data_fmt = dt_prova.strftime('%d/%m/%Y')

        if dias < 0: return data_fmt, "🏁 Concluída"
        if dias == 0: return data_fmt, "🚨 É HOJE!"
        if dias <= 30: return data_fmt, f"🔥 Reta Final: {dias} dias"
        return data_fmt, f"⏳ Faltam {dias} dias"
    except:
        return data_iso, None

def get_editais():
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {
                    "cargo": row.get('cargo') or "Geral", 
                    "data_iso": row.get('data_prova'),
                    "materias": {}
                }
            if row.get('materia'):
                editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

def get_stats(concurso):
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- 4. FLUXO PRINCIPAL ---

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# --- TELA 1: CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.markdown("## 💀 CENTRAL DE COMANDO")
    st.markdown("---")
    
    editais = get_editais()
    
    col_cards, col_admin = st.columns([2, 1], gap="large")
    
    with col_cards:
        st.subheader("🚀 Missões Ativas")
        if not editais:
            st.info("Nenhuma missão ativa.")
        else:
            for nome, dados in editais.items():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1.5])
                    with c1:
                        st.markdown(f"### {nome}")
                        st.caption(f"🎯 {dados['cargo']}")
                    with c2:
                        dt_str, status = get_data_countdown(dados['data_iso'])
                        st.markdown(f"📅 **Prova:** {dt_str}")
                        if status:
                            cor = "#FF4B4B" if "Reta Final" in status or "HOJE" in status else "#E0E0E0"
                            st.markdown(f"<span style='color:{cor}; font-weight:600; font-size:0.9em'>{status}</span>", unsafe_allow_html=True)
                    with c3:
                        st.write("") 
                        if st.button("ACESSAR", key=f"btn_{nome}", use_container_width=True):
                            st.session_state.missao_ativa = nome
                            st.rerun()

    with col_admin:
        st.subheader("🛠️ Gestão Rápida")
        with st.container(border=True):
            st.markdown("**➕ Nova Missão**")
            with st.form("quick_create"):
                nm = st.text_input("Nome (Ex: PF)")
                cg = st.text_input("Cargo")
                dt = st.date_input("Data da Prova", format="DD/MM/YYYY")
                
                if st.form_submit_button("CRIAR MISSÃO", use_container_width=True):
                    if nm:
                        supabase.table("editais_materias").insert({
                            "concurso": nm, "cargo": cg, 
                            "data_prova": dt.strftime('%Y-%m-%d'),
                            "materia": "Geral", "topicos": [], "usuario": "Commander"
                        }).execute()
                        st.toast(f"Missão {nm} criada!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Digite um nome.")

        st.write("") 
        with st.container(border=True):
            st.markdown("**🗑️ Zona de Perigo**")
            lista_del = ["Selecione..."] + list(editais.keys())
            alvo = st.selectbox("Apagar Missão:", lista_del)
            if alvo != "Selecione...":
                st.warning(f"Apagar TODO o histórico de '{alvo}'?")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").delete().eq("concurso", alvo).execute()
                    supabase.table("editais_materias").delete().eq("concurso", alvo).execute()
                    st.success("Missão eliminada.")
                    time.sleep(1)
                    st.rerun()

# --- TELA 2: MODO OPERACIONAL ---
else:
    missao = st.session_state.missao_ativa
    dados = get_editais().get(missao, {})
    df = get_stats(missao)
    
    with st.sidebar:
        st.markdown(f"## 🎯 {missao}")
        dt_str, status = get_data_countdown(dados.get('data_iso'))
        if status: st.caption(f"{status}")

        if st.button("🔙 VOLTAR AO COMANDO", use_container_width=True):
            st.session_state.missao_ativa = None
            st.rerun()
            
        st.markdown("---")
        menu = option_menu(
            menu_title=None,
            options=["Dashboard", "Registrar", "Configurar", "Histórico"],
            icons=["bar-chart-fill", "pencil-square", "gear-fill", "clock-history"],
            default_index=0,
            styles={"nav-link-selected": {"background-color": "#FF4B4B"}}
        )

    # --- DASHBOARD REORGANIZADO (AQUI ESTÁ A CORREÇÃO) ---
    if menu == "Dashboard":
        st.title("📊 Painel Tático")
        
        if df.empty:
            st.info("Aguardando dados de combate. Inicie os registros.")
        else:
            # 1. CARDS (LINHA DE CIMA)
            total = int(df['total'].sum())
            acertos = int(df['acertos'].sum())
            erros = total - acertos
            precisao = (acertos / total * 100) if total > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Questões Resolvidas", total)
            col2.metric("Acertos Totais", acertos)
            col3.metric("Precisão Atual", f"{precisao:.1f}%")
            
            st.markdown("---")
            
            # 2. GRÁFICOS (GRID 2 COLUNAS)
            g1, g2 = st.columns([2, 1], gap="medium")
            
            with g1:
                st.markdown("#### 📈 Evolução Temporal")
                df['Data'] = pd.to_datetime(df['data_estudo']).dt.strftime('%d/%m')
                df_chart = df.groupby('Data')[['total', 'acertos']].sum().reset_index()
                
                fig_area = px.area(df_chart, x='Data', y=['total', 'acertos'], 
                              color_discrete_sequence=['#333333', '#FF4B4B'],
                              labels={'value': 'Qtd', 'variable': 'Métrica'})
                
                # Ajuste Fino do Layout
                fig_area.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=350, # Altura travada
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_area, use_container_width=True)
                
            with g2:
                st.markdown("#### 🎯 Precisão Visual")
                # Gráfico de Rosca (Donut)
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['Acertos', 'Erros'], 
                    values=[acertos, erros],
                    hole=.6, # Faz o buraco do donut
                    marker=dict(colors=['#FF4B4B', '#333333']),
                    textinfo='percent'
                )])
                
                fig_pie.update_layout(
                    showlegend=True,
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=350, # Mesma altura do outro para alinhar
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

    elif menu == "Registrar":
        st.title("📝 Novo Registro")
        materias = list(dados.get('materias', {}).keys())
        
        if not materias:
            st.warning("⚠️ Adicione matérias em 'Configurar' antes de registrar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    mat = st.selectbox("Matéria", materias)
                    topicos = dados['materias'].get(mat, []) or ["Geral"]
                    assunto = st.selectbox("Assunto", topicos)
                with c2:
                    dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                
                st.divider()
                c3, c4 = st.columns(2)
                acertos = c3.number_input("Acertos", min_value=0, step=1)
                total = c4.number_input("Total", min_value=1, step=1)
                
                if st.button("SALVAR REGISTRO", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": assunto,
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": acertos,
                        "total": total, "taxa": (acertos/total)*100, "usuario": "Commander"
                    }).execute()
                    st.toast("Salvo!", icon="🔥")
                    time.sleep(0.5)

    elif menu == "Configurar":
        st.title("⚙️ Configuração")
        c1, c2 = st.columns([1, 2], gap="medium")
        
        with c1:
            st.markdown("#### Nova Matéria")
            with st.form("add_mat"):
                nm = st.text_input("Nome")
                if st.form_submit_button("ADICIONAR"):
                    supabase.table("editais_materias").insert({
                        "concurso": missao, "materia": nm, "topicos": [],
                        "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso'),
                        "usuario": "Commander"
                    }).execute()
                    st.rerun()
        
        with c2:
            st.markdown("#### Matérias")
            for m, t in dados.get('materias', {}).items():
                with st.expander(f"📚 {m}"):
                    current = "; ".join(t)
                    new_tops = st.text_area(f"Tópicos", value=current, key=f"t_{m}")
                    c_s, c_d = st.columns([4, 1])
                    if c_s.button("Salvar", key=f"s_{m}"):
                        l = [x.strip() for x in new_tops.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                        st.toast("Atualizado!")
                        time.sleep(0.5); st.rerun()
                    if c_d.button("🗑️", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()

    elif menu == "Histórico":
        st.title("📜 Histórico")
        if not df.empty:
            df_view = df.copy()
            df_view['data_estudo'] = pd.to_datetime(df_view['data_estudo']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_view[['data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']], use_container_width=True, hide_index=True)
        else: st.info("Sem dados.")
