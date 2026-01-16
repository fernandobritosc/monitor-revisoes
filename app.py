import streamlit as st
import pandas as pd  # <--- CORRIGIDO: O ERRO DE IMPORTAÇÃO ESTAVA AQUI
import datetime
import json
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import secrets
import string
import plotly.express as px

# 1. Configurações de Página
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# 2. Segurança
try:
    import version
except ImportError:
    class version:
        VERSION = "34.0.0-ANTICRASH"
        STATUS = "Válvula de Segurança Ativa"

# 3. Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- FUNÇÕES DE DADOS (COM LIMPEZA DE CACHE) ---

@st.cache_data(ttl=1) # TTL BAIXO PARA FORÇAR ATUALIZAÇÃO RÁPIDA
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

@st.cache_data(ttl=1) # TTL BAIXO PARA ATUALIZAR EXCLUSÕES NA HORA
def db_get_editais(usuario_logado):
    try:
        # Tenta buscar do usuário ou públicos
        res = supabase.table("editais_materias").select("*").or_(f"usuario.eq.{usuario_logado},usuario.is.null").execute()
    except:
        # Se der erro de coluna, busca tudo (fallback)
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
res_u_global = supabase.table("perfil_usuarios").select("*").execute()
users_global = {row['nome']: row for row in res_u_global.data}

if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["Acessar", "Novo Guerreiro"])
        with t_log:
            with st.form("login"):
                u = st.selectbox("Guerreiro", list(users_global.keys()) if users_global else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTRAR", use_container_width=True):
                    if u in users_global and p == users_global[u]['pin']:
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("PIN Errado.")
        with t_cad:
            with st.form("cad"):
                tk = st.text_input("Token")
                n_cad = st.text_input("Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        try:
                            supabase.table("perfil_usuarios").insert({"nome": n_cad, "pin": pi}).execute()
                            supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                            st.cache_data.clear()
                            st.success("Criado! Vá em Acessar.")
                        except: st.error("Erro: Nome já existe.")
                    else: st.error("Token Inválido.")
    st.stop()

usuario_atual = st.session_state.usuario_logado
# CARREGA OS EDITAIS ATUALIZADOS
st.cache_data.clear() # FORÇA LIMPEZA NO INICIO
editais = db_get_editais(usuario_atual)

# --- VÁLVULA DE SEGURANÇA (AQUI ESTÁ A CORREÇÃO DO ERRO) ---
# Se o concurso ativo na memória não existir mais na lista de editais, reseta tudo.
if 'concurso_ativo' in st.session_state:
    if st.session_state.concurso_ativo not in editais:
        del st.session_state.concurso_ativo
        st.rerun()

# --- CENTRAL DE MISSÕES ---
if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Missão: {usuario_atual}")
    c_sel, c_nov = st.columns([1.5, 1])
    with c_sel:
        st.subheader("🎯 Selecionar Missão")
        if not editais: st.info("Sem editais.")
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
            dt = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("CRIAR E INICIAR", use_container_width=True):
                # BLINDAGEM DE INSERÇÃO
                supabase.table("editais_materias").insert({
                    "concurso": nm, "cargo": cg, "data_prova": dt.strftime('%Y-%m-%d'), 
                    "materia": "Geral", "topicos": [], "usuario": usuario_atual
                }).execute()
                st.cache_data.clear()
                st.session_state.concurso_ativo = nm
                st.rerun()
    st.stop()

# --- MISSÃO ATIVA ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    st.success(f"🎯 Missão: {concurso_ativo}")
    if st.button("🔄 Trocar de Missão"):
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
        st.plotly_chart(px.line(df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index(), x='Data', y='total', markers=True), use_container_width=True)

elif selected == "Novo Registro":
    st.title("📝 Registro")
    mats = list(editais[concurso_ativo]["materias"].keys())
    mat = st.selectbox("Matéria", mats)
    with st.form("r"):
        d = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
        asnt = st.selectbox("Assunto", editais[concurso_ativo]["materias"].get(mat) or ["Geral"])
        ac = st.number_input("Acertos", 0); tt = st.number_input("Total", 1)
        if st.form_submit_button("SALVAR"):
            supabase.table("registros_estudos").insert({"data_estudo": d.strftime('%Y-%m-%d'), "usuario": usuario_atual, "concurso": concurso_ativo, "materia": mat, "assunto": asnt, "acertos": int(ac), "total": int(tt), "taxa": (ac/tt*100)}).execute()
            st.cache_data.clear(); st.success("Salvo!")

elif selected == "Gestão do Edital":
    st.title("📑 Ajustar Missão")
    
    with st.expander("⚠️ EXCLUIR ESTE CONCURSO"):
        st.warning("Tem certeza? Isso apaga o edital e as matérias.")
        if st.button("CONFIRMAR EXCLUSÃO"):
            # DELETAR COM LOG DE ERRO PARA DEBUG
            try:
                supabase.table("editais_materias").delete().eq("concurso", concurso_ativo).eq("usuario", usuario_atual).execute()
                st.cache_data.clear() # Limpa memória
                del st.session_state.concurso_ativo # Limpa estado
                st.rerun() # Reinicia
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

    st.markdown("---")
    m_n = st.text_input("Nova Matéria")
    if st.button("Adicionar"):
        supabase.table("editais_materias").insert({"concurso": concurso_ativo, "materia": m_n, "topicos": [], "cargo": editais[concurso_ativo]['cargo'], "data_prova": editais[concurso_ativo]['data_iso'], "usuario": usuario_atual}).execute()
        st.cache_data.clear(); st.rerun()
    
    for m, t in editais[concurso_ativo]["materias"].items():
        with st.expander(f"📚 {m}"):
            tx = st.text_area("Tópicos (;)", value="; ".join(t), key=f"t_{m}")
            if st.button("Salvar Assuntos", key=f"b_{m}"):
                novos = [x.strip() for x in tx.split(";") if x.strip()]
                supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", concurso_ativo).eq("materia", m).eq("usuario", usuario_atual).execute()
                st.cache_data.clear(); st.rerun()

elif selected == "⚙️ Gestão de Sistema":
    st.title("⚙️ Painel Admin")
    st.subheader("🧹 Limpeza Global")
    res_gl = supabase.table("editais_materias").select("concurso, usuario").execute()
    df_gl = pd.DataFrame(res_gl.data).drop_duplicates()
    if not df_gl.empty:
        alvo = st.selectbox("ELIMINAR DE QUALQUER UM:", [f"{r['concurso']} ({r['usuario']})" for _, r in df_gl.iterrows()])
        if st.button("ELIMINAR AGORA"):
            c_alvo = alvo.split(" (")[0]
            u_alvo = alvo.split(" (")[1].replace(")", "")
            supabase.table("editais_materias").delete().eq("concurso", c_alvo).eq("usuario", u_alvo).execute()
            st.cache_data.clear()
            st.success("Eliminado!"); st.rerun()
