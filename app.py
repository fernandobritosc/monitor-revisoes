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
    .perf-bad { border-left-color: #EF4444; }
    .perf-med { border-left-color: #F59E0B; }
    .perf-good { border-left-color: #10B981; }
    .card-subject { font-weight: 800; font-size: 0.85rem; color: #FFF; }
    .card-topic { font-size: 0.75rem; color: #94A3B8; margin-top: 4px; line-height: 1.2; }
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

def get_stats(concurso):
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).order("data_estudo", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def calcular_pendencias(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    pendencias = []
    for col in ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']:
        if col not in df.columns: df[col] = False
    for _, row in df.iterrows():
        delta = (hoje - row['dt_temp']).days
        taxa = row.get('taxa', 0)
        css = "perf-bad" if taxa < 60 else "perf-med" if taxa < 80 else "perf-good"
        base = {"id": row['id'], "Mat": row['materia'], "Ass": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Taxa": taxa, "CSS": css}
        if delta >= 30 and not row['rev_30d']: pendencias.append({**base, "Fase": "30d", "Label": "💎 D30"})
        elif delta >= 15 and not row['rev_15d']: pendencias.append({**base, "Fase": "15d", "Label": "🧠 D15"})
        elif delta >= 7 and not row['rev_07d']: pendencias.append({**base, "Fase": "07d", "Label": "📅 D7"})
        elif delta >= 1 and not row['rev_24h']: pendencias.append({**base, "Fase": "24h", "Label": "🔥 D1"})
    return pd.DataFrame(pendencias)

# --- 4. IA: FATIAMENTO REFINADO ---
def fatiar_edital_blindado(texto):
    texto_limpo = re.sub(r'\s+', ' ', texto)
    materia_atual = "GERAL"
    materias_detectadas = {}
    blacklist = ["ANEXO", "CONTEÚDO", "PROGRAMÁTICO", "PROVA", "EDITAL", "VAGAS"]
    
    # Divide primeiro por possíveis títulos de matérias (CAIXA ALTA)
    partes = re.split(r'([A-ZÀ-Ú\s]{8,}(?::|\n|$))', texto_limpo)
    
    for item in partes:
        item = item.strip()
        if not item: continue
        if item.isupper() and len(item) < 50 and not any(word in item for word in blacklist):
            materia_atual = item
            materias_detectadas[materia_atual] = []
        else:
            # Separa por numeração: " 1 ", " 2 ", " 3.1 "
            topicos = re.split(r'(\s\d+(?:\.\d+)*[\.\s]+[A-ZÀ-Ú])', item)
            if len(topicos) > 1:
                for j in range(1, len(topicos), 2):
                    txt = (topicos[j] + topicos[j+1]).strip()
                    if materia_atual not in materias_detectadas: materias_detectadas[materia_atual] = []
                    materias_detectadas[materia_atual].append(txt)
            else:
                if len(item) > 10:
                    if materia_atual not in materias_detectadas: materias_detectadas[materia_atual] = []
                    materias_detectadas[materia_atual].append(item)
    return {k: v for k, v in materias_detectadas.items() if len(v) > 0}

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
                    st.session_state.missao_ativa = nome; st.rerun()

    with tabs[1]:
        st.subheader("🤖 Novo Concurso via IA")
        c1, c2 = st.columns(2)
        n_n, n_c = c1.text_input("Concurso"), c2.text_input("Cargo")
        pdf = st.file_uploader("Edital PDF", type="pdf")
        if st.button("🚀 ANALISAR") and pdf and n_n:
            with st.spinner("Processando..."):
                doc = fitz.open(stream=pdf.read(), filetype="pdf")
                st.session_state.temp_ia = fatiar_edital_blindado("\n".join([p.get_text() for p in doc]))
                st.session_state.temp_n, st.session_state.temp_c = n_n, n_c
                doc.close()
        if "temp_ia" in st.session_state:
            for m, t in st.session_state.temp_ia.items():
                with st.expander(f"📚 {m}"):
                    st.write("\n".join([f"- {i}" for i in t]))
                    if st.button(f"Salvar {m}", key=f"ia_{m}"):
                        supabase.table("editais_materias").insert({"concurso": st.session_state.temp_n, "cargo": st.session_state.temp_c, "materia": m, "topicos": t}).execute()
                        st.toast(f"{m} salva!")
            if st.button("✅ FINALIZAR"): del st.session_state.temp_ia; st.rerun()

else:
    missao = st.session_state.missao_ativa
    df = get_stats(missao)
    dados = get_editais().get(missao, {})
    
    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], 
                           default_index=2, styles={"nav-link-selected": {"background-color": "#DC2626"}})

    if menu == "Dashboard":
        st.subheader("📊 Performance")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            hrs = (df['tempo'].sum() / 60) if 'tempo' in df.columns else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", int(tot)); c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%"); c3.metric("Tempo", f"{int(hrs)}h")
            df_g = df.copy(); df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            st.plotly_chart(px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626'], height=350), use_container_width=True)

    elif menu == "Revisões":
        st.subheader("🔄 Radar D1 - D30")
        df_p = calcular_pendencias(df)
        if df_p.empty: st.success("✅ Tudo revisado!")
        else:
            cols = st.columns(4); fases = [("24h", "🔥 D1"), ("07d", "📅 D7"), ("15d", "🧠 D15"), ("30d", "💎 D30")]
            for i, (fid, flabel) in enumerate(fases):
                with cols[i]:
                    st.markdown(f"#### {flabel}")
                    itens = df_p[df_p['Fase'] == fid]
                    for _, row in itens.iterrows():
                        st.markdown(f'<div class="rev-card {row["CSS"]}"><div class="card-subject">{row["Mat"]}</div><div class="card-topic">{row["Ass"]}</div><div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-top:5px;"><span>📅 {row["Data"]}</span><span class="score-badge">{row["Taxa"]:.0f}%</span></div></div>', unsafe_allow_html=True)
                        if st.button("Ok", key=f"f_{row['id']}_{fid}"):
                            supabase.table("registros_estudos").update({f"rev_{fid}": True}).eq("id", row['id']).execute(); st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Registrar Questões")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1]); mat = c1.selectbox("Matéria", mats); ass = c1.selectbox("Assunto", dados['materias'].get(mat, ["Geral"])); dt = c2.date_input("Data")
                st.divider(); ac = st.number_input("Acertos", 0); tot = st.number_input("Total", 1)
                t1, t2 = st.columns(2); h_val = t1.selectbox("Horas", range(13)); m_val = t2.selectbox("Minutos", range(60))
                if st.button("💾 SALVAR REGISTRO", type="primary"):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "tempo": (h_val*60+m_val), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute(); st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Add"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos", "\n".join(t), key=f"t_{m}", height=150)
                if st.button("Salvar", key=f"s_{m}"):
                    novos = [l.strip() for l in tx.split('\n') if l.strip()]
                    supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Vazio.")
        else:
            ed = st.data_editor(df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total']], hide_index=True)
            if st.button("💾 ATUALIZAR"):
                for _, r in ed.iterrows():
                    tx = (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "taxa": tx}).eq("id", r['id']).execute()
                st.rerun()
