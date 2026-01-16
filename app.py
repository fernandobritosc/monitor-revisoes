import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL ELITE (CSS) ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* RESET GERAL */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0E0E0E;
    }
    
    /* REMOVER ESPAÇOS EM BRANCO DESNECESSÁRIOS */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    header {visibility: hidden;}
    
    /* BOTÕES CUSTOMIZADOS */
    .stButton button {
        background-color: #262626;
        color: #E5E5E5;
        border: 1px solid #404040;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #DC2626; /* Vermelho Sangue */
        border-color: #DC2626;
        color: white;
        transform: translateY(-1px);
    }
    
    /* CARDS DE MÉTRICAS (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #1A1A1A;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem; color: #888; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: #FFF; }
    
    /* INPUTS MAIS COMPACTOS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stDateInput input {
        background-color: #171717 !important;
        border: 1px solid #333 !important;
        color: #EEE !important;
        border-radius: 6px !important;
        font-size: 0.9rem;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    /* --- CARDS DO RADAR DE REVISÃO --- */
    .rev-card-container {
        background-color: #171717;
        border: 1px solid #2A2A2A;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        transition: transform 0.2s;
        position: relative;
        overflow: hidden;
    }
    .rev-card-container:hover {
        border-color: #444;
        transform: translateY(-2px);
    }
    
    /* Faixa colorida lateral indicando urgência */
    .border-24h { border-left: 4px solid #EF4444; }
    .border-07d { border-left: 4px solid #F59E0B; }
    .border-15d { border-left: 4px solid #3B82F6; }
    .border-30d { border-left: 4px solid #10B981; }
    
    .rev-header { font-size: 0.95rem; font-weight: 700; color: #FFF; margin-bottom: 4px; }
    .rev-body { font-size: 0.85rem; color: #A3A3A3; margin-bottom: 8px; line-height: 1.3; }
    .rev-meta { font-size: 0.75rem; color: #555; display: flex; justify-content: space-between; align-items: center; }
    .rev-tag { background: #222; padding: 2px 6px; border-radius: 4px; border: 1px solid #333; }

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
        if dias <= 30: return data_fmt, f"🔥 {dias} dias"
        return data_fmt, f"⏳ {dias} dias"
    except: return data_iso, None

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

def calcular_revisoes_pendentes(df):
    if df.empty: return []
    hoje = datetime.date.today()
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    pendencias = []
    
    # Garante colunas
    for col in ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']:
        if col not in df.columns: df[col] = False

    for _, row in df.iterrows():
        dias = (hoje - row['dt_temp']).days
        # Lógica cumulativa: Se deve e não fez, aparece.
        if dias >= 1 and not row['rev_24h']:
            pendencias.append({"id": row['id'], "Fase": "24h", "Matéria": row['materia'], "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Dias": dias})
        if dias >= 7 and not row['rev_07d']:
            pendencias.append({"id": row['id'], "Fase": "07d", "Matéria": row['materia'], "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Dias": dias})
        if dias >= 15 and not row['rev_15d']:
            pendencias.append({"id": row['id'], "Fase": "15d", "Matéria": row['materia'], "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Dias": dias})
        if dias >= 30 and not row['rev_30d']:
            pendencias.append({"id": row['id'], "Fase": "30d", "Matéria": row['materia'], "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Dias": dias})
            
    return pd.DataFrame(pendencias)

# --- 4. FLUXO PRINCIPAL ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

# --- TELA 1: CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.markdown("## 💀 CENTRAL DE COMANDO")
    st.markdown("---")
    editais = get_editais()
    c_main, c_side = st.columns([3, 1], gap="large")
    
    with c_main:
        if not editais: st.info("Sem missões ativas.")
        else:
            for nome, dados in editais.items():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1.5, 1])
                    dt_str, status = get_data_countdown(dados['data_iso'])
                    with c1:
                        st.markdown(f"**{nome}**")
                        st.caption(f"{dados['cargo']}")
                    with c2:
                        st.markdown(f"📅 {dt_str}")
                        if status: 
                            cor = "#EF4444" if "Reta" in status or "HOJE" in status else "#A3A3A3"
                            st.markdown(f"<span style='color:{cor}; font-weight:600; font-size:0.85em'>{status}</span>", unsafe_allow_html=True)
                    with c3:
                        if st.button("ACESSAR", key=f"btn_{nome}"):
                            st.session_state.missao_ativa = nome
                            st.rerun()

    with c_side:
        with st.container(border=True):
            st.markdown("**➕ Nova Missão**")
            with st.form("quick_create"):
                nm = st.text_input("Nome", placeholder="Sigla (Ex: PF)")
                cg = st.text_input("Cargo", placeholder="Agente")
                dt = st.date_input("Data Prova")
                if st.form_submit_button("CRIAR"):
                    if nm:
                        try: supabase.table("editais_materias").insert({"concurso": nm, "cargo": cg, "data_prova": dt.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": [], "usuario": "Commander"}).execute()
                        except: supabase.table("editais_materias").insert({"concurso": nm, "cargo": cg, "data_prova": dt.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": []}).execute()
                        st.rerun()

        st.write("")
        with st.container(border=True):
            st.markdown("**🗑️ Exclusão**")
            lista = ["..."] + list(editais.keys())
            alvo = st.selectbox("Apagar:", lista, label_visibility="collapsed")
            if alvo != "..." and st.button("CONFIRMAR APAGAR"):
                supabase.table("registros_estudos").delete().eq("concurso", alvo).execute()
                supabase.table("editais_materias").delete().eq("concurso", alvo).execute()
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
        st.write("")
        if st.button("🔙 VOLTAR"):
            st.session_state.missao_ativa = None
            st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["bar-chart-fill", "check-circle", "pencil-square", "gear-fill", "table"], default_index=0,
                           styles={"nav-link-selected": {"background-color": "#DC2626"}})

    # --- DASHBOARD ---
    if menu == "Dashboard":
        st.subheader("📊 Painel Tático")
        if df.empty: st.info("Sem dados.")
        else:
            tot = int(df['total'].sum())
            ac = int(df['acertos'].sum())
            prec = (ac/tot*100) if tot > 0 else 0
            mins = df['tempo'].fillna(0).sum() if 'tempo' in df.columns else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões", tot)
            c2.metric("Acertos", ac)
            c3.metric("Precisão", f"{prec:.1f}%")
            c4.metric("Horas", f"{int(mins//60)}h {int(mins%60)}m")
            
            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            df['Data'] = pd.to_datetime(df['data_estudo']).dt.strftime('%d/%m')
            fig = px.area(df.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#333', '#DC2626'])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=10,r=10,t=10,b=10), legend=dict(orientation="h", y=1.1))
            g1.plotly_chart(fig, use_container_width=True)
            
            fig2 = go.Figure(data=[go.Pie(labels=['Acertos', 'Erros'], values=[ac, tot-ac], hole=.6, marker=dict(colors=['#DC2626', '#333']), textinfo='percent')])
            fig2.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
            g2.plotly_chart(fig2, use_container_width=True)

    # --- RADAR DE REVISÃO (NOVO VISUAL) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisão")
        df_rev = calcular_revisoes_pendentes(df)
        
        if len(df_rev) == 0:
            st.success("✅ Tudo limpo! Nenhuma revisão pendente.")
        else:
            cols = st.columns(4)
            fases = ["24h", "07d", "15d", "30d"]
            labels = ["🔥 24h", "📅 7d", "🧠 15d", "💎 30d"]
            
            for i, fase in enumerate(fases):
                with cols[i]:
                    st.markdown(f"**{labels[i]}**")
                    tasks = df_rev[df_rev['Fase'] == fase]
                    if tasks.empty: st.caption("-")
                    else:
                        for _, row in tasks.iterrows():
                            # Renderiza Visual do Card
                            border_class = f"border-{fase}"
                            st.markdown(f"""
                            <div class="rev-card-container {border_class}">
                                <div class="rev-header">{row['Matéria']}</div>
                                <div class="rev-body">{row['Assunto']}</div>
                                <div class="rev-meta">
                                    <span class="rev-tag">{row['Data']}</span>
                                    <span style="color: #EF4444;">+{row['Dias']}d</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Botão Lógico
                            col_db = f"rev_{fase}"
                            if st.button("Concluir", key=f"done_{row['id']}_{fase}"):
                                try:
                                    supabase.table("registros_estudos").update({col_db: True}).eq("id", row['id']).execute()
                                    st.toast("Feito!"); time.sleep(0.5); st.rerun()
                                except: st.error("Erro: Crie as colunas rev_24h, etc no banco.")

    # --- REGISTRO (COMPACTO) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias em 'Configurar'.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                mat = c1.selectbox("Matéria", mats)
                tops = dados['materias'].get(mat, []) or ["Geral"]
                assunto = c1.selectbox("Assunto", tops)
                dt = c2.date_input("Data")
                
                st.markdown("---")
                c3, c4, c5 = st.columns([1, 1, 1])
                ac = c3.number_input("Acertos", 0, step=1)
                tot = c4.number_input("Total", 1, step=1)
                
                c5.write("**Tempo**")
                cc1, cc2 = c5.columns(2)
                h = cc1.selectbox("H", range(13), label_visibility="collapsed")
                m = cc2.selectbox("M", range(60), label_visibility="collapsed")
                
                st.write("")
                if st.button("💾 REGISTRAR BATALHA", type="primary"):
                    try:
                        supabase.table("registros_estudos").insert({
                            "concurso": missao, "materia": mat, "assunto": assunto,
                            "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot,
                            "taxa": (ac/tot)*100, "tempo": h*60+m,
                            "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }).execute()
                        st.toast("Salvo!"); time.sleep(0.5)
                    except Exception as e: st.error(f"Erro: {e}")

    # --- CONFIGURAR ---
    elif menu == "Configurar":
        st.subheader("⚙️ Configuração")
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.container(border=True):
                st.markdown("**Adicionar Matéria**")
                nm = st.text_input("Nome", label_visibility="collapsed")
                if st.button("➕ Adicionar"):
                    try: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso'), "usuario": "Commander"}).execute()
                    except: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso')}).execute()
                    st.rerun()
        with c2:
            for m, t in dados.get('materias', {}).items():
                with st.expander(f"{m}"):
                    val = st.text_area("Tópicos (;)", "; ".join(t), height=100, key=f"t_{m}")
                    c_s, c_d = st.columns([4, 1])
                    if c_s.button("Salvar", key=f"s_{m}"):
                        l = [x.strip() for x in val.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()
                    if c_d.button("🗑️", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()

    # --- HISTÓRICO ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if not df.empty:
            df['data_estudo'] = pd.to_datetime(df['data_estudo']).dt.date
            if 'tempo' not in df.columns: df['tempo'] = 0
            
            # Tabela Editável
            edited = st.data_editor(df[['id','data_estudo','materia','assunto','acertos','total','tempo']], 
                           column_config={"id":None, "data_estudo": st.column_config.DateColumn("Data"), "tempo": st.column_config.NumberColumn("Min")},
                           use_container_width=True, hide_index=True, key="h_edit")
            
            c_save, c_del = st.columns([3, 1])
            if c_save.button("💾 SALVAR EDIÇÕES"):
                for _, r in edited.iterrows():
                    try: supabase.table("registros_estudos").update({"data_estudo": r['data_estudo'].strftime('%Y-%m-%d'), "acertos": r['acertos'], "total": r['total'], "tempo": r['tempo'], "taxa": (r['acertos']/r['total']*100) if r['total']>0 else 0}).eq("id", r['id']).execute()
                    except: pass
                st.toast("Atualizado!"); time.sleep(0.5); st.rerun()
            
            # Exclusão
            opts = {f"{r['data_estudo'].strftime('%d/%m')} - {r['materia']}": r['id'] for _, r in df.iterrows()}
            sel = c_del.selectbox("Apagar", ["..."]+list(opts.keys()), label_visibility="collapsed")
            if sel != "..." and c_del.button("🗑️ APAGAR"):
                supabase.table("registros_estudos").delete().eq("id", opts[sel]).execute()
                st.rerun()
        else: st.info("Vazio.")
