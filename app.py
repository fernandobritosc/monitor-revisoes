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
TOKENS_FILE = "tokens_db.json"
META_QUESTOES = 2000 

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

def gerar_novo_token():
    chars = string.ascii_uppercase + string.digits
    codigo = "SK-" + ''.join(secrets.choice(chars) for _ in range(4))
    tokens = carregar_json(TOKENS_FILE)
    if "ativos" not in tokens: tokens["ativos"] = []
    tokens["ativos"].append(codigo)
    salvar_json(TOKENS_FILE, tokens)
    return codigo

def calcular_revisao(data_base, taxa):
    if taxa < 70: dias = 1
    elif taxa < 90: dias = 7
    else: dias = 21
    return data_base + datetime.timedelta(days=dias)

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
                st.info("Nenhum usuário. Gere um token inicial.")
                if st.button("Gerar Token de Primeiro Acesso"):
                    tk = gerar_novo_token()
                    st.success(f"Token: {tk}")
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
                t_token = st.text_input("Token de Convite")
                n_user = st.text_input("Nome do Guerreiro")
                n_pin = st.text_input("PIN (4 dígitos)", type="password", max_chars=4)
                n_rec = st.text_input("Palavra-Chave (Reset de Senha)")
                if st.form_submit_button("CRIAR CONTA"):
                    ativos = tokens_db.get("ativos", [])
                    if t_token not in ativos: st.error("Token inválido.")
                    elif n_user in users_db: st.error("Usuário já existe.")
                    else:
                        users_db[n_user] = {"pin": n_pin, "chave": n_rec}
                        salvar_json(USERS_FILE, users_db)
                        ativos.remove(t_token)
                        tokens_db["ativos"] = ativos
                        salvar_json(TOKENS_FILE, tokens_db)
                        st.success("Conta criada!")

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
    st.stop()

# --- ÁREA LOGADA ---
usuario_atual = st.session_state.usuario_logado
df_global = carregar_dados()
editais = carregar_json(EDITAIS_FILE)
df_meu = df_global[df_global['Usuario'] == usuario_atual].copy()

with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 SAIR"):
        del st.session_state.usuario_logado
        st.rerun()
    
    menus = ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"]
    icons = ["bar-chart", "plus-circle", "trophy", "book-half", "table"]
    if usuario_atual == "Fernando":
        menus.append("Gerar Convites")
        icons.append("ticket-perforated")

    selected = option_menu("Menu Tático", menus, icons=icons, default_index=0)

# === PÁGINAS ===
if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_meu.empty:
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

        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🕸️ Radar Tático")
            df_radar = df_meu.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="N")
            if not df_radar.empty:
                fig = go.Figure(data=go.Scatterpolar(r=df_radar['N'], theta=df_radar['Materia'], fill='toself', line_color='#00E676'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            st.subheader("📈 Evolução")
            df_meu['Data_Real'] = pd.to_datetime(df_meu['Data_Estudo'], dayfirst=True, errors='coerce')
            df_t = df_meu.groupby("Data_Real")['Total'].sum().reset_index()
            st.plotly_chart(px.line(df_t, x="Data_Real", y="Total", markers=True).update_traces(line_color='#00E676'), use_container_width=True)
    else: st.info("Bora estudar! 💀")

elif selected == "Novo Registro":
    st.title("📝 Registro de Estudo")
    if not editais: st.warning("Cadastre um Edital primeiro!")
    else:
        conc = st.selectbox("Edital:", list(editais.keys()))
        mats = list(editais[conc]["materias"].keys())
        mat = st.selectbox("Disciplina:", mats) if mats else None
        topicos = editais[conc]["materias"][mat] if mat else []
        with st.form("reg_form", clear_on_submit=True):
            d_in = st.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
            ass = st.selectbox("Tópico:", topicos) if topicos else st.text_input("Tópico")
            a, t = st.columns(2)
            ac, tot = a.number_input("Acertos", 0), t.number_input("Total", 1)
            if st.form_submit_button("SALVAR", use_container_width=True):
                tx = (ac/tot*100)
                nova = pd.DataFrame([{"Data_Estudo": d_in.strftime('%d/%m/%Y'), "Usuario": usuario_atual, "Concurso": conc, "Materia": mat, "Assunto": ass, "Acertos": str(ac), "Total": str(tot), "Taxa": f"{tx:.1f}%", "Proxima_Revisao": calcular_revisao(d_in, tx).strftime('%d/%m/%Y')}])
                salvar_dados(pd.concat([df_global, nova], ignore_index=True))
                st.success("Salvo!")

elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Esquadrão")
    if not df_global.empty:
        df_g = df_global.copy()
        df_g['Total'] = pd.to_numeric(df_g['Total'], errors='coerce').fillna(0)
        rank = df_g.groupby("Usuario")['Total'].sum().reset_index().sort_values("Total", ascending=False)
        st.plotly_chart(px.bar(rank, x="Total", y="Usuario", orientation='h', color="Usuario"), use_container_width=True)

elif selected == "Gestão Editais":
    st.title("📑 Editais")
    with st.expander("➕ Novo Concurso"):
        with st.form("new_c"):
            n, c, d = st.columns(3)
            name, cargo, date = n.text_input("Nome"), c.text_input("Cargo"), d.date_input("Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                editais[name] = {"cargo": cargo, "data": date.strftime('%Y-%m-%d'), "materias": {}}
                salvar_json(EDITAIS_FILE, editais); st.rerun()
    if editais:
        ed_sel = st.selectbox("Escolha:", list(editais.keys()))
        c1, c2 = st.columns([1, 2])
        with c1:
            nm = st.text_input("Nova Matéria")
            if st.button("Add"):
                editais[ed_sel]["materias"][nm] = []; salvar_json(EDITAIS_FILE, editais); st.rerun()
        with c2:
            for m, t in editais[ed_sel]["materias"].items():
                with st.expander(f"{m} ({len(t)})"):
                    txt = st.text_area(f"Importar p/ {m}", key=f"t_{m}")
                    if st.button("OK", key=f"b_{m}") and txt:
                        editais[ed_sel]["materias"][m].extend([x.strip() for x in txt.replace("\n", ";").split(";") if x.strip()])
                        salvar_json(EDITAIS_FILE, editais); st.rerun()

elif selected == "Histórico":
    st.title("🗂️ Meus Dados")
    df_edit = st.data_editor(df_meu, use_container_width=True, num_rows="dynamic")
    if not df_edit.equals(df_meu):
        salvar_dados(pd.concat([df_global[df_global['Usuario'] != usuario_atual], df_edit], ignore_index=True))
        st.success("Atualizado!")

elif selected == "Gerar Convites":
    st.title("🎟️ Convites")
    if st.button("Gerar Novo"): st.code(gerar_novo_token())
    st.write("Tokens Ativos:", carregar_json(TOKENS_FILE).get("ativos", []))
