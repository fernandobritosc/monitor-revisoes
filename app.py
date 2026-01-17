import streamlit as st
import pandas as pd
import datetime
import time
import re
import fitz  # PyMuPDF
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="COMMANDER ELITE", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0A0A0B; color: #E2E8F0; }
    header { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }
    .rev-card { background: #17171B; border: 1px solid #2D2D35; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #333; }
    .score-badge { background: #2D2D35; color: #FFF; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
    .stButton button { background: #1E1E24; border: 1px solid #3F3F46; border-radius: 6px; font-weight: 600; width: 100%; transition: 0.3s; }
    .stButton button:hover { background: #DC2626; border-color: #DC2626; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. LÓGICA DE DADOS ---
def get_editais():
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {"cargo": row.get('cargo') or "Geral", "materias": {}}
            if row.get('materia'): editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

# --- 4. O NOVO FATIADOR "BISTURI" (MAIS SIMPLES E PRECISO) ---
def fatiar_edital_bisturi(texto):
    """Fatia o edital focando apenas em números no início da linha, ignorando o resto."""
    linhas = texto.split('\n')
    materias = {}
    materia_atual = "MATÉRIA NÃO IDENTIFICADA"
    
    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
        
        # Identifica Matéria (Títulos em CAIXA ALTA sem números no começo)
        if linha.isupper() and not re.match(r'^\d', linha) and len(linha) > 5:
            materia_atual = linha
            materias[materia_atual] = []
            continue
            
        # Identifica Tópico (Deve começar com número)
        if re.match(r'^\d', linha):
            if materia_atual not in materias: materias[materia_atual] = []
            materias[materia_atual].append(linha)
        else:
            # Se não tem número, anexa ao tópico anterior (continuação)
            if materia_atual in materias and materias[materia_atual]:
                materias[materia_atual][-1] += " " + linha
    
    return {k: v for k, v in materias.items() if v}

# --- 5. FLUXO APP ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "🤖 Cadastrar via PDF"])
    
    with tabs[0]:
        editais = get_editais()
        for nome, dados in editais.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        st.subheader("🤖 Importador Automático")
        c1, c2 = st.columns(2)
        n_n, n_c = c1.text_input("Concurso"), c2.text_input("Cargo")
        pdf = st.file_uploader("Suba o PDF do Conteúdo Programático", type="pdf")
        
        if st.button("🚀 EXTRAIR TÓPICOS") and pdf and n_n:
            doc = fitz.open(stream=pdf.read(), filetype="pdf")
            texto = "\n".join([p.get_text() for p in doc])
            st.session_state.temp_ia = fatiar_edital_bisturi(texto)
            st.session_state.temp_n, st.session_state.temp_c = n_n, n_c
            doc.close()

        if "temp_ia" in st.session_state:
            for m, t in st.session_state.temp_ia.items():
                with st.expander(f"📚 {m}"):
                    # Mostra um por linha para você conferir
                    for item in t: st.write(item)
                    if st.button(f"Salvar {m}", key=f"ia_{m}"):
                        supabase.table("editais_materias").insert({"concurso": st.session_state.temp_n, "cargo": st.session_state.temp_c, "materia": m, "topicos": t}).execute()
                        st.toast(f"{m} salva!")
            if st.button("✅ FINALIZAR"): del st.session_state.temp_ia; st.rerun()

else:
    # --- INTERFACE DE ESTUDOS (REGISTRAR, DASHBOARD, ETC) ---
    missao = st.session_state.missao_ativa
    res_stats = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
    df = pd.DataFrame(res_stats.data)
    dados_edital = get_editais().get(missao, {})
    
    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], 
                           default_index=2)

    # Bloco Registrar (Garantido)
    if menu == "Registrar":
        st.subheader("📝 Registrar Questões")
        mats = list(dados_edital.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                mat = c1.selectbox("Matéria", mats)
                ass = c1.selectbox("Assunto", dados_edital['materias'].get(mat, ["Geral"]))
                dt = c2.date_input("Data")
                st.divider()
                ac = st.number_input("Acertos", 0)
                tot = st.number_input("Total", 1)
                if st.button("💾 SALVAR REGISTRO", type="primary"):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute()
                    st.rerun()
    
    # Adicione aqui os blocos de Dashboard, Revisões, Configurar e Histórico como nas versões anteriores
    elif menu == "Dashboard": st.write("Estatísticas em breve.")
    elif menu == "Revisões": st.write("Radar de revisões pronto.")
    elif menu == "Configurar": 
        # Interface manual para quando o PDF falhar
        st.subheader("⚙️ Configuração Manual")
        # (Código de configuração aqui)
