import streamlit as st
import pandas as pd
import datetime
import time
import re
import fitz  # PyMuPDF
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
    .card-subject { font-weight: 800; font-size: 0.85rem; color: #FFF; }
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

# --- 4. IA: FATIAMENTO POR NUMERAÇÃO (REFINADO) ---
def fatiar_edital_blindado(texto):
    """Fatia o edital respeitando a numeração (1, 1.1, 2...) e ignora vírgulas internas."""
    linhas = texto.split('\n')
    progresso = {}
    materia_atual = None
    blacklist = ["ANEXO", "CONTEÚDO", "PROGRAMÁTICO", "PROVA", "EDITAL", "RESULTADO"]

    for linha in linhas:
        linha = linha.strip()
        if not linha or len(linha) < 3: continue
        
        # 1. Identifica Matéria (Títulos curtos em CAIXA ALTA)
        if linha.isupper() and len(linha) < 50:
            if any(word in linha for word in blacklist): continue
            materia_atual = linha
            progresso[materia_atual] = []
            continue

        if materia_atual:
            # 2. Identifica Tópicos pela numeração (Ex: 1 tópico, 1.1 subtópico)
            # Procura por padrões como "1 ", "1.1 ", "10. ", "2.1.3 "
            partes = re.split(r'(\d+(?:\.\d+)*\s+[A-ZÀ-Ú])', linha)
            
            if len(partes) > 1:
                # Reconstroi os tópicos fatiados pela regex
                for i in range(1, len(partes), 2):
                    topico_completo = (partes[i] + partes[i+1]).strip()
                    if len(topico_completo) > 5:
                        progresso[materia_atual].append(topico_completo)
            else:
                # Se não tem número mas a linha é grande, pode ser a continuação de um tópico
                if len(linha) > 10:
                    if progresso[materia_atual]:
                        progresso[materia_atual][-1] += " " + linha
                    else:
                        progresso[materia_atual].append(linha)

    # Limpeza de caracteres residuais
    for m in progresso:
        progresso[m] = [t.replace('  ', ' ').strip() for t in progresso[m]]
        
    return {k: v for k, v in progresso.items() if len(v) > 0}

# --- 5. FLUXO CENTRAL ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "🤖 Cadastrar via IA"])
    
    with tabs[0]:
        editais = get_editais()
        if not editais: st.info("Nenhum concurso ativo.")
        for nome, dados in editais.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()

    with tabs[1]:
        st.subheader("🤖 Novo Concurso Inteligente")
        c1, c2 = st.columns(2)
        novo_n = c1.text_input("Concurso")
        novo_c = c2.text_input("Cargo")
        pdf = st.file_uploader("Upload do Conteúdo Programático", type="pdf")
        
        if st.button("🚀 ANALISAR PDF") and pdf and novo_n:
            with st.spinner("Fatiando por tópicos numerados..."):
                doc = fitz.open(stream=pdf.read(), filetype="pdf")
                texto = "\n".join([page.get_text() for page in doc])
                st.session_state.temp_ia = fatiar_edital_blindado(texto)
                st.session_state.temp_n = novo_n
                st.session_state.temp_c = novo_c
                doc.close()

        if "temp_ia" in st.session_state:
            res = st.session_state.temp_ia
            for m, t in res.items():
                with st.expander(f"📚 {m} ({len(t)} tópicos)"):
                    st.write("\n".join([f"**{i+1}.** {item}" for i, item in enumerate(t)]))
                    if st.button(f"💾 SALVAR {m}", key=f"ia_{m}"):
                        supabase.table("editais_materias").insert({
                            "concurso": st.session_state.temp_n,
                            "cargo": st.session_state.temp_c,
                            "materia": m, "topicos": t
                        }).execute()
                        st.toast(f"{m} salva com sucesso!")
            if st.button("✅ FINALIZAR"):
                del st.session_state.temp_ia
                st.rerun()
else:
    # (O restante do código de Dashboard, Revisões, Registrar, Configurar e Histórico permanece o mesmo das versões anteriores)
    # Copiar aqui o bloco "else" da v89.0 para manter as funcionalidades internas.
    st.sidebar.title(f"🎯 {st.session_state.missao_ativa}")
    if st.sidebar.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
    st.write("Acesse as abas laterais para gerenciar seus estudos.")
