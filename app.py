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

# --- 4. IA: FATIAMENTO ATIVO POR NUMERAÇÃO (RECONSTRUÍDO) ---
def fatiar_edital_definitivo(texto):
    """Divide o texto toda vez que encontra um padrão de numeração (1, 2, 3.1)."""
    # Remove quebras de linha duplas para unificar o bloco de texto
    texto_unificado = re.sub(r'\s+', ' ', texto)
    
    materias_detectadas = {}
    blacklist = ["ANEXO", "CONTEÚDO", "PROGRAMÁTICO", "PROVA", "EDITAL", "VAGAS"]

    # Passo 1: Isolar possíveis títulos de matérias (Tudo em CAIXA ALTA com mais de 8 letras)
    partes = re.split(r'(\b[A-ZÀ-Ú\s]{8,}\b(?::|\n|$))', texto_unificado)
    
    materia_atual = "GERAL"
    for item in partes:
        item = item.strip()
        if not item: continue
        
        if item.isupper() and len(item) < 60 and not any(word in item for word in blacklist):
            materia_atual = item
            materias_detectadas[materia_atual] = []
        else:
            # Passo 2: O "Corte Cirúrgico". 
            # Procura por: Início da linha ou Espaço + Número + Ponto Opcional + Espaço + Letra Maiúscula
            # Ex: " 1 Noções", " 3.1 Conceito", " 10 Agentes"
            topicos_fatiados = re.split(r'(\s\d+(?:\.\d+)*\s+[A-ZÀ-Ú])', item)
            
            if len(topicos_fatiados) > 1:
                for i in range(1, len(topicos_fatiados), 2):
                    texto_final = (topicos_fatiados[i] + topicos_fatiados[i+1]).strip()
                    if materia_atual not in materias_detectadas: materias_detectadas[materia_atual] = []
                    # Limpa excesso de espaços
                    materias_detectadas[materia_atual].append(re.sub(r'\s+', ' ', texto_final))
            else:
                if len(item) > 10:
                    if materia_atual not in materias_detectadas: materias_detectadas[materia_atual] = []
                    materias_detectadas[materia_atual].append(re.sub(r'\s+', ' ', item))

    return {k: v for k, v in materias_detectadas.items() if len(v) > 0}

# --- 5. FLUXO APP ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "🤖 Cadastrar via PDF"])
    
    with tabs[0]:
        ed = get_editais()
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        st.subheader("🤖 Importador Inteligente")
        c1, c2 = st.columns(2)
        n_n, n_c = c1.text_input("Concurso"), c2.text_input("Cargo")
        pdf = st.file_uploader("Upload PDF", type="pdf")
        
        if st.button("🚀 EXTRAIR TÓPICOS") and pdf and n_n:
            doc = fitz.open(stream=pdf.read(), filetype="pdf")
            texto_bruto = "\n".join([p.get_text() for p in doc])
            st.session_state.temp_ia = fatiar_edital_definitivo(texto_bruto)
            st.session_state.temp_n, st.session_state.temp_c = n_n, n_c
            doc.close()

        if "temp_ia" in st.session_state:
            for m, t in st.session_state.temp_ia.items():
                with st.expander(f"📚 {m} ({len(t)} tópicos)"):
                    # Exibição organizada para conferência
                    for item in t: st.markdown(f"• {item}")
                    if st.button(f"Salvar {m}", key=f"ia_{m}"):
                        supabase.table("editais_materias").insert({
                            "concurso": st.session_state.temp_n, 
                            "cargo": st.session_state.temp_c, 
                            "materia": m, "topicos": t
                        }).execute()
                        st.toast(f"{m} salva!")
            if st.button("✅ FINALIZAR"): del st.session_state.temp_ia; st.rerun()

else:
    # --- INTERFACE DE ESTUDOS COMPLETA ---
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
                st.divider(); ac = st.number_input("Acertos", 0); tot = st.number_input("Total", 1)
                if st.button("💾 SALVAR REGISTRO", type="primary"):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": ass, 
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, 
                        "taxa": (ac/tot*100) if tot > 0 else 0,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute(); st.rerun()

    elif menu == "Dashboard":
        # (Lógica de Dashboard mantida)
        st.subheader("📊 Performance Geral")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            c1, c2 = st.columns(2)
            c1.metric("Questões", int(tot)); c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            df_g = df.copy(); df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            st.plotly_chart(px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626']), use_container_width=True)

    elif menu == "Configurar":
        st.subheader("⚙️ Configuração do Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Add"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados_edital.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos (um por linha)", "\n".join(t), key=f"t_{m}", height=150)
                if st.button("Salvar Matéria", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                if st.button("🗑️ Excluir Matéria", key=f"d_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()
