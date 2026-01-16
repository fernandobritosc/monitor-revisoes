import streamlit as st
import pandas as pd
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import plotly.express as px
import secrets
import string
import version # Importa o nosso controlo de versão

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Erro de conexão. Verifique os Secrets.")
        st.stop()

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS (BLINDAGEM E GESTÃO) ---

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
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row['cargo'] or "Não informado", 
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        editais[conc]["materias"][row['materia']] = row['topicos']
    return editais

# --- SISTEMA DE LOGIN ---
if 'usuario_logado' not in st.session_state:
    res_u = supabase.table("perfil_usuarios").select("*").execute()
    users = {row['nome']: row for row in res_u.data}
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Acessar Base", "Novo Guerreiro"])
        with t1:
            if not users:
                if st.button("Gerar Token Inicial"):
                    tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                    supabase.table("tokens_convite").insert({"codigo": tk}).execute()
                    st.success(f"TOKEN: {tk}")
            else:
                with st.form("login_f"):
                    u = st.selectbox("Quem está acessando?", list(users.keys()))
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p == users[u]['pin']:
                            st.session_state.usuario_logado = u
                            st.rerun()
                        else: st.error("PIN Incorreto.")
        with t2:
            with st.form("cad_f"):
                tk_in = st.text_input("Token de Convite")
                n_in = st.text_input("Seu Nome")
                p_in = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk_in).eq("usado", False).execute()
                    if res_tk.data:
                        supabase.table("perfil_usuarios").insert({"nome": n_in, "pin": p_in}).execute()
                        supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk_in).execute()
                        st.cache_data.clear()
                        st.success("Conta criada! Vá em Acessar.")
                    else: st.error("Token Inválido.")
    st.stop()

# --- AMBIENTE OPERACIONAL ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()
df_meu = db_get_estudos(usuario_atual)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    icons = ["bar-chart", "plus-circle", "trophy", "book-half", "table"]
    
    if usuario_atual == "Fernando Pinheiro":
        menus.append("⚙️ Gestão de Sistema")
        icons.append("gear")
    
    selected = option_menu("Menu Tático", menus, icons=icons, default_index=0)
    
    # RODAPÉ DE VERSÃO
    st.markdown("---")
    st.caption(f"🚀 Versão: {version.VERSION}")
    st.caption(f"🟢 Status: {version.STATUS}")
    if st.button("🔄 Sincronizar Tudo"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        st.rerun()

# --- LÓGICA DOS MENUS ---

if selected == "Dashboard":
    st.title("📊 Performance")
    if not df_meu.empty:
        c1, c2 = st.columns(2)
        tot = int(df_meu['total'].sum())
        prec = (df_meu['acertos'].sum()/tot*100) if tot > 0 else 0
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{prec:.1f}%", border=True)
        
        df_p = df_meu.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        fig = px.line(df_p, x='Data', y='total', markers=True)
        fig.update_xaxes(type='category', title="Data") 
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

elif selected == "Novo Registro":
    st.title("📝 Registro")
    if not editais: st.warning("Crie um edital.")
    else:
        conc = st.selectbox("Concurso", list(editais.keys()))
        mat = st.selectbox("Matéria", list(editais[conc]["materias"].keys()))
        with st.form("reg"):
            dt = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass = st.selectbox("Tópico", editais[conc]["materias"][mat] or ["Geral"])
            a = st.number_input("Acertos", 0)
            t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": conc, "materia": mat, "assunto": ass, "acertos": a, "total": t, "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear()
                st.success("Salvo!")

elif selected == "Gestão Editais":
    st.title("📑 Editais")
    t1, t2 = st.tabs(["➕ Novo", "📚 Matérias"])
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral"}).execute()
                st.cache_data.clear()
                st.rerun()
    with t2:
        if editais:
            sel = st.selectbox("Edital", list(editais.keys()))
            st.success(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
            m_n = st.text_input("Nova Matéria")
            if st.button("Adicionar"):
                supabase.table("editais_materias").insert({"concurso": sel, "materia": m_n, "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']}).execute()
                st.cache_data.clear()
                st.rerun()

elif selected == "Ranking Squad":
    st.title("🏆 Ranking")
    res_all = supabase.table("registros_estudos").select("usuario, total").execute()
    df_all = pd.DataFrame(res_all.data)
    if not df_all.empty:
        df_all['total'] = pd.to_numeric(df_all['total'])
        rank = df_all.groupby("usuario")['total'].sum().reset_index().sort_values("total", ascending=False)
        st.plotly_chart(px.bar(rank, x="total", y="usuario", orientation='h'), use_container_width=True)

elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_meu.empty:
        st.dataframe(df_meu[['Data', 'concurso', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

# --- ⚙️ GESTÃO DE SISTEMA (EXCLUSIVO FERNANDO) ---
elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Painel de Controlo de Segurança")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📥 Backup de Dados (Snapshot)")
        st.write("Gera um ficheiro JSON com todos os editais e registos atuais.")
        if st.button("Gerar Snapshot"):
            # Buscar dados
            ed_data = supabase.table("editais_materias").select("*").execute().data
            reg_data = supabase.table("registros_estudos").select("*").execute().data
            
            snapshot = {
                "timestamp": str(datetime.datetime.now()),
                "version": version.VERSION,
                "data": {
                    "editais": ed_data,
                    "registros": reg_data
                }
            }
            
            json_string = json.dumps(snapshot, indent=4)
            st.download_button(
                label="⬇️ Baixar Ficheiro de Segurança",
                data=json_string,
                file_name=f"squad_snapshot_{datetime.date.today()}.json",
                mime="application/json"
            )
            st.info("Guarde este ficheiro num local seguro.")

    with c2:
        st.subheader("🎟️ Convites")
        if st.button("Gerar Token de Convite"):
            tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
            supabase.table("tokens_convite").insert({"codigo": tk}).execute()
            st.code(tk)
            st.success("Envie este código ao novo guerreiro.")

    st.markdown("---")
    st.subheader("📜 Notas da Versão Atual")
    for note in version.CHANGELOG:
        st.write(f"- {note}")
