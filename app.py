import streamlit as st
import pandas as pd
import datetime
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# Configuração da página
st.set_page_config(page_title="Faca na Caveira - Squad", page_icon="💀", layout="wide")

# --- ARQUIVOS DE BANCO DE DADOS ---
DB_FILE = "estudos_data.csv"
EDITAIS_FILE = "editais_db.json"
USERS_FILE = "users_db.json"
TOKEN_CONVITE = "CAVEIRA2026" # <--- TOKEN QUE TU VAIS DAR AOS TEUS AMIGOS

# --- FUNÇÕES DE PERSISTÊNCIA ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE, sep=';', dtype=str)
        except: return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def carregar_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def salvar_json(caminho, dado):
    with open(caminho, "w", encoding="utf-8") as f: json.dump(dado, f, indent=4, ensure_ascii=False)

# --- SISTEMA DE LOGIN E CADASTRO ---
users_db = carregar_json(USERS_FILE)

if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>💀 SQUAD PRIVADO</h1>", unsafe_allow_html=True)
        
        tab_login, tab_cadastro, tab_reset = st.tabs(["Acessar Base", "Novo Guerreiro", "Recuperar PIN"])
        
        # ABA: LOGIN
        with tab_login:
            if not users_db:
                st.info("Nenhum usuário cadastrado. Vá em 'Novo Guerreiro'.")
            else:
                with st.form("login_form"):
                    u_login = st.selectbox("Quem está acessando?", list(users_db.keys()))
                    p_login = st.text_input("PIN de Acesso", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        if p_login == users_db[u_login]['pin']:
                            st.session_state.usuario_logado = u_login
                            st.rerun()
                        else: st.error("PIN incorreto.")

        # ABA: CADASTRO COM TOKEN
        with tab_cadastro:
            with st.form("cadastro_form"):
                st.caption("Apenas para membros autorizados")
                t_token = st.text_input("Token de Convite")
                n_user = st.text_input("Nome do Guerreiro")
                n_pin = st.text_input("Criar PIN (4 dígitos)", type="password", max_chars=4)
                n_recupera = st.text_input("Palavra-Chave / CPF (Para recuperar senha)")
                
                if st.form_submit_button("CRIAR CONTA"):
                    if t_token != TOKEN_CONVITE: st.error("Token de Convite inválido.")
                    elif n_user in users_db: st.error("Usuário já existe.")
                    elif len(n_pin) < 4: st.error("O PIN deve ter 4 dígitos.")
                    elif not n_user or not n_recupera: st.error("Preencha todos os campos.")
                    else:
                        users_db[n_user] = {"pin": n_pin, "chave": n_recupera}
                        salvar_json(USERS_FILE, users_db)
                        st.success("Conta criada! Já pode fazer login.")

        # ABA: RESET DE SENHA
        with tab_reset:
            with st.form("reset_form"):
                r_user = st.selectbox("Resetar senha de:", list(users_db.keys()))
                r_chave = st.text_input("Sua Palavra-Chave / CPF cadastrado")
                r_novo_pin = st.text_input("Novo PIN (4 dígitos)", type="password", max_chars=4)
                
                if st.form_submit_button("REDEFINIR PIN"):
                    if r_user in users_db and r_chave == users_db[r_user]['chave']:
                        users_db[r_user]['pin'] = r_novo_pin
                        salvar_json(USERS_FILE, users_db)
                        st.success("PIN alterado com sucesso!")
                    else: st.error("Dados de validação incorretos.")
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
df_global = carregar_dados()
editais = carregar_json(EDITAIS_FILE)

# Garantir colunas novas no CSV
if "Usuario" not in df_global.columns:
    df_global["Usuario"] = usuario_atual
    salvar_dados(df_global)

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR DO SISTEMA"):
        del st.session_state.usuario_logado
        st.rerun()
    
    st.markdown("---")
    selected = option_menu(
        "Menu Tático", 
        ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"],
        icons=["bar-chart", "plus-circle", "trophy", "book-half", "table"],
        default_index=0
    )

# === LÓGICA DE CÁLCULO DE STREAK (GLOBAL) ===
def get_streak_metrics(df):
    if df.empty: return 0, 0
    try:
        dates = pd.to_datetime(df['Data_Estudo'], dayfirst=True, errors='coerce').dt.normalize().dropna().unique()
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

# === PÁGINAS ===
df_meu = df_global[df_global['Usuario'] == usuario_atual].copy()

if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
        # Cálculos Pessoais
        df_meu['Acertos'] = pd.to_numeric(df_meu['Acertos'], errors='coerce').fillna(0)
        df_meu['Total'] = pd.to_numeric(df_meu['Total'], errors='coerce').fillna(1)
        t_q = df_meu['Total'].sum()
        acc = (df_meu['Acertos'].sum() / t_q * 100) if t_q > 0 else 0
        sa, mx = get_streak_metrics(df_meu)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", int(t_q), border=True)
        c2.metric("Precisão", f"{acc:.1f}%", border=True)
        c3.metric("🔥 Streak", f"{sa}d", border=True)
        c4.metric("🏆 Recorde", f"{mx}d", border=True)
        
        # Radar
        st.markdown("---")
        df_r = df_meu.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="N")
        fig = go.Figure(data=go.Scatterpolar(r=df_r['N'], theta=df_r['Materia'], fill='toself', line_color='#00E676'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado registrado.")

elif selected == "Novo Registro":
    st.title("📝 Novo Lançamento")
    if not editais: st.warning("Cadastre um edital primeiro.")
    else:
        conc = st.selectbox("Selecione o Edital:", list(editais.keys()))
        mats = list(editais[conc]["materias"].keys())
        mat = st.selectbox("Disciplina:", mats) if mats else None
        topicos = editais[conc]["materias"][mat] if mat else []
        
        with st.form("reg_form", clear_on_submit=True):
            d_in = st.date_input("Data", datetime.date.today())
            assunto = st.selectbox("Tópico:", topicos) if topicos else st.text_input("Tópico")
            a, t = st.columns(2)
            ac = a.number_input("Acertos", 0, step=1)
            tot = t.number_input("Total", 1, step=1)
            if st.form_submit_button("SALVAR REGISTRO", use_container_width=True):
                tx = (ac/tot*100)
                nova = pd.DataFrame([{
                    "Data_Estudo": d_in.strftime('%d/%m/%Y'),
                    "Usuario": usuario_atual,
                    "Concurso": conc, "Materia": mat, "Assunto": assunto,
                    "Acertos": str(ac), "Total": str(tot), "Taxa": f"{tx:.1f}%",
                    "Proxima_Revisao": (d_in + datetime.timedelta(days=7)).strftime('%d/%m/%Y')
                }])
                df_global = pd.concat([df_global, nova], ignore_index=True)
                salvar_dados(df_global)
                st.success("Estudo registrado com sucesso!")

elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Esquadrão")
    if not df_global.empty:
        df_g = df_global.copy()
        df_g['Total'] = pd.to_numeric(df_g['Total'], errors='coerce').fillna(0)
        rank = df_g.groupby("Usuario")['Total'].sum().reset_index().sort_values("Total", ascending=False)
        st.plotly_chart(px.bar(rank, x="Total", y="Usuario", orientation='h', title="Questões Totais"), use_container_width=True)
        
        stats = []
        for u in users_db.keys():
            du = df_g[df_g['Usuario'] == u]
            streak, _ = get_streak_metrics(du)
            stats.append({"Guerreiro": u, "Questões": int(du['Total'].sum()), "🔥 Streak": f"{streak}d"})
        st.table(pd.DataFrame(stats).sort_values("Questões", ascending=False))

elif selected == "Gestão Editais":
    st.title("📑 Editais Compartilhados")
    with st.expander("➕ Novo Concurso"):
        nc = st.text_input("Nome do Concurso")
        if st.button("Criar") and nc:
            editais[nc] = {"materias": {}}
            salvar_json(EDITAIS_FILE, editais)
            st.rerun()
    if editais:
        ed_sel = st.selectbox("Escolha para Editar:", list(editais.keys()))
        c1, c2 = st.columns([1, 2])
        with c1:
            nm = st.text_input("Nova Matéria")
            if st.button("Add Matéria") and nm:
                editais[ed_sel]["materias"][nm] = []
                salvar_json(EDITAIS_FILE, editais)
                st.rerun()
        with c2:
            for m, t in editais[ed_sel]["materias"].items():
                with st.expander(m):
                    txt = st.text_area(f"Tópicos para {m}", key=f"t_{m}")
                    if st.button("Importar", key=f"b_{m}") and txt:
                        editais[ed_sel]["materias"][m].extend([x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()])
                        salvar_json(EDITAIS_FILE, editais)
                        st.rerun()

elif selected == "Histórico":
    st.title("🗂️ Meus Registros")
    st.caption("Apenas você pode ver e editar seus próprios dados.")
    df_edit = st.data_editor(df_meu, use_container_width=True, num_rows="dynamic")
    if not df_edit.equals(df_meu):
        df_outros = df_global[df_global['Usuario'] != usuario_atual]
        df_final = pd.concat([df_outros, df_edit], ignore_index=True)
        salvar_dados(df_final)
        st.success("Histórico atualizado!")
