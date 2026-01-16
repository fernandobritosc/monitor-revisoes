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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    header {visibility: hidden;}
    
    /* Botões */
    .stButton button {
        background-color: #1E1E1E;
        color: #E0E0E0;
        border: 1px solid #333;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    
    /* Métricas e Cards */
    div[data-testid="stMetric"] {
        background-color: #0E0E0E;
        padding: 15px 20px;
        border-radius: 8px;
        border: 1px solid #222;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    
    /* Tabelas Editáveis */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 8px;
    }
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
        # Importante: Buscamos também o ID para poder editar/excluir
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).order("data_estudo", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def calcular_revisoes(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    revisoes = []
    df['dt_obj'] = pd.to_datetime(df['data_estudo']).dt.date
    for _, row in df.iterrows():
        delta = (hoje - row['dt_obj']).days
        motivo = None
        if delta == 1: motivo = "🔥 24 Horas"
        elif delta == 7: motivo = "📅 7 Dias"
        elif delta == 30: motivo = "🧠 30 Dias"
        if motivo:
            revisoes.append({
                "Matéria": row['materia'],
                "Assunto": row['assunto'],
                "Original": row['dt_obj'].strftime('%d/%m'),
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
                            cor = "#FF4B4B" if "Reta Final" in status or "HOJE" in status else "#E0E0E0"
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
                st.warning(f"Isso apaga TUDO de '{alvo}'!")
                if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
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
            icons=["bar-chart-fill", "repeat", "pencil-square", "gear-fill", "table"],
            default_index=0,
            styles={"nav-link-selected": {"background-color": "#FF4B4B"}}
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
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", total)
            c2.metric("Acertos", acertos)
            c3.metric("Precisão", f"{precisao:.1f}%")
            
            st.markdown("---")
            g1, g2 = st.columns([2, 1], gap="medium")
            with g1:
                st.markdown("#### 📈 Evolução")
                df['Data'] = pd.to_datetime(df['data_estudo']).dt.strftime('%d/%m')
                df_chart = df.groupby('Data')[['total', 'acertos']].sum().reset_index()
                fig_area = px.area(df_chart, x='Data', y=['total', 'acertos'], 
                              color_discrete_sequence=['#333333', '#FF4B4B'])
                fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(l=20,r=20,t=20,b=20))
                st.plotly_chart(fig_area, use_container_width=True)
            with g2:
                st.markdown("#### 🎯 Alvo")
                fig_pie = go.Figure(data=[go.Pie(labels=['Acertos', 'Erros'], values=[acertos, erros], hole=.6, marker=dict(colors=['#FF4B4B', '#333333']), textinfo='percent')])
                fig_pie.update_layout(showlegend=True, height=350, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20,r=20,t=20,b=20), legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_pie, use_container_width=True)

    elif menu == "Revisões":
        st.title("🔄 Radar de Revisão")
        df_rev = calcular_revisoes(df)
        if df_rev.empty:
            st.success("✅ Nenhuma revisão pendente para hoje!")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("### 🔥 24 Horas")
                rev_24 = df_rev[df_rev['Tipo'] == "🔥 24 Horas"]
                if not rev_24.empty: st.dataframe(rev_24[['Matéria', 'Assunto']], hide_index=True, use_container_width=True)
                else: st.caption("Nada aqui.")
            with c2:
                st.markdown("### 📅 7 Dias")
                rev_7 = df_rev[df_rev['Tipo'] == "📅 7 Dias"]
                if not rev_7.empty: st.dataframe(rev_7[['Matéria', 'Assunto']], hide_index=True, use_container_width=True)
                else: st.caption("Nada aqui.")
            with c3:
                st.markdown("### 🧠 30 Dias")
                rev_30 = df_rev[df_rev['Tipo'] == "🧠 30 Dias"]
                if not rev_30.empty: st.dataframe(rev_30[['Matéria', 'Assunto']], hide_index=True, use_container_width=True)
                else: st.caption("Nada aqui.")

    elif menu == "Registrar":
        st.title("📝 Novo Registro")
        materias = list(dados.get('materias', {}).keys())
        if not materias: st.warning("⚠️ Adicione matérias em 'Configurar'.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1:
                    mat = st.selectbox("Matéria", materias)
                    topicos = dados['materias'].get(mat, []) or ["Geral"]
                    assunto = st.selectbox("Assunto", topicos)
                with c2:
                    dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                st.divider()
                c3, c4 = st.columns(2)
                acertos = c3.number_input("Acertos", 0, step=1)
                total = c4.number_input("Total", 1, step=1)
                if st.button("SALVAR REGISTRO", type="primary", use_container_width=True):
                    try:
                        supabase.table("registros_estudos").insert({
                            "concurso": missao, "materia": mat, "assunto": assunto,
                            "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": acertos,
                            "total": total, "taxa": (acertos/total)*100
                        }).execute()
                        st.toast("Salvo!", icon="🔥")
                        time.sleep(0.5)
                    except Exception as e: st.error(f"Erro: {e}")

    elif menu == "Configurar":
        st.title("⚙️ Configuração")
        c1, c2 = st.columns([1, 2], gap="medium")
        with c1:
            st.markdown("#### Nova Matéria")
            with st.form("add_mat"):
                nm = st.text_input("Nome")
                if st.form_submit_button("ADICIONAR"):
                    try: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso'), "usuario": "Commander"}).execute()
                    except: supabase.table("editais_materias").insert({"concurso": missao, "materia": nm, "topicos": [], "cargo": dados.get('cargo'), "data_prova": dados.get('data_iso')}).execute()
                    st.rerun()
        with c2:
            st.markdown("#### Matérias")
            for m, t in dados.get('materias', {}).items():
                with st.expander(f"📚 {m}"):
                    new_tops = st.text_area(f"Tópicos", value="; ".join(t), key=f"t_{m}")
                    c_s, c_d = st.columns([4, 1])
                    if c_s.button("Salvar", key=f"s_{m}"):
                        l = [x.strip() for x in new_tops.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()
                    if c_d.button("🗑️", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()

    # --- HISTÓRICO INTELIGENTE (SMART GRID) ---
    elif menu == "Histórico":
        st.title("📜 Histórico Interativo")
        st.info("💡 Dica: Você pode editar os valores diretamente na tabela. Marque a caixa 'Excluir' para apagar.")
        
        if not df.empty:
            # Prepara o DataFrame para edição
            df_edit = df.copy()
            df_edit['Excluir'] = False # Cria a coluna de checkbox
            
            # Organiza as colunas
            df_edit = df_edit[['id', 'Excluir', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa']]
            
            # Configura o Editor
            edited_df = st.data_editor(
                df_edit,
                column_config={
                    "id": None, # Esconde o ID (mas ele existe pro sistema)
                    "Excluir": st.column_config.CheckboxColumn(help="Marque para apagar este registro"),
                    "data_estudo": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "materia": st.column_config.TextColumn("Matéria"),
                    "assunto": st.column_config.TextColumn("Assunto"),
                    "acertos": st.column_config.NumberColumn("Acertos", min_value=0),
                    "total": st.column_config.NumberColumn("Total", min_value=1),
                    "taxa": st.column_config.ProgressColumn("Precisão", format="%.1f%%", min_value=0, max_value=100),
                },
                disabled=["taxa"], # Taxa é calculada, não editada
                hide_index=True,
                use_container_width=True
            )
            
            st.write("")
            if st.button("💾 SALVAR ALTERAÇÕES", type="primary"):
                # 1. Processa Exclusões
                to_delete = edited_df[edited_df['Excluir'] == True]['id'].tolist()
                if to_delete:
                    supabase.table("registros_estudos").delete().in_("id", to_delete).execute()
                
                # 2. Processa Edições (Atualiza tudo que não foi excluído)
                # Iterar e atualizar é mais seguro para garantir consistência
                rows_to_update = edited_df[edited_df['Excluir'] == False]
                
                for index, row in rows_to_update.iterrows():
                    # Recalcula taxa para garantir integridade
                    nova_taxa = (row['acertos'] / row['total'] * 100) if row['total'] > 0 else 0
                    
                    supabase.table("registros_estudos").update({
                        "data_estudo": row['data_estudo'], # Supabase aceita string ISO ou objeto date
                        "materia": row['materia'],
                        "assunto": row['assunto'],
                        "acertos": row['acertos'],
                        "total": row['total'],
                        "taxa": nova_taxa
                    }).eq("id", row['id']).execute()
                
                st.success("Histórico atualizado com sucesso!")
                time.sleep(1)
                st.rerun()
                
        else:
            st.info("Sem dados para exibir.")
