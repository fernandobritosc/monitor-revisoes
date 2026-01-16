import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=300)
def db_get_estudos(usuario=None):
    query = supabase.table("registros_estudos").select("*")
    if usuario: query = query.eq("usuario", usuario)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['dt_ordenacao'] = pd.to_datetime(df['data_estudo'])
        df['Data'] = df['dt_ordenacao'].dt.strftime('%d/%m/%Y')
        df = df.sort_values('dt_ordenacao', ascending=False)
    return df

@st.cache_data(ttl=3600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row['concurso']
        if conc not in editais:
            dt_raw = row['data_prova']
            dt_br = "A definir"
            if dt_raw:
                try: dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
                except: dt_br = "Erro"
            editais[conc] = {
                "cargo": row.get('cargo') or "Não informado", 
                "data_br": dt_br, "data_iso": dt_raw, "materias": {}
            }
        materia = row.get('materia')
        if materia: editais[conc]["materias"][materia] = row.get('topicos') or []
    return editais

# --- ACESSO ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Entrar", "Novo Guerreiro"])
        with tab1:
            with st.form("login"):
                u = st.selectbox("Guerreiro", list(users.keys()) if users else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users and p == users[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("Erro")
        with tab2:
            with st.form("cad"):
                tk = st.text_input("Token")
                n = st.text_input("Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n, "pin": pi}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                        st.success("Criado!")
                    else: st.error("Token Inválido")
    st.stop()

# --- AMBIENTE OPERACIONAL ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu", menus, default_index=0)
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()
    if st.button("Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# --- LÓGICA DE NAVEGAÇÃO (IF/ELIF/ELSE CORRIGIDO) ---

if selected == "Dashboard":
    st.title("📊 Painel Analytics")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        tot = int(df_meu['total'].sum())
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{(df_meu['acertos'].sum()/tot*100):.1f}%", border=True)
        df_p = df_meu.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        fig = px.line(df_p, x='Data', y='total', markers=True)
        fig.update_xaxes(type='category', title="Data") 
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

elif selected == "Novo Registro":
    st.title("📝 Registrar Estudo")
    if not editais: st.warning("Crie um edital.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass = st.selectbox("Tópico", editais[conc]["materias"].get(mat) or ["Geral"])
            a = st.number_input("Acertos", 0); t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear(); st.success("Salvo!")

elif selected == "Ranking Squad":
    st.title("🏆 Ranking")
    res_all = supabase.table("registros_estudos").select("usuario, total").execute()
    df_all = pd.DataFrame(res_all.data)
    if not df_all.empty:
        rank = df_all.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h'), use_container_width=True)

elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Matérias e Assuntos"])
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso"); c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral", "topicos": []}).execute()
                st.cache_data.clear(); st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Escolha o Edital", list(editais.keys()))
            c1, c2 = st.columns(2)
            with c1: st.info(f"📍 {editais[sel]['cargo']} | 📅 {editais[sel]['data_br']}")
            with c2: 
                if st.checkbox("⚠️ EXCLUIR EDITAL INTEIRO", key=f"del_ed_{sel}"):
                    if st.button(f"Confirmar Exclusão de {sel}"):
                        supabase.table("editais_materias").delete().eq("concurso", sel).execute()
                        st.cache_data.clear(); st.rerun()

            st.markdown("---")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar Matéria"):
                supabase.table("editais_materias").insert({"concurso": sel, "materia": m_n, "topicos": [], "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']}).execute()
                st.cache_data.clear(); st.rerun()

            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    novo_m = st.text_input("Renomear Matéria", value=m, key=f"ren_{m}")
                    if novo_m != m:
                        if st.button(f"Salvar Nome", key=f"b_ren_{m}"):
                            supabase.table("editais_materias").update({"materia": novo_m}).eq("concurso", sel).eq("materia", m).execute()
                            st.cache_data.clear(); st.rerun()
                    
                    txt = st.text_area(f"Tópicos (separe por ;)", value="; ".join(t), key=f"txt_{m}")
                    if st.button(f"Atualizar Tópicos", key=f"b_top_{m}"):
                        novos = [x.strip() for x in txt.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear(); st.rerun()
                    
                    if st.checkbox(f"Excluir matéria {m}", key=f"chk_del_{m}"):
                        if st.button(f"🗑️ APAGAR {m.upper()}", key=f"del_mat_{m}"):
                            supabase.table("editais_materias").delete().eq("concurso", sel).eq("materia", m).execute()
                            st.cache_data.clear(); st.rerun()

elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        st.dataframe(df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    if st.button("🎟️ Novo Token Convite"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
