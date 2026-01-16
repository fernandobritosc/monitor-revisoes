import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import plotly.graph_objects as go
import secrets
import string

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNÇÕES COM CACHE ---

@st.cache_data(ttl=600)
def db_get_usuarios():
    res = supabase.table("perfil_usuarios").select("*").execute()
    return {row['nome']: row for row in res.data}

@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario:
        query = query.eq("usuario", usuario)
    res = query.execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_raw": dt_raw, # Mantemos o formato ISO para o input
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

def db_get_tokens():
    res = supabase.table("tokens_convite").select("*").eq("usado", False).execute()
    return [t['codigo'] for t in res.data]

# --- LÓGICA DE STREAK ---
def get_streak_metrics(df):
    if df.empty or 'data_estudo' not in df.columns: return 0, 0
    try:
        dates = pd.to_datetime(df['data_estudo']).dt.normalize().dropna().unique()
        dates = sorted(dates)
        if not len(dates): return 0, 0
        max_s, cur_s = 1, 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1: cur_s += 1
            else: max_s = max(max_s, cur_s); cur_s = 1
        max_s = max(max_s, cur_s)
        hoje = pd.Timestamp.now().normalize()
        sa = 0
        dr = sorted(dates, reverse=True)
        if hoje in dr: sa = 1; ck = hoje - pd.Timedelta(days=1)
        elif (hoje - pd.Timedelta(days=1)) in dr: sa = 0; ck = hoje - pd.Timedelta(days=1)
        else: return 0, max_s
        for d in dr:
            if d == hoje: continue
            if d == ck: sa += 1; ck -= pd.Timedelta(days=1)
            else: break
        return sa, max_s
    except: return 0, 0

# --- LOGIN ---
if 'usuario_logado' not in st.session_state:
    users = db_get_usuarios()
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Acessar Base", "Novo Guerreiro", "Recuperar PIN"])
        
        with t1:
            if not users:
                st.info("Nenhum usuário cadastrado.")
                if st.button("Gerar Token de Primeiro Acesso"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"Token: {tk}")
            else:
                with st.form("login_form"):
                    u = st.selectbox("Quem está acessando?", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("PIN incorreto.")

        with t2:
            with st.form("cadastro_form"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Nome do Guerreiro")
                p_in = st.text_input("PIN (4 dígitos)", type="password", max_chars=4)
                ch_in = st.text_input("Palavra-Chave (Reset)")
                if st.form_submit_button("CRIAR CONTA"):
                    ativos = db_get_tokens()
                    if tk_in in ativos:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in, "chave_recuperacao": ch_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Criado! Faça login.")
                    else: st.error("Token inválido.")
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    icons = ["bar-chart", "plus-circle", "trophy", "book-half", "table"]
    if usuario_atual == "Fernando Pinheiro":
        menus.append("Gerar Convites")
        icons.append("ticket-perforated")
    
    selected = option_menu("Menu Tático", menus, icons=icons, default_index=0)

# --- PÁGINAS ---

if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
        df_meu['total'] = pd.to_numeric(df_meu['total'])
        df_meu['acertos'] = pd.to_numeric(df_meu['acertos'])
        total_q = df_meu['total'].sum()
        prec = (df_meu['acertos'].sum() / total_q * 100) if total_q > 0 else 0
        sa, mx = get_streak_metrics(df_meu)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", int(total_q), border=True)
        c2.metric("Precisão", f"{prec:.1f}%", border=True)
        c3.metric("🔥 Streak", f"{sa}d", border=True)
        c4.metric("🏆 Recorde", f"{mx}d", border=True)
        
        st.markdown("---")
        df_meu['data_real'] = pd.to_datetime(df_meu['data_estudo'])
        df_evol = df_meu.groupby('data_real')['total'].sum().reset_index()
        fig = px.line(df_evol, x='data_real', y='total', title="Evolução de Estudos", markers=True)
        fig.update_traces(line_color='#00E676')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Registre estudos para ver seus dados.")

elif selected == "Novo Registro":
    st.title("📝 Novo Registro")
    if not editais: st.warning("Cadastre um edital primeiro!")
    else:
        conc = st.selectbox("Edital", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        topicos = editais[conc]["materias"][mat]
        with st.form("reg_form", clear_on_submit=True):
            dt = st.date_input("Data", datetime.date.today())
            ass = st.selectbox("Tópico", topicos)
            a, t = st.columns(2)
            ac_v = a.number_input("Acertos", 0)
            tot_v = t.number_input("Total", 1)
            if st.form_submit_button("SALVAR ESTUDO", use_container_width=True):
                tx = (ac_v/tot_v*100)
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass,
                    "acertos": ac_v, "total": tot_v, "taxa": tx
                }).execute()
                st.cache_data.clear()
                st.success("Salvo com sucesso!")

elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Squad")
    df_g = db_get_estudos()
    if not df_g.empty:
        df_g['total'] = pd.to_numeric(df_g['total'])
        rank = df_g.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h', color="usuario"), use_container_width=True)

elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    tab_novo, tab_edit = st.tabs(["➕ Novo Edital", "✏️ Editar Existente"])

    with tab_novo:
        with st.form("novo_conc_form"):
            c1, c2, c3 = st.columns([2, 2, 1])
            nome_c = c1.text_input("Nome do Concurso")
            cargo_c = c2.text_input("Cargo")
            data_c = c3.date_input("Data da Prova")
            if st.form_submit_button("Criar Edital"):
                if nome_c:
                    supabase.table("editais_materias").insert({
                        "concurso": nome_c, "materia": "Geral", "topicos": [],
                        "cargo": cargo_c, "data_prova": data_c.strftime('%Y-%m-%d')
                    }).execute()
                    st.cache_data.clear()
                    st.success(f"Edital {nome_c} criado!")
                    st.rerun()

    with tab_edit:
        if editais:
            ed_sel = st.selectbox("Selecione para Editar", list(editais.keys()), key="sel_edit")
            
            # Formulário de edição dos dados gerais
            with st.form("edit_geral_form"):
                st.markdown("##### Alterar Informações Gerais")
                c1, c2, c3 = st.columns([2, 2, 1])
                # Nota: Mudar o nome do concurso é complexo pois ele é usado como chave. 
                # Por agora, permitimos mudar Cargo e Data.
                novo_cargo = c1.text_input("Novo Cargo", value=editais[ed_sel]['cargo'])
                
                # Tratamento da data atual para o input
                data_atual_dt = datetime.date.today()
                if editais[ed_sel]['data_raw']:
                    try: data_atual_dt = datetime.datetime.strptime(editais[ed_sel]['data_raw'], '%Y-%m-%d').date()
                    except: pass
                
                nova_data = c3.date_input("Nova Data da Prova", value=data_atual_dt)
                
                if st.form_submit_button("Salvar Alterações Gerais"):
                    supabase.table("editais_materias").update({
                        "cargo": novo_cargo,
                        "data_prova": nova_data.strftime('%Y-%m-%d')
                    }).eq("concurso", ed_sel).execute()
                    st.cache_data.clear()
                    st.success("Informações atualizadas!")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("##### Gerir Matérias e Tópicos")
            col1, col2 = st.columns([1, 2])
            with col1:
                nova_m = st.text_input("Nova Matéria")
                if st.button("Adicionar Matéria") and nova_m:
                    supabase.table("editais_materias").insert({
                        "concurso": ed_sel, "materia": nova_m, "topicos": [],
                        "cargo": editais[ed_sel]['cargo'],
                        "data_prova": editais[ed_sel]['data_raw']
                    }).execute()
                    st.cache_data.clear()
                    st.rerun()
            with col2:
                for m, t in editais[ed_sel]["materias"].items():
                    with st.expander(f"📚 {m} ({len(t)} tópicos)"):
                        txt = st.text_area(f"Importar Tópicos para {m}", value="; ".join(t), key=f"t_{m}")
                        if st.button("Atualizar Lista", key=f"b_{m}"):
                            novos = [x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()]
                            supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", ed_sel).eq("materia", m).execute()
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("Nenhum edital cadastrado para editar.")

elif selected == "Gerar Convites":
    st.title("🎟️ Central de Convites")
    if st.button("Gerar Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
        st.success("Mande este token para seu amigo.")
