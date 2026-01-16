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
def db_get_estudos(usuario, concurso=None):
    query = supabase.table("registros_estudos").select("*").eq("usuario", usuario)
    if concurso:
        query = query.eq("concurso", concurso)
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

# --- LOGIN E CADASTRO ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["Acessar", "Novo Guerreiro"])
        with t_log:
            with st.form("login"):
                u = st.selectbox("Guerreiro", list(users.keys()) if users else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users and p == users[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("PIN Incorreto")
        with t_cad:
            with st.form("cad"):
                tk = st.text_input("Token")
                n = st.text_input("Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n, "pin": pi}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                        st.success("Conta criada!")
                    else: st.error("Token Inválido")
    st.stop()

# --- SELEÇÃO DE MISSÃO (CONCURSO ATIVO) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()

if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Guerreiro {usuario_atual}, selecione sua missão:")
    if not editais:
        st.info("Nenhum edital ativo. Use a barra lateral para criar um.")
        if st.button("Liberar Menu para Criar Edital"):
            st.session_state.concurso_ativo = "Configuração"
            st.rerun()
    else:
        for conc in editais.keys():
            if st.button(f"🚀 INICIAR OPERAÇÃO: {conc.upper()}", use_container_width=True):
                st.session_state.concurso_ativo = conc
                st.rerun()
    st.stop()

# --- AMBIENTE OPERACIONAL ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 Missão: **{concurso_ativo}**")
    if st.button("🔄 Trocar de Missão"):
        del st.session_state.concurso_ativo
        st.rerun()
    st.markdown("---")
    menus = ["Dashboard", "Novo Registro", "Gestão Editais", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    selected = option_menu("Menu", menus, icons=["bar-chart", "plus-circle", "book-half", "table", "gear"], default_index=0)
    
    if st.button("🚪 Sair"):
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
    else: st.info("Sem dados nesta missão.")

elif selected == "Novo Registro":
    st.title(f"📝 Registro: {concurso_ativo}")
    if concurso_ativo in editais:
        materias = list(editais[concurso_ativo]["materias"].keys())
        mat = st.selectbox("Matéria", materias)
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass_list = editais[concurso_ativo]["materias"].get(mat) or ["Geral"]
            ass = st.selectbox("Assunto", ass_list)
            a = st.number_input("Acertos", 0); t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": concurso_ativo, "materia": mat, "assunto": ass, "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear(); st.success("Salvo!")
    else: st.error("Edital não configurado.")

elif selected == "Gestão Editais":
    st.title("📑 Gestão Geral de Editais")
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
            sel = st.selectbox("Selecione para Editar", list(editais.keys()))
            if st.checkbox(f"🗑️ EXCLUIR CONCURSO {sel}"):
                if st.button("Confirmar Exclusão Total"):
                    supabase.table("editais_materias").delete().eq("concurso", sel).execute()
                    st.cache_data.clear(); st.rerun()
            
            st.markdown("---")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({"concurso": sel, "materia": m_n, "topicos": [], "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']}).execute()
                st.cache_data.clear(); st.rerun()

            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    novo_m = st.text_input("Renomear", value=m, key=f"r_{m}")
                    if novo_m != m and st.button("Salvar Nome", key=f"br_{m}"):
                        supabase.table("editais_materias").update({"materia": novo_m}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear(); st.rerun()
                    txt = st.text_area("Tópicos (;)", value="; ".join(t), key=f"t_{m}")
                    if st.button("Atualizar Tópicos", key=f"bt_{m}"):
                        novos = [x.strip() for x in txt.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear(); st.rerun()
                    if st.checkbox(f"Excluir {m}", key=f"c_{m}"):
                        if st.button(f"Confirmar Delete {m}", key=f"d_{m}"):
                            supabase.table("editais_materias").delete().eq("concurso", sel).eq("materia", m).execute()
                            st.cache_data.clear(); st.rerun()

elif selected == "Histórico":
    st.title(f"📜 Histórico: {concurso_ativo}")
    if not df_missao.empty:
        st.dataframe(df_missao[['Data', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema e Segurança")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Backup")
        if st.button("Gerar Snapshot JSON"):
            ed = supabase.table("editais_materias").select("*").execute().data
            reg = supabase.table("registros_estudos").select("*").execute().data
            st.download_button("Baixar Backup", json.dumps({"editais": ed, "registros": reg}), "squad_backup.json")
    with c2:
        st.subheader("🎟️ Convites")
        if st.button("Novo Token"):
            tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
            supabase.table("tokens_convite").insert({"codigo": tk}).execute()
            st.code(tk)
