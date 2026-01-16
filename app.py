import streamlit as st
import pandas as pd
import datetime
import time
from supabase import create_client, Client
from streamlit_option_menu import option_menu
# Tenta importar o Docling, se não estiver instalado, avisa o usuário
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="COMMANDER AI", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0A0A0B; color: #E2E8F0; }
    header { visibility: hidden; }
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; }
    .rev-card { background: #17171B; border: 1px solid #2D2D35; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. LÓGICA DOCLING (PENSAR FORA DA CAIXA) ---
def processar_edital_com_docling(uploaded_file):
    if not DOCLING_AVAILABLE:
        st.error("Biblioteca 'docling' não instalada. Adicione ao requirements.txt")
        return None
    
    with st.spinner("🤖 Docling analisando estrutura do PDF..."):
        # Salva arquivo temporário para o Docling ler
        with open("temp_edital.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        converter = DocumentConverter()
        result = converter.convert("temp_edital.pdf")
        markdown_text = result.document.export_to_markdown()
        
        # Aqui simplificamos: pegamos o texto e quebramos em linhas
        # Em um sistema real, usaríamos uma LLM para limpar esse Markdown
        return markdown_text

# --- 4. FUNÇÕES DE APOIO ---
def get_editais():
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {"cargo": row.get('cargo') or "Geral", "data_iso": row.get('data_prova'), "materias": {}}
            if row.get('materia'): editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

# --- 5. FLUXO APP ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    
    menu_top = option_menu(None, ["Missões", "Importar Edital (AI)"], 
                         icons=["list-stars", "file-earmark-pdf-fill"], 
                         menu_icon="cast", default_index=0, orientation="horizontal")

    if menu_top == "Missões":
        editais = get_editais()
        for nome, dados in editais.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome} | {dados['cargo']}")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()

    elif menu_top == "Importar Edital (AI)":
        st.subheader("🚀 Importação Automática via Docling")
        st.info("Suba o PDF do edital e o sistema extrairá as matérias automaticamente.")
        
        with st.container(border=True):
            nome_concurso = st.text_input("Nome do Concurso (Sigla)")
            cargo = st.text_input("Cargo")
            pdf_file = st.file_uploader("Escolha o Edital (PDF)", type="pdf")
            
            if st.button("INICIAR EXTRAÇÃO INTELIGENTE") and pdf_file and nome_concurso:
                texto_extraido = processar_edital_com_docling(pdf_file)
                if texto_extraido:
                    st.success("PDF processado com sucesso!")
                    with st.expander("Ver Conteúdo Extraído"):
                        st.markdown(texto_extraido)
                    
                    st.warning("⚠️ Agora o Commander precisa que você confirme a divisão de matérias.")
                    # Aqui poderíamos disparar a gravação no banco
                    # Para teste, vamos simular uma entrada:
                    if st.button("CONFIRMAR E CRIAR MISSÃO"):
                        supabase.table("editais_materias").insert({
                            "concurso": nome_concurso, "cargo": cargo, "materia": "Extraído via AI", "topicos": [texto_extraido[:200] + "..."]
                        }).execute()
                        st.rerun()

else:
    # ... (O restante do código de Dashboard, Revisões e Histórico permanece o mesmo da v63)
    st.write(f"Você está na missão: {st.session_state.missao_ativa}")
    if st.button("Voltar"): st.session_state.missao_ativa = None; st.rerun()
