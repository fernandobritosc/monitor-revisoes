import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL PRO (CSS AVANÇADO) ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0E0E0E;
    }
    
    /* Remove cabeçalho padrão */
    header {visibility: hidden;}
    
    /* Estilo dos Botões */
    .stButton button {
        background-color: #262626;
        color: #FFFFFF;
        border: 1px solid #333;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #DC2626; /* Vermelho Sangue */
        border-color: #DC2626;
        color: white;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    }
    
    /* Cards de Métricas */
    div[data-testid="stMetric"] {
        background-color: #171717;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #333;
    }
    
    /* Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #171717 !important;
        border: 1px solid #333 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    /* Cards do Radar (Custom Class) */
    .revision-card {
        background-color: #1E1E1E;
        border-left: 4px solid #DC2626;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .revision-title { font-weight: 700; color: #FFF; font-size: 1.1em; }
    .revision-sub { color: #A3A3A3; font-size: 0.9em; margin-top: 4px; }
    
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
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).order("data_estudo", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def calcular_revisoes(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    revisoes = []
    # Conversão Segura
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    
    for _, row in df.iterrows():
        delta = (hoje - row['dt_temp']).days
        motivo = None
        if delta == 1: motivo = "🔥 24h"
        elif delta == 7: motivo = "📅 7 Dias"
        elif delta == 30: motivo = "🧠 30 Dias"
        if motivo:
            revisoes.append({
                "Matéria": row['materia'],
                "Assunto": row['assunto'],
                "Original": row['dt_temp'].strftime('%d/%m'),
                "Tipo": motivo
            })
    return pd.DataFrame(revisoes)

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
                            cor = "#DC2626" if "Reta Final" in status or "HOJE" in status else "#A3A3A3"
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
                        try:
                            supabase.table("editais_materias").insert({
                                "concurso": nm, "cargo": cg, 
                                "data_prova": dt.strftime('%Y-%m-%d'),
                                "materia": "Geral", "topicos": [], "usuario": "Commander"
                            }).execute()
                        except:
                             supabase.table("editais_materias").insert({
                                "concurso": nm, "cargo": cg, 
                                "data_prova": dt.strftime('%Y-%m-%d'),
                                "materia": "Geral", "topicos": []
                            }).execute()
                        st.toast(f"Missão {nm} criada!")
                        time.sleep(1); st.rerun()

        st.write("") 
        with st.container(border=True):
            st.markdown("**🗑️ Zona de Perigo**")
            lista_del = ["Selecione..."] + list(editais.keys())
            alvo = st.selectbox("Apagar Missão:", lista_del)
            if alvo != "Selecione...":
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
            options=["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"],
            icons=["bar-chart-fill", "repeat", "clock", "gear-fill", "table"],
            default_index=0,
            styles={"nav-link-selected": {"background-color": "#DC2626"}}
        )

    if menu == "Dashboard":
        st.title("📊 Painel Tático")
        if df.empty:
            st.info("Inicie os registros para ver estatísticas.")
        else:
            total = int(df['total'].sum())
            acertos = int(df['acertos'].sum())
            erros = total - acertos
            precisao = (acertos / total * 100) if total > 0 else 0
            
            # Cálculo Tempo
            if 'tempo' in df.columns:
                total_minutos = df['tempo'].fillna(0).sum()
                horas_liquidas = int(total_minutos // 60)
                min_restantes = int(total_minutos % 60)
                txt_tempo = f"{horas_liquidas}h {min_restantes}m"
            else: txt_tempo = "0h 0m"
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões", total)
            c2.metric("Acertos", acertos)
            c3.metric("Precisão", f"{precisao:.1f}%")
            c4.metric("Horas Líquidas", txt_tempo)
            
            st.markdown("---")
            g1, g2 = st.columns([2, 1], gap="medium")
            with g1:
                st.markdown("#### 📈 Evolução")
                df['Data'] = pd.to_datetime(df['data_estudo']).dt.strftime('%d/%m')
                df_chart = df.groupby('Data')[['total', 'acertos']].sum().reset_index()
                fig_area = px.area(df_chart, x='Data', y=['total', 'acertos'], 
                              color_discrete_sequence=['#333333', '#DC2626'])
                fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(l=20,r=20,t=20,b=20))
                st.plotly_chart(fig_area, use_container_width=True)
            with g2:
                st.markdown("#### 🎯 Alvo")
                fig_pie = go.Figure(data=[go.Pie(labels=['Acertos', 'Erros'], values=[acertos, erros], hole=.6, marker=dict(colors=['#DC2626', '#333333']), textinfo='percent')])
                fig_pie.update_layout(showlegend=True, height=350, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20,r=20,t=20,b=20), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_pie, use_container_width=True)

    # --- RADAR REFORMULADO (VISUAL DE CARDS) ---
    elif menu == "Revisões":
        st.title("🔄 Radar de Revisão")
        st.caption("O sistema identifica automaticamente o que você estudou há 1, 7 ou 30 dias.")
        
        df_rev = calcular_revisoes(df)
        
        if df_rev.empty:
            st.markdown("""
            <div style="text-align: center; padding: 50px; background-color: #171717; border-radius: 12px; border: 1px dashed #333;">
                <h1 style="font-size: 3em;">✅</h1>
                <h3>Tudo Limpo, Comandante!</h3>
                <p style="color: #666;">Você não tem revisões pendentes para hoje.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            c1, c2, c3 = st.columns(3)
            
            def render_card(row, color="#DC2626"):
                st.markdown(f"""
                <div class="revision-card" style="border-left-color: {color};">
                    <div class="revision-title">{row['Matéria']}</div>
                    <div class="revision-sub">{row['Assunto']}</div>
                </div>
                """, unsafe_allow_html=True)

            with c1:
                st.markdown("### 🔥 24 Horas")
                revs = df_rev[df_rev['Tipo'] == "🔥 24h"]
                if revs.empty: st.info("Nada.")
                else:
                    for _, row in revs.iterrows(): render_card(row, "#DC2626")

            with c2:
                st.markdown("### 📅 7 Dias")
                revs = df_rev[df_rev['Tipo'] == "📅 7 Dias"]
                if revs.empty: st.info("Nada.")
                else:
                    for _, row in revs.iterrows(): render_card(row, "#F59E0B")

            with c3:
                st.markdown("### 🧠 30 Dias")
                revs = df_rev[df_rev['Tipo'] == "🧠 30 Dias"]
                if revs.empty: st.info("Nada.")
                else:
                    for _, row in revs.iterrows(): render_card(row, "#3B82F6")

    elif menu == "Registrar":
        st.title("📝 Novo Registro")
        materias = list(dados.get('materias', {}).keys())
        if not materias: st.warning("⚠️ Adicione matérias em 'Configurar'.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    mat = st.selectbox("Matéria", materias)
                    topicos = dados['materias'].get(mat, []) or ["Geral"]
                    assunto = st.selectbox("Assunto", topicos)
                with c2:
                    dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                
                st.divider()
                
                c_time, c_perf = st.columns([1, 1.5])
                
                with c_time:
                    st.caption("⏱️ Tempo Líquido")
                    t1, t2 = st.columns(2)
                    horas = t1.selectbox("Hs", list(range(13)), index=0)
                    minutos = t2.selectbox("Min", list(range(60)), index=0)
                
                with c_perf:
                    st.caption("🎯 Desempenho")
                    p1, p2 = st.columns(2)
                    acertos = p1.number_input("Acertos", 0, step=1)
                    total = p2.number_input("Total", 1, step=1)
                
                st.write("")
                if st.button("SALVAR REGISTRO", type="primary", use_container_width=True):
                    tempo_total_min = (horas * 60) + minutos
                    try:
                        supabase.table("registros_estudos").insert({
                            "concurso": missao, "materia": mat, "assunto": assunto,
                            "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": acertos,
                            "total": total, "taxa": (acertos/total)*100,
                            "tempo": tempo_total_min
                        }).execute()
                        st.toast(f"Registro Salvo! Desempenho registrado.", icon="🔥")
                        time.sleep(0.5)
                    except Exception as e: st.error(f"Erro: {e}")

    elif menu == "Configurar":
        st.title("⚙️ Configuração")
        c1, c2 = st.columns([1, 2], gap="medium")
        with c1:
            with st.container(border=True):
                st.markdown("**Nova Matéria**")
                with st.form("add_mat"):
                    nm = st.text_input("Nome", label_visibility="collapsed", placeholder="Ex: Direito Penal")
                    if st.form_submit_button("ADICIONAR"):
                        try: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso'), "usuario": "Commander"}).execute()
                        except: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso')}).execute()
                        st.rerun()
        with c2:
            st.markdown("#### Matérias do Edital")
            for m, t in dados.get('materias', {}).items():
                with st.expander(f"📚 {m}"):
                    new_tops = st.text_area(f"Tópicos", value="; ".join(t), key=f"t_{m}", height=100)
                    c_s, c_d = st.columns([4, 1])
                    if c_s.button("Salvar", key=f"s_{m}"):
                        l = [x.strip() for x in new_tops.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                        st.toast("Salvo!")
                        time.sleep(0.5); st.rerun()
                    if c_d.button("🗑️", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()

    elif menu == "Histórico":
        st.title("📜 Gestão de Registros")
        
        if not df.empty:
            df['data_estudo'] = pd.to_datetime(df['data_estudo']).dt.date
            if 'tempo' not in df.columns: df['tempo'] = 0
            
            # --- ZONA 1: EDIÇÃO ---
            with st.expander("✏️  Modo de Edição Rápida", expanded=True):
                df_edit = df[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo']].copy()
                edited_df = st.data_editor(
                    df_edit,
                    column_config={
                        "id": None,
                        "data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "materia": st.column_config.TextColumn("Matéria"),
                        "assunto": st.column_config.TextColumn("Assunto"),
                        "acertos": st.column_config.NumberColumn("Acertos"),
                        "total": st.column_config.NumberColumn("Total"),
                        "taxa": st.column_config.ProgressColumn("Precisão", format="%.1f%%"),
                        "tempo": st.column_config.NumberColumn("Min")
                    },
                    disabled=["taxa", "materia", "assunto"], 
                    hide_index=True,
                    use_container_width=True,
                    key="editor_history"
                )
                if st.button("💾 SALVAR EDIÇÕES", type="primary"):
                    for index, row in edited_df.iterrows():
                        nova_taxa = (row['acertos'] / row['total'] * 100) if row['total'] > 0 else 0
                        try:
                            supabase.table("registros_estudos").update({
                                "data_estudo": row['data_estudo'].strftime('%Y-%m-%d'),
                                "acertos": row['acertos'],
                                "total": row['total'],
                                "taxa": nova_taxa,
                                "tempo": row['tempo']
                            }).eq("id", row['id']).execute()
                        except: pass
                    st.success("Atualizado!")
                    time.sleep(1)
                    st.rerun()

            # --- ZONA 2: EXCLUSÃO ---
            st.write("")
            with st.container(border=True):
                st.markdown("**🗑️ Zona de Exclusão**")
                df['label'] = df.apply(lambda x: f"{x['data_estudo'].strftime('%d/%m')} | {x['materia']} | {x['acertos']}/{x['total']}", axis=1)
                opcoes_del = dict(zip(df['label'], df['id']))
                c_sel, c_btn = st.columns([3, 1])
                escolha = c_sel.selectbox("Registro para apagar:", ["Selecione..."] + list(opcoes_del.keys()), label_visibility="collapsed")
                
                if escolha != "Selecione..." and c_btn.button("APAGAR", type="primary"):
                    supabase.table("registros_estudos").delete().eq("id", opcoes_del[escolha]).execute()
                    st.success("Apagado.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Sem dados.")
