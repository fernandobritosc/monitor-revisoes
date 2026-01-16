import streamlit as st
import pandas as pd  # CORREÇÃO DA IMAGEM 3D57AC
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Segurança: Proteção contra ausência do ficheiro version.py
try:
    import version
except ImportError:
    class version:
        VERSION = "27.0.0-FIX"
        STATUS = "Blindagem de Cache e API"

# 3. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=300)
def db_get_estudos(usuario, concurso=None):
    query = supabase.table("registros_estudos").select("*").eq("usuario", usuario)
    if concurso: query = query.eq("concurso", concurso)
    res = query.execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['dt_ordenacao'] = pd.to_datetime(df['data_estudo'])
        df['Data'] = df['dt_ordenacao'].dt.strftime('%d/%m/%Y')
        df = df.sort_values('dt_ordenacao', ascending=False)
    return df

@st.cache_data(ttl=600)
def db_get_editais():
    res = supabase.table("editais_materias").select("*").execute()
    editais = {}
    for row in res.data:
        conc = row.get('concurso')
        if not conc: continue
        if conc not in editais:
            dt_raw = row.get('data_prova')
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row.get('cargo') or "Não informado", 
                "data_br": dt_br, "data_iso": dt_raw, "materias": {}
            }
        materia = row.get('materia')
        if materia: editais[conc]["materias"][materia] = row.get('topicos') or []
    return editais

# --- LOGIN E CADASTRO (RESOLVENDO O CASO DO JOÃO) ---
res_u_global = supabase.table("perfil_usuarios").select("*").execute()
users_global = {row['nome']: row for row in res_u_global.data}

if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["Acessar Base", "Novo Guerreiro"])
        with t_log:
            with st.form("login"):
                u = st.selectbox("Guerreiro", list(users_global.keys()) if users_global else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users_global and p == users_global[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("Acesso Negado.")
        with t_cad:
            with st.form("cad"):
                st.info("O João deve usar um Token único.")
                tk = st.text_input("Token")
                n_cad = st.text_input("Nome (Ex: João)")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        try:
                            # CORREÇÃO IMAGEM 3CD3B0: Envio robusto para evitar registo fantasma
                            supabase.table("perfil_usuarios").insert({"nome": n_cad, "pin": pi}).execute()
                            supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                            st.cache_data.clear()
                            st.success("Sucesso! Agora vá na aba Acessar.")
                        except Exception as e:
                            st.error(f"Erro: {str(e)}")
                    else: st.error("Token Inválido ou já usado.")
    st.stop()

# --- CENTRAL DE MISSÕES (CONCURSO NA TELA INICIAL) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()

if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Missão: {usuario_atual}")
    c_sel, c_nov = st.columns([1.5, 1])
    with c_sel:
        st.subheader("🎯 Selecionar Missão")
        if not editais: st.info("Crie o seu primeiro edital ao lado.")
        else:
            for conc in editais.keys():
                if st.button(f"🚀 {conc.upper()}", use_container_width=True):
                    st.session_state.concurso_ativo = conc
                    st.rerun()
    with c_nov:
        st.subheader("➕ Novo Edital")
        with st.form("f_missao"):
            nm = st.text_input("Nome do Concurso")
            cg = st.text_input("Cargo")
            dt = st.date_input("Data da Prova", format="DD/MM/YYYY")
            if st.form_submit_button("CRIAR E INICIAR", use_container_width=True):
                # CORREÇÃO IMAGEM 31894E: Injeção de campos obrigatórios
                supabase.table("editais_materias").insert({
                    "concurso": nm, "cargo": cg, "data_prova": dt.strftime('%Y-%m-%d'), 
                    "materia": "Geral", "topicos": []
                }).execute()
                st.cache_data.clear()
                st.session_state.concurso_ativo = nm
                st.rerun()
    st.stop()

# --- AMBIENTE OPERACIONAL ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 Missão Ativa:\n{concurso_ativo}")
    if st.button("🔄 Trocar de Missão", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
    st.markdown("---")
    menus = ["Dashboard", "Novo Registro", "Gestão do Edital", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu", menus, icons=["bar-chart", "plus-circle", "book-half", "table", "gear"], default_index=0)
    if st.button("Sair"):
        del st.session_state.usuario_logado
        if 'concurso_ativo' in st.session_state: del st.session_state.concurso_ativo
        st.rerun()

# --- TELAS ---
if selected == "Dashboard":
    st.title(f"📊 Desempenho: {concurso_ativo}")
    if not df_missao.empty:
        c1, c2 = st.columns(2)
        tot = int(df_missao['total'].sum())
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{(df_missao['acertos'].sum()/tot*100):.1f}%", border=True)
        df_p = df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        st.plotly_chart(px.line(df_p, x='Data', y='total', markers=True), use_container_width=True)

elif selected == "Novo Registro":
    st.title("📝 Registro de Estudos")
    if concurso_ativo in editais:
        mats = list(editais[concurso_ativo]["materias"].keys())
        mat = st.selectbox("Matéria", mats)
        with st.form("r"):
            d = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            a_list = editais[concurso_ativo]["materias"].get(mat) or ["Geral"]
            asnt = st.selectbox("Assunto", a_list)
            ac = st.number_input("Acertos", 0); tt = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({"data_estudo": d.strftime('%Y-%m-%d'), "usuario": usuario_atual, "concurso": concurso_ativo, "materia": mat, "assunto": asnt, "acertos": int(ac), "total": int(tt), "taxa": (ac/tt*100)}).execute()
                st.cache_data.clear(); st.success("Salvo!")

elif selected == "Gestão do Edital":
    st.title(f"📑 Ajustar Missão: {concurso_ativo}")
    m_n = st.text_input("Nova Matéria")
    if st.button("Adicionar"):
        # CORREÇÃO IMAGEM 318284
        supabase.table("editais_materias").insert({"concurso": concurso_ativo, "materia": m_n, "topicos": [], "cargo": editais[concurso_ativo]['cargo'], "data_prova": editais[concurso_ativo]['data_iso']}).execute()
        st.cache_data.clear(); st.rerun()
    for m, t in editais[concurso_ativo]["materias"].items():
        with st.expander(f"📚 {m}"):
            tx = st.text_area("Tópicos (;)", value="; ".join(t), key=f"t_{m}")
            if st.button("Salvar Assuntos", key=f"b_{m}"):
                novos = [x.strip() for x in tx.split(";") if x.strip()]
                supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", concurso_ativo).eq("materia", m).execute()
                st.cache_data.clear(); st.rerun()

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    st.subheader("👥 Membros do Squad")
    df_u = pd.DataFrame(list(users_global.values()))
    if not df_u.empty:
        st.dataframe(df_u[['nome', 'pin']], use_container_width=True, hide_index=True)
        u_del = st.selectbox("Remover membro (para refazer cadastro):", [""] + list(users_global.keys()))
        if u_del and st.button(f"🗑️ Excluir {u_del}"):
            supabase.table("perfil_usuarios").delete().eq("nome", u_del).execute()
            st.success("Removido! Peça ao João para tentar de novo."); st.rerun()
    if st.button("🎟️ Novo Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
