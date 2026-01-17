import streamlit as st
import pandas as pd
import datetime
import time
import os
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# Importação do Docling com tratamento de erro
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    DOCLING_READY = True
except ImportError:
    DOCLING_READY = False

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="COMMANDER ELITE", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0A0A0B; color: #E2E8F0; }
    header { visibility: hidden; }
    .block-container { padding-top: 1rem !important; }
    .rev-card {
        background: #17171B; border: 1px solid #2D2D35; border-radius: 8px;
        padding: 12px; margin-bottom: 10px; border-left: 4px solid #333;
    }
    .perf-bad { border-left-color: #EF4444; }
    .perf-med { border-left-color: #F59E0B; }
    .perf-good { border-left-color: #10B981; }
    .score-badge { background: #2D2D35; color: #FFF; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
    .stButton button { background: #1E1E24; border: 1px solid #3F3F46; border-radius: 6px; font-weight: 600; width: 100%; }
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
                editais[c] = {"cargo": row.get('cargo') or "Geral", "data_iso": row.get('data_prova'), "materias": {}}
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
        
        # Lógica de Camada Única (A mais urgente aparece primeiro)
        if delta >= 30 and not row['rev_30d']: pendencias.append({**base, "Fase": "30d", "Label": "💎 D30"})
        elif delta >= 15 and not row['rev_15d']: pendencias.append({**base, "Fase": "15d", "Label": "🧠 D15"})
        elif delta >= 7 and not row['rev_07d']: pendencias.append({**base, "Fase": "07d", "Label": "📅 D7"})
        elif delta >= 1 and not row['rev_24h']: pendencias.append({**base, "Fase": "24h", "Label": "🔥 D1"})
    return pd.DataFrame(pendencias)

# --- 4. FLUXO PRINCIPAL ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    editais = get_editais()
    for nome, dados in editais.items():
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"### {nome}\n*{dados['cargo']}*")
            if c2.button("ACESSAR", key=f"ac_{nome}"):
                st.session_state.missao_ativa = nome
                st.rerun()
else:
    missao = st.session_state.missao_ativa
    df = get_stats(missao)
    dados = get_editais().get(missao, {})
    
    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "IA: Novo Edital", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "robot", "gear", "list-task"], 
                           default_index=1, styles={"nav-link-selected": {"background-color": "#DC2626"}})

    if menu == "Dashboard":
        st.subheader("📊 Performance Geral")
        if df.empty: st.info("Sem dados.")
        else:
            tot, ac = df['total'].sum(), df['acertos'].sum()
            mins = df['tempo'].sum() if 'tempo' in df.columns else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", int(tot)); c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%"); c3.metric("Tempo", f"{int(mins//60)}h")
            st.divider()
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
                    itens = df_p[df_p['Fase'] == fid] if not df_p.empty else []
                    for _, row in itens.iterrows():
                        st.markdown(f'<div class="rev-card {row["CSS"]}"><div style="font-weight:800;font-size:0.85rem;color:#FFF;">{row["Mat"]}</div><div style="font-size:0.75rem;color:#94A3B8;">{row["Ass"]}</div><div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-top:5px;"><span>📅 {row["Data"]}</span><span class="score-badge">{row["Taxa"]:.0f}%</span></div></div>', unsafe_allow_html=True)
                        if st.button("Ok", key=f"f_{row['id']}_{fid}"):
                            supabase.table("registros_estudos").update({f"rev_{fid}": True}).eq("id", row['id']).execute(); st.rerun()

    elif menu == "Registrar":
        st.subheader("📝 Registrar Questões")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1]); mat = c1.selectbox("Matéria", mats); assunto = c1.selectbox("Assunto", dados['materias'].get(mat, ["Geral"])); dt = c2.date_input("Data")
                st.divider(); p1, p2 = st.columns(2); ac = p1.number_input("Acertos", 0); tot = p2.number_input("Total", 1)
                t1, t2 = st.columns(2); h_val = t1.selectbox("Horas", range(13)); m_val = t2.selectbox("Minutos", range(60))
                if st.button("💾 REGISTRAR BATALHA", type="primary"):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": assunto, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "tempo": h_val*60+m_val, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute(); st.toast("Salvo!"); time.sleep(0.5); st.rerun()

elif menu == "IA: Novo Edital":
        st.subheader("🤖 IA: Importador de Edital")
        if not DOCLING_READY:
            st.error("Erro: Bibliotecas Docling não encontradas no requirements.txt")
        else:
            st.info("Suba o PDF do edital para extrair o conteúdo programático automaticamente.")
            with st.container(border=True):
                nome_concurso = st.text_input("Nome do Concurso", placeholder="Ex: PCGO")
                pdf_file = st.file_uploader("Escolha o Edital (PDF)", type="pdf")
                
                if st.button("🚀 INICIAR EXTRAÇÃO INTELIGENTE") and pdf_file and nome_concurso:
                    with st.spinner("🤖 Analisando PDF..."):
                        try:
                            temp_path = os.path.join(os.getcwd(), "temp_edital.pdf")
                            with open(temp_path, "wb") as f:
                                f.write(pdf_file.getbuffer())
                            
                            # --- CONFIGURAÇÃO CORRIGIDA PARA VERSÕES NOVAS ---
                            from docling.datamodel.pipeline_options import PdfPipelineOptions
                            from docling.datamodel.base_models import InputFormat
                            
                            pipeline_opts = PdfPipelineOptions()
                            pipeline_opts.do_ocr = False # Mantemos False para evitar o PermissionError
                            pipeline_opts.do_table_structure = True
                            
                            # A mudança está aqui: usamos format_options
                            converter = DocumentConverter(
                                allowed_formats=[InputFormat.PDF],
                                format_options={
                                    InputFormat.PDF: pipeline_opts
                                }
                            )
                            
                            result = converter.convert(temp_path)
                            texto_md = result.document.export_to_markdown()
                            
                            st.success("Leitura concluída!")
                            st.text_area("Conteúdo Extraído:", value=texto_md, height=400)
                            
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception as e:
                            st.error(f"Erro técnico: {e}")

    elif menu == "Configurar":
        st.subheader("⚙️ Edital")
        nm = st.text_input("Nova Matéria")
        if st.button("Add"): supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute(); st.rerun()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos (;)", "; ".join(t), key=f"t_{m}")
                cs, cd = st.columns([4, 1])
                if cs.button("Salvar", key=f"s_{m}"):
                    supabase.table("editais_materias").update({"topicos": [x.strip() for x in tx.split(";") if x.strip()]}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                if cd.button("🗑️", key=f"d_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Vazio.")
        else:
            edited = st.data_editor(df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total']], hide_index=True, use_container_width=True)
            if st.button("💾 SALVAR ALTERAÇÕES"):
                for _, r in edited.iterrows():
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "taxa": (r['acertos']/r['total']*100) if r['total'] > 0 else 0}).eq("id", r['id']).execute()
                st.rerun()
            st.divider()
            alvo = st.selectbox("Apagar:", ["Selecione..."] + [f"{r['data_estudo']} | {r['materia']} ({r['id']})" for _, r in df.iterrows()])
            if alvo != "Selecione..." and st.button("🗑️ EXCLUIR"):
                rid = alvo.split('(')[-1].strip(')')
                supabase.table("registros_estudos").delete().eq("id", rid).execute(); st.rerun()
