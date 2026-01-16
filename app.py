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

# 2. Segurança: Proteção contra ausência do arquivo version.py
try:
    import version
except ImportError:
    class version:
        VERSION = "23.0.0-FIX"
        STATUS = "Blindagem de Reconhecimento"

# 3. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS (COM LIMPEZA DE CACHE FORÇADA) ---

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

@st.cache_data(ttl=600) # Aumentamos o TTL, mas limpamos manualmente no INSERT
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

# --- LOGIN ---
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
                    else: st.error("PIN Incorreto.")
        with t_cad:
            with st.form("cad"):
                tk = st.text_input("Token de Convite")
                n_cad = st.text_input("Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        try:
                            supabase.table("perfil_usuarios").insert({"nome": n_cad, "pin": pi}).execute()
                            supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                            st.success("Guerreiro Cadastrado!")
                        except: st.error("Erro no cadastro.")
                    else: st.error("Token Inválido.")
    st.stop()

# --- CENTRAL DE MISSÕES (SÓ APARECE SE NÃO HOUVER CONCURSO ATIVO) ---
usuario_atual = st.session_state.usuario_logado
editais = db_get_editais()

if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Guerreiro {usuario_atual}, para qual missão vamos hoje?")
    
    col_sel, col_novo = st.columns([1.5, 1])
    
    with col_sel:
        st.subheader("🎯 Suas Missões")
        if not editais: st.info("Nenhuma missão criada ainda.")
        else:
            for conc in editais.keys():
                if st.button(f"🚀 ENTRAR: {conc.upper()}", use_container_width=True, key=f"btn_{conc}"):
                    st.session_state.concurso_ativo = conc
                    st.rerun()
                    
    with col_novo:
        st.subheader("➕ Nova Missão")
        with st.form("form_novo_edital"):
            nome_edital = st.text_input("Nome do Concurso (Ex: PF, PC, Senado)")
            cargo_edital = st.text_input("Cargo")
            data_edital = st.date_input("Data da Prova", format="DD/MM/YYYY")
            if st.form_submit_button("CRIAR E INICIAR", use_container_width=True):
                if not nome_edital:
                    st.error("Digite o NOME do concurso para que ele seja reconhecido!")
                else:
                    try:
                        # Grava no banco com blindagem de campos obrigatórios
                        supabase.table("editais_materias").insert({
                            "concurso": nome_edital, "cargo": cargo_edital, 
                            "data_prova": data_edital.strftime('%Y-%m-%d'), 
                            "materia": "Geral", "topicos": [] 
                        }).execute()
                        
                        # LIMPA O CACHE PARA O NOME APARECER NO RECONHECIMENTO
                        st.cache_data.clear()
                        st.session_state.concurso_ativo = nome_edital
                        st.success(f"Missão {nome_edital} criada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar missão: {str(e)}")
    st.stop()

# --- AMBIENTE OPERACIONAL (MISSÃO SELECIONADA) ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 **Missão Ativa:**\n{concurso_ativo}")
    if st.button("🔄 Trocar de Missão", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
    
    st.markdown("---")
    menus = ["Dashboard", "Novo Registro", "Gestão do Edital", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": menus.append("⚙️ Gestão de Sistema")
    
    selected = option_menu("Menu Tático", menus, icons=["bar-chart", "plus-circle", "book-half", "table", "gear"], default_index=0)
    
    if st.button("🚪 Sair"):
        del st.session_state.usuario_logado
        if 'concurso_ativo' in st.session_state: del st.session_state.concurso_ativo
        st.rerun()

# --- TELAS (FILTRADAS PELO CONCURSO_ATIVO) ---

if selected == "Dashboard":
    st.title(f"📊 Desempenho: {concurso_ativo}")
    if not df_missao.empty:
        c1, c2 = st.columns(2)
        tot = int(df_missao['total'].sum())
        c1.metric("Questões na Missão", tot, border=True)
        c2.metric("Precisão Geral", f"{(df_missao['acertos'].sum()/tot*100):.1f}%", border=True)
        df_p = df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        st.plotly_chart(px.line(df_p, x='Data', y='total', markers=True), use_container_width=True)
    else: st.info(f"Nenhum registro para {concurso_ativo}.")

elif selected == "Novo Registro":
    st.title(f"📝 Registro: {concurso_ativo}")
    # Verifica se o edital existe no dicionário para carregar as matérias
    if concurso_ativo in editais:
        materias = list(editais[concurso_ativo]["materias"].keys())
        mat = st.selectbox("Selecione a Matéria", materias)
        with st.form("reg_estudo"):
            dt = st.date_input("Data do Estudo", datetime.date.today(), format="DD/MM/YYYY")
            ass_lista = editais[concurso_ativo]["materias"].get(mat) or ["Geral"]
            ass = st.selectbox("Assunto", ass_lista)
            a = st.number_input("Acertos", 0); t = st.number_input("Total", 1)
            if st.form_submit_button("SALVAR REGISTRO"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": dt.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": concurso_ativo, "materia": mat, "assunto": ass, 
                    "acertos": int(a), "total": int(t), "taxa": (a/t*100)
                }).execute()
                st.cache_data.clear(); st.success("Salvo!")
    else: st.error("Erro ao carregar matérias. Tente 'Sincronizar Tudo'.")

elif selected == "Gestão do Edital":
    st.title(f"📑 Ajustar Missão: {concurso_ativo}")
    # Permite adicionar matérias apenas para o concurso que está aberto
    st.subheader("Adicionar Matéria ao Edital")
    m_n = st.text_input("Nome da Matéria")
    if st.button("Confirmar Adição"):
        if m_n:
            supabase.table("editais_materias").insert({
                "concurso": concurso_ativo, "materia": m_n, "topicos": [], 
                "cargo": editais[concurso_ativo]['cargo'], "data_prova": editais[concurso_ativo]['data_iso']
            }).execute()
            st.cache_data.clear(); st.rerun()
        else: st.warning("Digite um nome!")

    st.markdown("---")
    # Edição de tópicos das matérias existentes
    for m, t in editais[concurso_ativo]["materias"].items():
        with st.expander(f"📚 {m}"):
            txt = st.text_area("Tópicos (separe por ;)", value="; ".join(t), key=f"t_{m}")
            if st.button("Salvar Assuntos", key=f"bt_{m}"):
                novos = [x.strip() for x in txt.split(";") if x.strip()]
                supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", concurso_ativo).eq("materia", m).execute()
                st.cache_data.clear(); st.rerun()
            if st.checkbox(f"Excluir {m}", key=f"c_{m}"):
                if st.button(f"🗑️ Deletar {m}", key=f"d_{m}"):
                    supabase.table("editais_materias").delete().eq("concurso", concurso_ativo).eq("materia", m).execute()
                    st.cache_data.clear(); st.rerun()

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Sistema")
    if st.button("📥 Gerar Backup JSON"):
        ed = supabase.table("editais_materias").select("*").execute().data
        re = supabase.table("registros_estudos").select("*").execute().data
        st.download_button("Baixar Backup", json.dumps({"editais": ed, "registros": re}), "squad_backup.json")
