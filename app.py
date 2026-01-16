import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO VISUAL PRO ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0E0E0E;
    }
    header {visibility: hidden;}
    
    .stButton button {
        background-color: #262626;
        color: #FFFFFF;
        border: 1px solid #333;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #DC2626;
        border-color: #DC2626;
        color: white;
    }
    
    div[data-testid="stMetric"] {
        background-color: #171717;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #333;
    }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #171717 !important;
        border: 1px solid #333 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    /* CARDS DE REVISÃO */
    .rev-card {
        background-color: #171717;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 5px solid #555;
    }
    .rev-24h { border-left-color: #EF4444; } /* Vermelho */
    .rev-07d { border-left-color: #F59E0B; } /* Laranja */
    .rev-15d { border-left-color: #3B82F6; } /* Azul */
    .rev-30d { border-left-color: #10B981; } /* Verde */
    
    .rev-title { font-weight: bold; font-size: 14px; color: #FFF; }
    .rev-sub { font-size: 12px; color: #AAA; }
    .rev-date { font-size: 11px; color: #666; margin-top: 5px; }

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
    except: return data_iso, None

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

# --- LÓGICA DE REVISÃO ACUMULATIVA (STICKY) ---
def calcular_revisoes_pendentes(df):
    if df.empty: return []
    
    hoje = datetime.date.today()
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    
    pendencias = []
    
    # Se as colunas não existirem no DF (banco antigo), cria como False para não quebrar
    for col in ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']:
        if col not in df.columns: df[col] = False

    for _, row in df.iterrows():
        dias_passados = (hoje - row['dt_temp']).days
        
        # REGRA 24 HORAS (>= 1 dia e não feito)
        if dias_passados >= 1 and row['rev_24h'] is False:
            pendencias.append({
                "id": row['id'], "Fase": "24h", "Matéria": row['materia'], 
                "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'),
                "DiasAtraso": dias_passados - 1
            })
            
        # REGRA 7 DIAS (>= 7 dias e não feito)
        if dias_passados >= 7 and row['rev_07d'] is False:
             pendencias.append({
                "id": row['id'], "Fase": "07d", "Matéria": row['materia'], 
                "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'),
                "DiasAtraso": dias_passados - 7
            })

        # REGRA 15 DIAS (>= 15 dias e não feito)
        if dias_passados >= 15 and row['rev_15d'] is False:
             pendencias.append({
                "id": row['id'], "Fase": "15d", "Matéria": row['materia'], 
                "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'),
                "DiasAtraso": dias_passados - 15
            })

        # REGRA 30 DIAS (>= 30 dias e não feito)
        if dias_passados >= 30 and row['rev_30d'] is False:
             pendencias.append({
                "id": row['id'], "Fase": "30d", "Matéria": row['materia'], 
                "Assunto": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'),
                "DiasAtraso": dias_passados - 30
            })
            
    return pd.DataFrame(pendencias)

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
            if alvo != "Selecione..." and st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                supabase.table("registros_estudos").delete().eq("concurso", alvo).execute()
                supabase.table("editais_materias").delete().eq("concurso", alvo).execute()
                st.success("Missão eliminada."); time.sleep(1); st.rerun()

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
            icons=["bar-chart-fill", "check-circle", "clock", "gear-fill", "table"],
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

    # --- RADAR DE REVISÃO (AGORA COM BOTÃO DE CONCLUIR) ---
    elif menu == "Revisões":
        st.title("🔄 Radar de Revisão Acumulada")
        st.caption("As revisões só somem quando você marcar como 'Feito'.")
        
        df_pendentes = calcular_revisoes_pendentes(df)
        
        if len(df_pendentes) == 0:
            st.markdown("""
            <div style="text-align: center; padding: 50px; background-color: #171717; border-radius: 12px; border: 1px dashed #333;">
                <h1 style="font-size: 3em;">✅</h1>
                <h3>Dever Cumprido!</h3>
                <p style="color: #666;">Nenhuma revisão pendente no momento.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Dividir por colunas (Fases)
            cols = st.columns(4)
            fases = ["24h", "07d", "15d", "30d"]
            titulos = ["🔥 24 Horas", "📅 7 Dias", "🧠 15 Dias", "💎 30 Dias"]
            
            for i, fase in enumerate(fases):
                with cols[i]:
                    st.markdown(f"### {titulos[i]}")
                    # Filtra tarefas dessa fase
                    tasks = df_pendentes[df_pendentes['Fase'] == fase]
                    
                    if tasks.empty:
                        st.caption("Vazio")
                    else:
                        for _, row in tasks.iterrows():
                            # Renderiza o Card
                            css_class = f"rev-{fase}"
                            st.markdown(f"""
                            <div class="rev-card {css_class}">
                                <div class="rev-title">{row['Matéria']}</div>
                                <div class="rev-sub">{row['Assunto']}</div>
                                <div class="rev-date">Estudado em: {row['Data']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Botão de Concluir (Lógica de Banco de Dados)
                            # Usamos uma chave única para o botão não confundir
                            btn_key = f"btn_done_{row['id']}_{fase}"
                            if st.button("✅ Feito", key=btn_key, use_container_width=True):
                                # Define qual coluna atualizar no banco
                                col_db = ""
                                if fase == "24h": col_db = "rev_24h"
                                elif fase == "07d": col_db = "rev_07d"
                                elif fase == "15d": col_db = "rev_15d"
                                elif fase == "30d": col_db = "rev_30d"
                                
                                # Atualiza Supabase
                                try:
                                    supabase.table("registros_estudos").update({col_db: True}).eq("id", row['id']).execute()
                                    st.toast("Revisão Concluída!", icon="🎉")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}. Verifique se criou a coluna '{col_db}' no Supabase.")

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
                            "tempo": tempo_total_min,
                            # Inicia revisões como False
                            "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                        }).execute()
                        st.toast(f"Salvo!", icon="🔥")
                        time.sleep(0.5)
                    except Exception as e:
                        if "rev_" in str(e) or "column" in str(e):
                            st.error("ERRO: Você criou as colunas 'rev_24h', 'rev_07d', etc no Supabase?")
                        else: st.error(f"Erro: {e}")

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
                    hide_index=True, use_container_width=True, key="editor_history"
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
                    st.success("Atualizado!"); time.sleep(1); st.rerun()

            st.write("")
            with st.container(border=True):
                st.markdown("**🗑️ Zona de Exclusão**")
                df['label'] = df.apply(lambda x: f"{x['data_estudo'].strftime('%d/%m')} | {x['materia']} | {x['acertos']}/{x['total']}", axis=1)
                opcoes_del = dict(zip(df['label'], df['id']))
                c_sel, c_btn = st.columns([3, 1])
                escolha = c_sel.selectbox("Registro para apagar:", ["Selecione..."] + list(opcoes_del.keys()), label_visibility="collapsed")
                
                if escolha != "Selecione..." and c_btn.button("APAGAR", type="primary"):
                    supabase.table("registros_estudos").delete().eq("id", opcoes_del[escolha]).execute()
                    st.success("Apagado."); time.sleep(1); st.rerun()
        else:
            st.info("Sem dados.")
