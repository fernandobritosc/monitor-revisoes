import streamlit as st
import pandas as pd
import datetime
import json
import secrets
import string
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO INICIAL E SEGURANÇA ---
st.set_page_config(page_title="Squad Faca na Caveira", page_icon="💀", layout="wide")

# Versão interna
class version:
    VERSION = "35.0.0-NUCLEAR"
    STATUS = "Delete em Cascata Ativo"

# Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 2. FUNÇÕES DE BANCO DE DADOS ---

@st.cache_data(ttl=0) 
def db_get_estudos(usuario, concurso=None):
    try:
        query = supabase.table("registros_estudos").select("*").eq("usuario", usuario)
        if concurso: query = query.eq("concurso", concurso)
        res = query.execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['dt_ordenacao'] = pd.to_datetime(df['data_estudo'])
            df['Data'] = df['dt_ordenacao'].dt.strftime('%d/%m/%Y')
            df = df.sort_values('dt_ordenacao', ascending=False)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=0)
def db_get_editais(usuario_logado):
    try:
        # Tenta buscar do usuário ou públicos
        res = supabase.table("editais_materias").select("*").or_(f"usuario.eq.{usuario_logado},usuario.is.null").execute()
    except:
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
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        
        materia = row.get('materia')
        if materia: 
            editais[conc]["materias"][materia] = row.get('topicos') or []
            
    return editais

# --- 3. LOGIN ---
res_u_global = supabase.table("perfil_usuarios").select("*").execute()
users_global = {row['nome']: row for row in res_u_global.data}

if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD LOGIN</h1>", unsafe_allow_html=True)
        tab_login, tab_cad = st.tabs(["Entrar", "Novo Cadastro"])
        
        with tab_login:
            with st.form("login_form"):
                u = st.selectbox("Guerreiro", list(users_global.keys()) if users_global else ["Nenhum"])
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ACESSAR", use_container_width=True):
                    if u in users_global and str(p) == str(users_global[u]['pin']):
                        st.session_state.usuario_logado = u
                        st.rerun()
                    else: st.error("PIN Incorreto.")
        
        with tab_cad:
            with st.form("cad_form"):
                tk = st.text_input("Token")
                n_cad = st.text_input("Seu Nome")
                pi = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        try:
                            supabase.table("perfil_usuarios").insert({"nome": n_cad, "pin": pi}).execute()
                            supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                            st.cache_data.clear()
                            st.success("Conta Criada! Vá para a aba 'Entrar'.")
                        except: st.error("Erro: Nome já existe.")
                    else: st.error("Token inválido.")
    st.stop()

# --- 4. ESTADO ---
usuario_atual = st.session_state.usuario_logado
st.cache_data.clear() # Limpeza preventiva a cada reload
editais = db_get_editais(usuario_atual)

if 'concurso_ativo' in st.session_state:
    if st.session_state.concurso_ativo not in editais:
        del st.session_state.concurso_ativo
        st.rerun()

# --- 5. TELA INICIAL ---
if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Olá, {usuario_atual}")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("🎯 Suas Missões")
        if not editais: st.info("Nenhuma missão encontrada.")
        else:
            for conc in editais.keys():
                if st.button(f"🚀 ACESSAR: {conc.upper()}", use_container_width=True):
                    st.session_state.concurso_ativo = conc
                    st.rerun()
                    
    with c2:
        st.subheader("➕ Nova Missão")
        with st.form("new_mission"):
            nm = st.text_input("Nome (Ex: PF)")
            cg = st.text_input("Cargo")
            dt = st.date_input("Data da Prova")
            if st.form_submit_button("CRIAR"):
                supabase.table("editais_materias").insert({
                    "concurso": nm, "cargo": cg, 
                    "data_prova": dt.strftime('%Y-%m-%d'), "materia": "Geral", 
                    "topicos": [], "usuario": usuario_atual
                }).execute()
                st.cache_data.clear()
                st.session_state.concurso_ativo = nm
                st.rerun()
    st.stop()

# --- 6. AMBIENTE ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.success(f"Guerreiro: **{usuario_atual}**")
    st.info(f"Missão: **{concurso_ativo}**")
    if st.button("🔄 Trocar Missão", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
    st.markdown("---")
    
    opcoes = ["Dashboard", "Novo Registro", "Configurar Edital", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": opcoes.append("⚙️ ADMIN (01)")
    selected = option_menu("Menu", options=opcoes, default_index=0)
    
    if st.button("Sair"):
        st.cache_data.clear()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- 7. TELAS ---

if selected == "Dashboard":
    st.title(f"📊 {concurso_ativo}")
    if df_missao.empty: st.info("Sem dados.")
    else:
        c1, c2 = st.columns(2)
        tot = int(df_missao['total'].sum())
        c1.metric("Questões", tot, border=True)
        c2.metric("Precisão", f"{(df_missao['acertos'].sum()/tot*100):.1f}%", border=True)
        st.plotly_chart(px.line(df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index(), x='Data', y='total', markers=True), use_container_width=True)

elif selected == "Novo Registro":
    st.title(f"📝 {concurso_ativo}")
    mats = list(editais[concurso_ativo]["materias"].keys())
    if not mats: st.warning("Cadastre matérias em 'Configurar Edital'.")
    else:
        mat_sel = st.selectbox("Matéria", mats)
        with st.form("reg"):
            d_reg = st.date_input("Data", datetime.date.today())
            ass_sel = st.selectbox("Assunto", editais[concurso_ativo]["materias"].get(mat_sel) or ["Geral"])
            c_a, c_t = st.columns(2)
            qa = c_a.number_input("Acertos", 0); qt = c_t.number_input("Total", 1)
            if st.form_submit_button("SALVAR"):
                supabase.table("registros_estudos").insert({
                    "data_estudo": d_reg.strftime('%Y-%m-%d'), "usuario": usuario_atual,
                    "concurso": concurso_ativo, "materia": mat_sel, "assunto": ass_sel,
                    "acertos": int(qa), "total": int(qt), "taxa": (qa/qt)*100
                }).execute()
                st.cache_data.clear(); st.success("Salvo!")

elif selected == "Configurar Edital":
    st.title("📑 Configuração")
    
    with st.expander("🔴 EXCLUIR ESTA MISSÃO (PERIGO)"):
        if st.button("CONFIRMAR EXCLUSÃO TOTAL"):
            # 1. Apaga registros primeiro (Cascade Manual)
            supabase.table("registros_estudos").delete().eq("concurso", concurso_ativo).eq("usuario", usuario_atual).execute()
            # 2. Apaga o edital
            supabase.table("editais_materias").delete().eq("concurso", concurso_ativo).eq("usuario", usuario_atual).execute()
            st.cache_data.clear()
            del st.session_state.concurso_ativo
            st.rerun()

    st.markdown("---")
    nm = st.text_input("Nova Matéria")
    if st.button("Adicionar"):
        supabase.table("editais_materias").insert({
            "concurso": concurso_ativo, "materia": nm, "topicos": [], "cargo": editais[concurso_ativo]['cargo'],
            "data_prova": editais[concurso_ativo]['data_iso'], "usuario": usuario_atual
        }).execute()
        st.cache_data.clear(); st.rerun()
            
    for mat, topicos in editais[concurso_ativo]["materias"].items():
        with st.expander(f"📚 {mat}"):
            txt = st.text_area("Tópicos (;)", value="; ".join(topicos), key=f"t_{mat}")
            if st.button("Salvar", key=f"b_{mat}"):
                nt = [t.strip() for t in txt.split(";") if t.strip()]
                supabase.table("editais_materias").update({"topicos": nt}).eq("concurso", concurso_ativo).eq("materia", mat).eq("usuario", usuario_atual).execute()
                st.cache_data.clear(); st.rerun()

elif selected == "Histórico":
    st.title("📜 Histórico")
    if not df_missao.empty: st.dataframe(df_missao[['Data', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)

# --- PAINEL ADMIN COM DELETE NUCLEAR ---
elif selected == "⚙️ ADMIN (01)":
    st.title("⚙️ Painel do Comandante")
    st.subheader("1. Limpeza Global (Modo Nuclear)")
    st.info("Esta função apaga PRIMEIRO os históricos de estudo e DEPOIS o edital. Resolve o problema de 'não excluir'.")
    
    res_all = supabase.table("editais_materias").select("concurso, usuario").execute()
    df_all = pd.DataFrame(res_all.data).drop_duplicates()
    
    if not df_all.empty:
        escolha = st.selectbox("Selecione para EXCLUIR:", [""] + [f"{r['concurso']} | Dono: {r['usuario']}" for _, r in df_all.iterrows()])
        
        if escolha and st.button("🗑️ DELETAR MISSÃO SELECIONADA"):
            partes = escolha.split(" | Dono: ")
            nome_c = partes[0]
            dono_c = partes[1]
            
            # PASSO 1: Apagar filhos (Registros de Estudo)
            st.write(f"A limpar registros de estudo de {dono_c}...")
            supabase.table("registros_estudos").delete().eq("concurso", nome_c).eq("usuario", dono_c).execute()
            
            # PASSO 2: Apagar pai (Edital)
            st.write(f"A apagar edital {nome_c}...")
            supabase.table("editais_materias").delete().eq("concurso", nome_c).eq("usuario", dono_c).execute()
            
            st.cache_data.clear()
            st.success(f"Missão '{nome_c}' foi exterminada com sucesso!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("2. Gestão de Guerreiros")
    df_users = pd.DataFrame(list(users_global.values()))
    if not df_users.empty:
        st.dataframe(df_users, use_container_width=True)
        u_del = st.selectbox("Remover Usuário:", [""] + list(users_global.keys()))
        if u_del and st.button("EXCLUIR USUÁRIO"):
            # Apaga registros do usuário também para não deixar lixo
            supabase.table("registros_estudos").delete().eq("usuario", u_del).execute()
            supabase.table("editais_materias").delete().eq("usuario", u_del).execute()
            supabase.table("perfil_usuarios").delete().eq("nome", u_del).execute()
            st.cache_data.clear(); st.success("Usuário removido."); st.rerun()
            
    st.markdown("---")
    if st.button("Gerar Token"):
        tk = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        supabase.table("tokens_convite").insert({"codigo": tk}).execute()
        st.code(tk)
