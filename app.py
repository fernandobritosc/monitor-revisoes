import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL DE ALTA PERFORMANCE (CSS) ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Configuração Global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0A0A0B;
        color: #E2E8F0;
    }
    
    .block-container { padding-top: 1.5rem !important; }
    header { visibility: hidden; }

    /* Cards de Revisão Estilo Dashboard */
    .rev-card {
        background: #17171B;
        border: 1px solid #2D2D35;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        transition: transform 0.2s ease;
    }
    .rev-card:hover { border-color: #4A4A55; transform: translateY(-2px); }
    
    /* Indicadores de Performance */
    .perf-bad { border-left: 5px solid #EF4444; }   /* Ruim < 60% */
    .perf-med { border-left: 5px solid #F59E0B; }   /* Médio 60-80% */
    .perf-good { border-left: 5px solid #10B981; }  /* Bom > 80% */
    
    .card-subject { font-weight: 800; font-size: 0.9rem; color: #FFF; margin-bottom: 3px; }
    .card-topic { font-size: 0.8rem; color: #94A3B8; margin-bottom: 8px; line-height: 1.2; }
    .card-footer { display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748B; }
    .score-tag { font-weight: 700; color: #FFF; background: #2D2D35; padding: 2px 6px; border-radius: 4px; }

    /* Botões */
    .stButton button {
        background: #1E1E24;
        border: 1px solid #3F3F46;
        border-radius: 8px;
        font-weight: 600;
        transition: 0.3s;
        width: 100%;
    }
    .stButton button:hover {
        background: #DC2626;
        border-color: #DC2626;
        color: white;
    }

    /* Ajuste de Inputs para não ficarem gigantes */
    .stSelectbox, .stNumberInput, .stDateInput { margin-bottom: -10px; }

</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. LOGICA DE DADOS ---
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
    
    colunas_rev = ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']
    for c in colunas_rev:
        if c not in df.columns: df[c] = False

    for _, row in df.iterrows():
        delta = (hoje - row['dt_temp']).days
        taxa = row.get('taxa', 0)
        
        # Cor por performance
        css = "perf-bad" if taxa < 60 else "perf-med" if taxa < 80 else "perf-good"
        
        base = {"id": row['id'], "Mat": row['materia'], "Ass": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Taxa": taxa, "CSS": css}
        
        # Filtro Cronograma D1, D7, D15, D30
        if delta >= 1 and not row['rev_24h']: pendencias.append({**base, "Fase": "24h", "Label": "🔥 D1"})
        if delta >= 7 and not row['rev_07d']: pendencias.append({**base, "Fase": "07d", "Label": "📅 D7"})
        if delta >= 15 and not row['rev_15d']: pendencias.append({**base, "Fase": "15d", "Label": "🧠 D15"})
        if delta >= 30 and not row['rev_30d']: pendencias.append({**base, "Fase": "30d", "Label": "💎 D30"})
            
    return pd.DataFrame(pendencias)

# --- 4. INTERFACE ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

# TELA 1: COMANDO CENTRAL
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    editais = get_editais()
    c_m, c_n = st.columns([2, 1])
    
    with c_m:
        st.subheader("Missões Ativas")
        for nome, dados in editais.items():
            with st.container(border=True):
                ca, cb = st.columns([4, 1])
                ca.markdown(f"**{nome}** | {dados['cargo']}")
                if cb.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()
    with c_n:
        with st.container(border=True):
            st.subheader("Nova Missão")
            with st.form("new_mission"):
                n = st.text_input("Nome (Sigla)")
                c = st.text_input("Cargo")
                d = st.date_input("Data da Prova")
                if st.form_submit_button("CRIAR"):
                    supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral"}).execute()
                    st.rerun()

# TELA 2: MODO OPERACIONAL
else:
    missao = st.session_state.missao_ativa
    df = get_stats(missao)
    dados = get_editais().get(missao, {})
    
    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR AO COMANDO"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=1,
                           styles={"nav-link-selected": {"background-color": "#DC2626"}})

    # --- DASHBOARD ---
    if menu == "Dashboard":
        st.subheader("📊 Painel de Performance")
        if df.empty: st.info("Sem dados.")
        else:
            tot = df['total'].sum()
            ac = df['acertos'].sum()
            hrs = (df['tempo'].sum() / 60) if 'tempo' in df.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", int(tot))
            c2.metric("Precisão", f"{(ac/tot*100):.1f}%")
            c3.metric("Horas Líquidas", f"{int(hrs)}h")
            
            st.divider()
            df_g = df.copy()
            df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            fig = px.area(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#2D2D35', '#DC2626'])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig, use_container_width=True)

    # --- REVISÕES (GRID KANBAN) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisão (D1 - D30)")
        df_p = calcular_pendencias(df)
        
        if df_p.empty:
            st.success("✅ Nenhuma revisão pendente para hoje!")
        else:
            fases = [("24h", "🔥 D1"), ("07d", "📅 D7"), ("15d", "🧠 D15"), ("30d", "💎 D30")]
            cols = st.columns(4)
            for i, (fid, flabel) in enumerate(fases):
                with cols[i]:
                    st.markdown(f"### {flabel}")
                    itens = df_p[df_p['Fase'] == fid]
                    if itens.empty: st.caption("Vazio")
                    else:
                        for _, row in itens.iterrows():
                            st.markdown(f"""
                            <div class="rev-card {row['CSS']}">
                                <div class="card-subject">{row['Mat']}</div>
                                <div class="card-topic">{row['Ass']}</div>
                                <div class="card-footer">
                                    <span>📅 {row['Data']}</span>
                                    <span class="score-tag">{row['Taxa']:.0f}%</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("Concluir", key=f"f_{row['id']}_{fid}"):
                                supabase.table("registros_estudos").update({f"rev_{fid}": True}).eq("id", row['id']).execute()
                                st.rerun()

    # --- REGISTRAR (LAYOUT ORGANIZADO) ---
    elif menu == "Registrar":
        st.subheader("📝 Registrar Sessão de Estudo")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Configure as matérias primeiro.")
        else:
            with st.container(border=True):
                # Linha 1: Matéria e Data
                r1c1, r1c2 = st.columns([2, 1])
                mat = r1c1.selectbox("Matéria", mats)
                assunto = r1c1.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
                dt = r1c2.date_input("Data do Estudo")
                
                st.write("") # Espaçador
                
                # Linha 2: Performance e Tempo
                r2c1, r2c2, r2c3 = st.columns([1, 1, 1])
                ac = r2c1.number_input("Acertos", 0)
                tot = r2c2.number_input("Total", 1)
                
                r2c3.write("**Tempo Líquido**")
                tc1, tc2 = r2c3.columns(2)
                h_val = tc1.selectbox("Hs", range(13), label_visibility="collapsed")
                m_val = tc2.selectbox("Min", range(60), label_visibility="collapsed")
                
                st.divider()
                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    try:
                        supabase.table("registros_estudos").insert({
                            "concurso": missao, "materia": mat, "assunto": assunto,
                            "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot,
                            "taxa": (ac/tot*100), "tempo": h_val*60+m_val,
                            "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }).execute()
                        st.toast("Sucesso! Registro salvo."); time.sleep(0.5); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

    # --- CONFIGURAR ---
    elif menu == "Configurar":
        st.subheader("⚙️ Gestão de Matérias")
        with st.container(border=True):
            nm = st.text_input("Nome da Matéria")
            if st.button("ADICIONAR MATÉRIA"):
                supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": []}).execute()
                st.rerun()
        st.divider()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tx = st.text_area("Tópicos (separe por ;)", "; ".join(t), key=f"t_{m}")
                cs, cd = st.columns([4, 1])
                if cs.button("Salvar", key=f"s_{m}"):
                    l = [x.strip() for x in tx.split(";") if x.strip()]
                    supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()
                if cd.button("🗑️", key=f"d_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()

    # --- HISTÓRICO ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico de Lançamentos")
        if df.empty: st.info("Vazio.")
        else:
            # Editor de Dados
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total']
            edited = st.data_editor(df[cols_show], hide_index=True, use_container_width=True, key="h_editor")
            
            if st.button("💾 SALVAR ALTERAÇÕES"):
                for _, r in edited.iterrows():
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], 
                        "taxa": (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    }).eq("id", r['id']).execute()
                st.rerun()
            
            st.divider()
            # Zona de Exclusão por Dropdown (Mais limpo)
            st.subheader("🗑️ Zona de Perigo")
            del_options = {f"{r['data_estudo']} | {r['materia']} ({r['id']})": r['id'] for _, r in df.iterrows()}
            alvo = st.selectbox("Escolha um registro para apagar:", ["Selecione..."] + list(del_options.keys()))
            if alvo != "Selecione..." and st.button("EXCLUIR PERMANENTEMENTE", type="primary"):
                supabase.table("registros_estudos").delete().eq("id", del_options[alvo]).execute()
                st.rerun()
