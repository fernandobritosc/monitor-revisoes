import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO BASE ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

# CSS Minimalista e Funcional
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0E0E0E; color: #EEE; }
    header {visibility: hidden;}
    .block-container { padding-top: 2rem !important; }
    
    /* Estilo dos Cards de Revisão */
    .rev-card {
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #333;
        background-color: #171717;
    }
    .border-red { border-left: 5px solid #EF4444; }    /* Ruim < 60% */
    .border-orange { border-left: 5px solid #F59E0B; } /* Médio 60-80% */
    .border-green { border-left: 5px solid #10B981; }  /* Bom > 80% */
    
    .card-title { font-weight: 700; font-size: 1rem; color: #FFF; margin-bottom: 4px; }
    .card-sub { font-size: 0.85rem; color: #A3A3A3; }
    .card-footer { font-size: 0.75rem; color: #555; margin-top: 8px; display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. FUNÇÕES DE SUPORTE ---
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

def processar_revisoes(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    df['dt_estudo_obj'] = pd.to_datetime(df['data_estudo']).dt.date
    
    pendencias = []
    colunas_rev = ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']
    for c in colunas_rev:
        if c not in df.columns: df[c] = False

    for _, row in df.iterrows():
        delta = (hoje - row['dt_estudo_obj']).days
        taxa = row.get('taxa', 0)
        
        # Define a cor do card pela performance
        cor = "border-red" if taxa < 60 else "border-orange" if taxa < 80 else "border-green"
        
        base = {
            "id": row['id'], "Materia": row['materia'], "Assunto": row['assunto'],
            "Data": row['dt_estudo_obj'].strftime('%d/%m'), "Taxa": taxa, "Cor": cor
        }
        
        # Critérios D1, D7, D15, D30
        if delta >= 1 and not row['rev_24h']: 
            d = base.copy(); d.update({"Fase": "24h", "Label": "🔥 D1"}); pendencias.append(d)
        if delta >= 7 and not row['rev_07d']: 
            d = base.copy(); d.update({"Fase": "07d", "Label": "📅 D7"}); pendencias.append(d)
        if delta >= 15 and not row['rev_15d']: 
            d = base.copy(); d.update({"Fase": "15d", "Label": "🧠 D15"}); pendencias.append(d)
        if delta >= 30 and not row['rev_30d']: 
            d = base.copy(); d.update({"Fase": "30d", "Label": "💎 D30"}); pendencias.append(d)
            
    return pd.DataFrame(pendencias)

# --- 4. NAVEGAÇÃO ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

# CENTRAL DE COMANDO
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    editais = get_editais()
    
    c1, c2 = st.columns([2, 1])
    with c1:
        for nome, dados in editais.items():
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                col_a.subheader(nome)
                col_a.caption(f"Cargo: {dados['cargo']}")
                if col_b.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("### ➕ Nova Missão")
            with st.form("new_m"):
                n = st.text_input("Nome")
                c = st.text_input("Cargo")
                d = st.date_input("Data Prova")
                if st.form_submit_button("CRIAR"):
                    supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral"}).execute()
                    st.rerun()

# MODO OPERACIONAL
else:
    missao = st.session_state.missao_ativa
    df = get_stats(missao)
    dados = get_editais().get(missao, {})
    
    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR AO COMANDO"):
            st.session_state.missao_ativa = None
            st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-check"], default_index=1)

    # --- DASHBOARD ---
    if menu == "Dashboard":
        st.subheader("📊 Performance Geral")
        if df.empty: st.info("Sem dados.")
        else:
            c1, c2, c3 = st.columns(3)
            tot = df['total'].sum()
            ac = df['acertos'].sum()
            c1.metric("Questões", int(tot))
            c2.metric("Precisão", f"{(ac/tot*100 if tot > 0 else 0):.1f}%")
            if 'tempo' in df.columns:
                h = df['tempo'].sum() // 60
                c3.metric("Horas Líquidas", f"{int(h)}h")
            
            st.markdown("---")
            df_g = df.copy()
            df_g['Data'] = pd.to_datetime(df_g['data_estudo']).dt.strftime('%d/%m')
            fig = px.line(df_g.groupby('Data')[['total', 'acertos']].sum().reset_index(), x='Data', y=['total', 'acertos'], color_discrete_sequence=['#444', '#DC2626'])
            st.plotly_chart(fig, use_container_width=True)

    # --- REVISÕES (LÓGICA STICKY) ---
    elif menu == "Revisões":
        st.subheader("🔄 Cronograma de Revisão (Dívida Ativa)")
        df_p = processar_revisoes(df)
        
        if df_p.empty:
            st.success("✅ Nenhuma revisão pendente!")
        else:
            fases = [("24h", "🔥 D1"), ("07d", "📅 D7"), ("15d", "🧠 D15"), ("30d", "💎 D30")]
            cols = st.columns(4)
            
            for i, (f_id, f_label) in enumerate(fases):
                with cols[i]:
                    st.markdown(f"#### {f_label}")
                    itens = df_p[df_p['Fase'] == f_id]
                    if itens.empty: st.caption("Vazio")
                    else:
                        for _, row in itens.iterrows():
                            # Card Visual
                            st.markdown(f"""
                            <div class="rev-card {row['Cor']}">
                                <div class="card-title">{row['Materia']}</div>
                                <div class="card-sub">{row['Assunto']}</div>
                                <div class="card-footer">
                                    <span>📅 {row['Data']}</span>
                                    <span>🎯 <b>{row['Taxa']:.0f}%</b></span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("Concluir", key=f"btn_{row['id']}_{f_id}"):
                                supabase.table("registros_estudos").update({f"rev_{f_id}": True}).eq("id", row['id']).execute()
                                st.toast("Revisão registrada!")
                                time.sleep(0.5); st.rerun()

    # --- REGISTRAR ---
    elif menu == "Registrar":
        st.subheader("📝 Registrar Questões")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro!")
        else:
            with st.form("reg_q"):
                c1, c2 = st.columns(2)
                mat = c1.selectbox("Matéria", mats)
                assunto = c1.selectbox("Assunto", dados['materias'].get(mat, ["Geral"]))
                dt = c2.date_input("Data")
                ac = c2.number_input("Acertos", 0)
                tot = c2.number_input("Total", 1)
                h, m = st.columns(2)
                hs = h.selectbox("Horas", range(13))
                mi = m.selectbox("Minutos", range(60))
                if st.form_submit_button("SALVAR REGISTRO"):
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": assunto,
                        "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot,
                        "taxa": (ac/tot*100), "tempo": hs*60+mi,
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("Registrado!"); time.sleep(0.5); st.rerun()

    # --- CONFIGURAR ---
    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        with st.container(border=True):
            nova_m = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({"concurso": missao, "materia": nova_m, "topicos": []}).execute()
                st.rerun()
        st.divider()
        for m, t in dados.get('materias', {}).items():
            with st.expander(f"📚 {m}"):
                tops = st.text_area("Tópicos (separar por ;)", "; ".join(t), key=f"tx_{m}")
                c_s, c_d = st.columns([4, 1])
                if c_s.button("Salvar", key=f"sv_{m}"):
                    l = [x.strip() for x in tops.split(";") if x.strip()]
                    supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()
                if c_d.button("🗑️", key=f"del_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()

    # --- HISTÓRICO ---
    elif menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty: st.info("Vazio.")
        else:
            # Editor de tabela
            df_e = df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total']]
            edited = st.data_editor(df_e, hide_index=True, use_container_width=True)
            if st.button("Salvar Alterações"):
                for _, r in edited.iterrows():
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "taxa": (r['acertos']/r['total']*100)}).eq("id", r['id']).execute()
                st.rerun()
            
            st.divider()
            st.markdown("### 🗑️ Excluir Registro")
            opcoes = {f"{r['data_estudo']} - {r['materia']} ({r['id']})": r['id'] for _, r in df.iterrows()}
            alvo_del = st.selectbox("Escolha um registro", list(opcoes.keys()), index=None)
            if alvo_del and st.button("EXCLUIR REGISTRO", type="primary"):
                supabase.table("registros_estudos").delete().eq("id", opcoes[alvo_del]).execute()
                st.rerun()
