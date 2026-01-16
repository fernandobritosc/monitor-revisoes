import streamlit as st
import pandas as pd
import datetime
import os
import json
import secrets
import string
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad Elite", page_icon="💀", layout="wide")

# --- ARQUIVOS DE BANCO DE DADOS ---
DB_FILE = "estudos_data.csv"
EDITAIS_FILE = "editais_db.json"
USERS_FILE = "users_db.json"
TOKENS_FILE = "tokens_db.json" # <--- NOVO ARQUIVO DE TOKENS

# --- FUNÇÕES DE PERSISTÊNCIA ---
def carregar_json(caminho):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                content = f.read()
                return json.loads(content) if content else {}
        except: return {}
    return {}

def salvar_json(caminho, dado):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dado, f, indent=4, ensure_ascii=False)

def carregar_dados():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE, sep=';', dtype=str)
        except: return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

# --- FUNÇÃO PARA GERAR TOKENS ÚNICOS ---
def gerar_novo_token():
    # Gera um código aleatório tipo SK-XXXX
    chars = string.ascii_uppercase + string.digits
    codigo = "SK-" + ''.join(secrets.choice(chars) for _ in range(4))
    tokens = carregar_json(TOKENS_FILE)
    if "ativos" not in tokens: tokens["ativos"] = []
    tokens["ativos"].append(codigo)
    salvar_json(TOKENS_FILE, tokens)
    return codigo

# --- SISTEMA DE LOGIN E CADASTRO ---
users_db = carregar_json(USERS_FILE)
tokens_db = carregar_json(TOKENS_FILE)

if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        
        tab_login, tab_cadastro, tab_reset = st.tabs(["Acessar Base", "Novo Guerreiro", "Recuperar PIN"])
        
        with tab_login:
            if not users_db:
                st.info("Nenhum usuário. Use o botão abaixo para gerar um token inicial.")
                if st.button("Gerar Token de Primeiro Acesso"):
                    tk = gerar_novo_token()
                    st.success(f"Token Gerado: {tk}")
            else:
                with st.form("login_form"):
                    u_login = st.selectbox("Quem está acessando?", list(users_db.keys()))
                    p_login = st.text_input("PIN de Acesso", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p_login == users_db[u_login]['pin']:
                            st.session_state.usuario_logado = u_login
                            st.rerun()
                        else: st.error("PIN incorreto.")

        with tab_cadastro:
            with st.form("cadastro_form"):
                st.caption("Insira um Token Válido (Uso Único)")
                t_token = st.text_input("Token de Convite")
                n_user = st.text_input("Nome do Guerreiro")
                n_pin = st.text_input("Criar PIN (4 dígitos)", type="password", max_chars=4)
                n_recupera = st.text_input("Palavra-Chave / CPF")
                
                if st.form_submit_button("CRIAR CONTA"):
                    tokens_ativos = tokens_db.get("ativos", [])
                    
                    if t_token not in tokens_ativos: 
                        st.error("Token inválido ou já utilizado.")
                    elif n_user in users_db: 
                        st.error("Usuário já existe.")
                    elif len(n_pin) < 4: 
                        st.error("O PIN deve ter 4 dígitos.")
                    elif not n_user or not n_recupera: 
                        st.error("Preencha todos os campos.")
                    else:
                        # 1. Cria o usuário
                        users_db[n_user] = {"pin": n_pin, "chave": n_recupera}
                        salvar_json(USERS_FILE, users_db)
                        
                        # 2. MATA O TOKEN (Remove da lista de ativos)
                        tokens_ativos.remove(t_token)
                        tokens_db["ativos"] = tokens_ativos
                        salvar_json(TOKENS_FILE, tokens_db)
                        
                        st.success("Conta criada! O Token foi invalidado.")

        with tab_reset:
            with st.form("reset_form"):
                r_user = st.selectbox("Resetar senha de:", list(users_db.keys())) if users_db else st.selectbox("Nenhum usuário", ["-"])
                r_chave = st.text_input("Sua Palavra-Chave")
                r_novo_pin = st.text_input("Novo PIN", type="password", max_chars=4)
                if st.form_submit_button("REDEFINIR PIN"):
                    if r_user in users_db and r_chave == users_db[r_user]['chave']:
                        users_db[r_user]['pin'] = r_novo_pin
                        salvar_json(USERS_FILE, users_db)
                        st.success("PIN alterado!")
                    else: st.error("Dados incorretos.")
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
df_global = carregar_dados()
editais = carregar_json(EDITAIS_FILE)

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    selected = option_menu(
        "Menu Tático", 
        ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico", "Gerar Convites"],
        icons=["bar-chart", "plus-circle", "trophy", "book-half", "table", "ticket-perforated"],
        default_index=0
    )

# --- PÁGINA DE GERAR CONVITES (SÓ VOCÊ USA) ---
if selected == "Gerar Convites":
    st.title("🎟️ Gerador de Convites Únicos")
    st.markdown("Cada token gerado abaixo só pode ser usado **uma vez**.")
    
    if st.button("Gerar Novo Token de Convite"):
        novo_tk = gerar_novo_token()
        st.code(novo_tk, language="text")
        st.success("Envie este código para o seu amigo.")
    
    st.markdown("---")
    st.subheader("Tokens Ativos no Sistema")
    t_db = carregar_json(TOKENS_FILE)
    ativos = t_db.get("ativos", [])
    if ativos:
        for a in ativos:
            st.text(f"• {a}")
    else:
        st.info("Nenhum token pendente.")

# (Restante das páginas: Dashboard, Registro, etc permanecem iguais ao seu código anterior)
# ... [Omitido por brevidade, mas deve manter a lógica de Usuario=usuario_atual]
