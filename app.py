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

# Versão interna para controle
class version:
    VERSION = "FINAL-STABLE"
    STATUS = "Produção"

# Conexão Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 2. FUNÇÕES DE BANCO DE DADOS (BLINDADAS) ---

@st.cache_data(ttl=0) # TTL=0 para nunca segurar cache velho de exclusão
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
    except Exception as e:
        st.error(f"Erro ao buscar estudos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=0) # TTL=0 garante que se você excluir, some na hora
def db_get_editais(usuario_logado):
    try:
        # Tenta buscar com filtro de usuário OU públicos (null)
        res = supabase.table("editais_materias").select("*").or_(f"usuario.eq.{usuario_logado},usuario.is.null").execute()
    except Exception:
        # Se der erro (ex: coluna usuario não existe), busca tudo
        res = supabase.table("editais_materias").select("*").execute()
        
    editais = {}
    for row in res.data:
        conc = row.get('concurso')
        if not conc: continue
        
        # Garante estrutura do dicionário
        if conc not in editais:
            dt_raw = row.get('data_prova')
            dt_br = datetime.datetime.strptime(dt_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if dt_raw else "A definir"
            editais[conc] = {
                "cargo": row.get('cargo') or "Não informado", 
                "data_br": dt_br, 
                "data_iso": dt_raw, 
                "materias": {}
            }
        
        # Preenche matérias
        materia = row.get('materia')
        if materia: 
            editais[conc]["materias"][materia] = row.get('topicos') or []
            
    return editais

# --- 3. SISTEMA DE LOGIN ---
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
                    else:
                        st.error("PIN Incorreto.")
        
        with tab_cad:
            with st.form("cad_form"):
                tk = st.text_input("Token de Convite")
                n_cad = st.text_input("Seu Nome")
                pi = st.text_input("Crie um PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("CRIAR CONTA"):
                    # Verifica token
                    res_tk = supabase.table("tokens_convite").select("*").eq("codigo", tk).eq("usado", False).execute()
                    if res_tk.data:
                        try:
                            # Tenta criar usuário
                            supabase.table("perfil_usuarios").insert({"nome": n_cad, "pin": pi}).execute()
                            # Queima o token
                            supabase.table("tokens_convite").update({"usado": True}).eq("codigo", tk).execute()
                            st.cache_data.clear()
                            st.success("Conta Criada! Vá para a aba 'Entrar'.")
                        except Exception as e:
                            st.error(f"Erro: {e}. Tente outro nome.")
                    else:
                        st.error("Token inválido ou já usado.")
    st.stop()

# --- 4. LÓGICA DE NAVEGAÇÃO E ESTADO ---
usuario_atual = st.session_state.usuario_logado
st.cache_data.clear() # Limpeza preventiva
editais = db_get_editais(usuario_atual)

# Válvula de Segurança: Se o concurso ativo foi excluído, reseta.
if 'concurso_ativo' in st.session_state:
    if st.session_state.concurso_ativo not in editais:
        del st.session_state.concurso_ativo
        st.rerun()

# --- 5. TELA INICIAL (SELEÇÃO DE MISSÃO) ---
if 'concurso_ativo' not in st.session_state:
    st.markdown(f"## 🥷 Olá, {usuario_atual}")
    st.markdown("---")
    
    col_sel, col_add = st.columns([1.5, 1])
    
    with col_sel:
        st.subheader("🎯 Suas Missões")
        if not editais:
            st.info("Nenhuma missão encontrada.")
        else:
            for conc in editais.keys():
                if st.button(f"🚀 ACESSAR: {conc.upper()}", use_container_width=True):
                    st.session_state.concurso_ativo = conc
                    st.rerun()
                    
    with col_add:
        st.subheader("➕ Nova Missão")
        with st.form("new_mission"):
            nm = st.text_input("Nome (Ex: PF, PRF)")
            cg = st.text_input("Cargo")
            dt = st.date_input("Data da Prova")
            if st.form_submit_button("CRIAR"):
                try:
                    supabase.table("editais_materias").insert({
                        "concurso": nm, "cargo": cg, 
                        "data_prova": dt.strftime('%Y-%m-%d'), 
                        "materia": "Geral", "topicos": [], 
                        "usuario": usuario_atual
                    }).execute()
                    st.cache_data.clear()
                    st.session_state.concurso_ativo = nm
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar: {e}")
    st.stop()

# --- 6. AMBIENTE DA MISSÃO (SIDEBAR E MENU) ---
concurso_ativo = st.session_state.concurso_ativo
df_missao = db_get_estudos(usuario_atual, concurso_ativo)

with st.sidebar:
    st.success(f"Logado: **{usuario_atual}**")
    st.info(f"Missão: **{concurso_ativo}**")
    
    if st.button("🔄 Trocar Missão", use_container_width=True):
        del st.session_state.concurso_ativo
        st.rerun()
        
    st.markdown("---")
    
    opcoes_menu = ["Dashboard", "Novo Registro", "Configurar Edital", "Histórico"]
    if usuario_atual == "Fernando Pinheiro": # Só Admin vê isso
        opcoes_menu.append("⚙️ ADMIN (01)")
        
    selected = option_menu("Menu Tático", options=opcoes_menu, default_index=0)
    
    st.markdown("---")
    if st.button("Sair do Sistema"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 7. TELAS DO SISTEMA ---

# A. DASHBOARD
if selected == "Dashboard":
    st.title(f"📊 Relatório: {concurso_ativo}")
    if df_missao.empty:
        st.info("Sem dados registrados nesta missão.")
    else:
        c1, c2 = st.columns(2)
        total_q = int(df_missao['total'].sum())
        acertos_q = int(df_missao['acertos'].sum())
        precisao = (acertos_q / total_q * 100) if total_q > 0 else 0
        
        c1.metric("Total Questões", total_q, border=True)
        c2.metric("Precisão Global", f"{precisao:.1f}%", border=True)
        
        # Gráfico
        df_chart = df_missao.sort_values('dt_ordenacao').groupby('Data')['total'].sum().reset_index()
        fig = px.line(df_chart, x='Data', y='total', markers=True, title="Evolução Diária")
        st.plotly_chart(fig, use_container_width=True)

# B. NOVO REGISTRO
elif selected == "Novo Registro":
    st.title(f"📝 Registrar: {concurso_ativo}")
    
    mats = list(editais[concurso_ativo]["materias"].keys())
    
    if not mats:
        st.warning("Cadastre matérias em 'Configurar Edital' primeiro.")
    else:
        mat_sel = st.selectbox("Matéria", mats)
        with st.form("registro_form"):
            d_reg = st.date_input("Data", datetime.date.today())
            
            # Assuntos
            lista_assuntos = editais[concurso_ativo]["materias"].get(mat_sel) or ["Geral"]
            ass_sel = st.selectbox("Assunto", lista_assuntos)
            
            col_a, col_t = st.columns(2)
            qtd_a = col_a.number_input("Acertos", min_value=0, step=1)
            qtd_t = col_t.number_input("Total Feito", min_value=1, step=1)
            
            if st.form_submit_button("SALVAR REGISTRO"):
                perc = (qtd_a / qtd_t) * 100
                supabase.table("registros_estudos").insert({
                    "data_estudo": d_reg.strftime('%Y-%m-%d'),
                    "usuario": usuario_atual,
                    "concurso": concurso_ativo,
                    "materia": mat_sel,
                    "assunto": ass_sel,
                    "acertos": int(qtd_a),
                    "total": int(qtd_t),
                    "taxa": perc
                }).execute()
                st.cache_data.clear()
                st.toast("Registro Salvo!")

# C. CONFIGURAR EDITAL (Adicionar/Remover Matérias e EXCLUIR CONCURSO)
elif selected == "Configurar Edital":
    st.title("📑 Configuração da Missão")
    
    # --- ÁREA DE PERIGO (EXCLUSÃO) ---
    with st.expander("🔴 EXCLUIR ESTA MISSÃO (PERIGO)", expanded=False):
        st.error(f"Você está prestes a apagar o concurso '{concurso_ativo}' e todas as suas matérias.")
        if st.button("CONFIRMAR EXCLUSÃO DEFINITIVA"):
            try:
                # Apaga do banco
                supabase.table("editais_materias").delete().eq("concurso", concurso_ativo).eq("usuario", usuario_atual).execute()
                # Limpa TUDO
                st.cache_data.clear()
                del st.session_state.concurso_ativo
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

    st.markdown("---")
    st.subheader("Adicionar Matéria")
    nova_mat = st.text_input("Nome da Matéria")
    if st.button("Adicionar"):
        if nova_mat:
            supabase.table("editais_materias").insert({
                "concurso": concurso_ativo,
                "materia": nova_mat,
                "topicos": [],
                "cargo": editais[concurso_ativo]['cargo'],
                "data_prova": editais[concurso_ativo]['data_iso'],
                "usuario": usuario_atual
            }).execute()
            st.cache_data.clear()
            st.rerun()
            
    st.subheader("Editar Tópicos")
    for mat, topicos in editais[concurso_ativo]["materias"].items():
        with st.expander(f"📚 {mat}"):
            txt_topicos = st.text_area("Tópicos (separe por ;)", value="; ".join(topicos), key=f"txt_{mat}")
            if st.button("Salvar Tópicos", key=f"btn_{mat}"):
                novos_topicos = [t.strip() for t in txt_topicos.split(";") if t.strip()]
                supabase.table("editais_materias").update({"topicos": novos_topicos}).eq("concurso", concurso_ativo).eq("materia", mat).eq("usuario", usuario_atual).execute()
                st.cache_data.clear()
                st.rerun()

# D. HISTÓRICO
elif selected == "Histórico":
    st.title("📜 Histórico de Registros")
    if not df_missao.empty:
        st.dataframe(df_missao[['Data', 'materia', 'assunto', 'acertos', 'total']], use_container_width=True, hide_index=True)
        
        reg_id = st.text_input("Para apagar, digite o ID (se tiver implementado ID visível)")
        # Nota: Simplificado para visualização apenas nesta versão estável

# E. ADMIN (Só Fernando vê)
elif selected == "⚙️ ADMIN (01)":
    st.title("⚙️ Painel do Comandante")
    
    st.subheader("1. Limpeza Global de Missões")
    # Busca todos os editais de todos os usuários
    res_all = supabase.table("editais_materias").select("concurso, usuario").execute()
    df_all = pd.DataFrame(res_all.data).drop_duplicates()
    
    if not df_all.empty:
        # Cria lista legível: "Concurso X (Dono: Y)"
        lista_opcoes = [f"{row['concurso']} | Dono: {row['usuario']}" for index, row in df_all.iterrows()]
        escolha = st.selectbox("Selecione para EXCLUIR:", [""] + lista_opcoes)
        
        if escolha and st.button("🗑️ DELETAR MISSÃO SELECIONADA"):
            # Extrai nome e dono
            partes = escolha.split(" | Dono: ")
            nome_c = partes[0]
            dono_c = partes[1]
            
            supabase.table("editais_materias").delete().eq("concurso", nome_c).eq("usuario", dono_c).execute()
            st.cache_data.clear()
            st.success(f"Missão '{nome_c}' do usuário '{dono_c}' foi eliminada!")
            st.rerun()
            
    st.markdown("---")
    st.subheader("2. Gestão de Guerreiros (Usuários)")
    df_users = pd.DataFrame(list(users_global.values()))
    if not df_users.empty:
        st.dataframe(df_users, use_container_width=True)
        
        user_del = st.selectbox("Remover Usuário:", [""] + list(users_global.keys()))
        if user_del and st.button("EXCLUIR USUÁRIO"):
            supabase.table("perfil_usuarios").delete().eq("nome", user_del).execute()
            st.cache_data.clear()
            st.success("Usuário removido.")
            st.rerun()
            
    st.markdown("---")
    st.subheader("3. Gerar Convite")
    if st.button("Gerar Novo Token"):
        token_novo = "SK-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        supabase.table("tokens_convite").insert({"codigo": token_novo}).execute()
        st.code(token_novo, language="text")
