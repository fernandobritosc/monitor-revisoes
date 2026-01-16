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

DB_FILE = "estudos_data.csv"
EDITAIS_FILE = "editais_db.json"
META_QUESTOES = 2000 

# --- CONFIGURAÇÃO DE ACESSO (O SQUAD) ---
SQUAD_ACCESS = {
    "Fernando": "1234",
    "Lucas": "2222",
    "André": "3333",
    "Tiago": "4444"
}

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, sep=';', dtype=str)
            return df
        except:
            return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])
    return pd.DataFrame(columns=["Data_Estudo", "Usuario", "Concurso", "Materia", "Assunto", "Acertos", "Total", "Taxa", "Proxima_Revisao"])

def salvar_dados(dataframe):
    dataframe.to_csv(DB_FILE, index=False, sep=';', encoding='utf-8-sig')

def carregar_editais():
    if os.path.exists(EDITAIS_FILE):
        try:
            with open(EDITAIS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_editais(editais_dict):
    with open(EDITAIS_FILE, "w", encoding="utf-8") as f:
        json.dump(editais_dict, f, indent=4, ensure_ascii=False)

def calcular_metricas_streak(df):
    if df.empty: return 0, 0
    try:
        dates = pd.to_datetime(df['Data_Estudo'], dayfirst=True, errors='coerce').dt.normalize().dropna().unique()
        dates = sorted(dates)
        if not len(dates): return 0, 0
        max_streak, current_run = 1, 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1: current_run += 1
            else:
                max_streak = max(max_streak, current_run)
                current_run = 1
        max_streak = max(max_streak, current_run)
        hoje = pd.Timestamp.now().normalize()
        streak_atual = 0
        dates_reverse = sorted(dates, reverse=True)
        if hoje in dates:
            streak_atual = 1
            check_date = hoje - pd.Timedelta(days=1)
        elif (hoje - pd.Timedelta(days=1)) in dates:
            streak_atual = 0
            check_date = hoje - pd.Timedelta(days=1)
        else: return 0, max_streak
        for d in dates_reverse:
            if d == hoje: continue
            if d == check_date:
                streak_atual += 1
                check_date -= pd.Timedelta(days=1)
            else: break
        return streak_atual, max_streak
    except: return 0, 0

# Inicialização
if 'df_dados' not in st.session_state:
    st.session_state.df_dados = carregar_dados()
if 'editais' not in st.session_state:
    st.session_state.editais = carregar_editais()

# --- SISTEMA DE LOGIN COM VALIDAÇÃO ---
if 'usuario_logado' not in st.session_state:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>💀 ACESSO SQUAD</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            user_input = st.selectbox("Quem está acessando?", list(SQUAD_ACCESS.keys()))
            pin_input = st.text_input("Digite seu PIN de 4 dígitos:", type="password")
            
            if st.button("AUTENTICAR", type="primary", use_container_width=True):
                if pin_input == SQUAD_ACCESS[user_input]:
                    st.session_state.usuario_logado = user_input
                    st.success(f"Bem-vindo, {user_input}!")
                    st.rerun()
                else:
                    st.error("PIN INCORRETO. Acesso Negado.")
        st.info("💡 Cada membro tem seu PIN individual para proteger seu histórico.")
    st.stop()

# --- CONTINUAÇÃO PÓS-LOGIN ---
usuario_atual = st.session_state.usuario_logado
df = st.session_state.df_dados
editais = st.session_state.editais
df_user = df[df['Usuario'] == usuario_atual].copy()

# Barra Lateral
with st.sidebar:
    st.markdown(f"### 🥷 {usuario_atual}")
    if st.button("🚪 LOGOUT"):
        del st.session_state.usuario_logado
        st.rerun()
    st.markdown("---")
    selected = option_menu(
        "Painel Tático", ["Dashboard", "Novo Registro", "Ranking Squad", "Gestão Editais", "Histórico"],
        icons=["bar-chart", "plus", "trophy", "book", "table"], default_index=0,
        styles={"nav-link-selected": {"background-color": "#00C853"}}
    )

# === DASHBOARD ===
if selected == "Dashboard":
    st.title(f"📊 Painel: {usuario_atual}")
    if not df_user.empty:
        # Metricas e Gráficos Pessoais
        total_q = pd.to_numeric(df_user['Total'], errors='coerce').sum()
        acertos = pd.to_numeric(df_user['Acertos'], errors='coerce').sum()
        precisao = (acertos/total_q*100) if total_q > 0 else 0
        streak, recorde = calcular_metricas_streak(df_user)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", int(total_q), border=True)
        c2.metric("Precisão", f"{precisao:.1f}%", border=True)
        c3.metric("🔥 Streak", f"{streak}d", border=True)
        c4.metric("🏆 Recorde", f"{recorde}d", border=True)

        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🕸️ Radar Tático")
            df_radar = df_user.copy()
            df_radar['Acertos'] = pd.to_numeric(df_radar['Acertos'], errors='coerce')
            df_radar['Total'] = pd.to_numeric(df_radar['Total'], errors='coerce')
            df_r = df_radar.groupby("Materia").apply(lambda x: (x['Acertos'].sum()/x['Total'].sum()*100)).reset_index(name="Nota")
            if not df_r.empty:
                fig = go.Figure(data=go.Scatterpolar(r=df_r['Nota'], theta=df_r['Materia'], fill='toself', line_color='#00E676'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            st.subheader("📉 Mapa da Vergonha")
            df_v = df_user.copy()
            df_v['Acertos'] = pd.to_numeric(df_v['Acertos'], errors='coerce')
            df_v['Total'] = pd.to_numeric(df_v['Total'], errors='coerce')
            resumo = df_v.groupby(["Materia", "Assunto"])[["Acertos", "Total"]].sum().reset_index()
            resumo["Nota"] = (resumo["Acertos"]/resumo["Total"]*100)
            piores = resumo[resumo["Nota"] < 80].sort_values("Nota")
            if not piores.empty:
                st.dataframe(piores[["Materia", "Assunto", "Nota"]], use_container_width=True, hide_index=True)
            else: st.success("Nada abaixo de 80%!")
    else: st.info("Bora começar os estudos!")

# === NOVO REGISTRO ===
elif selected == "Novo Registro":
    st.title("📝 Lançamento")
    if not editais: st.warning("Cadastre um Edital primeiro!")
    else:
        concurso_sel = st.selectbox("Edital:", list(editais.keys()))
        mats = list(editais[concurso_sel]["materias"].keys())
        mat_sel = st.selectbox("Disciplina:", mats) if mats else None
        topicos = editais[concurso_sel]["materias"][mat_sel] if mat_sel else []

        with st.form("registro"):
            c_data, c_ass = st.columns([1, 2])
            data_in = c_data.date_input("Data", datetime.date.today())
            assunto = c_ass.selectbox("Tópico:", topicos) if topicos else c_ass.text_input("Tópico")
            a, t = st.columns(2)
            ac = a.number_input("Acertos", min_value=0, step=1)
            tot = t.number_input("Total", min_value=1, step=1)
            if st.form_submit_button("SALVAR REGISTRO", use_container_width=True):
                tx = (ac/tot*100)
                nova = pd.DataFrame([{
                    "Data_Estudo": data_in.strftime('%d/%m/%Y'),
                    "Usuario": usuario_atual,
                    "Concurso": concurso_sel,
                    "Materia": mat_sel if mat_sel else "Geral",
                    "Assunto": assunto,
                    "Acertos": str(ac), "Total": str(tot), "Taxa": f"{tx:.1f}%"
                }])
                st.session_state.df_dados = pd.concat([df, nova], ignore_index=True)
                salvar_dados(st.session_state.df_dados)
                st.success("Registrado!")

# === RANKING SQUAD ===
elif selected == "Ranking Squad":
    st.title("🏆 Ranking do Esquadrão")
    df_q = df.copy()
    df_q['Total'] = pd.to_numeric(df_q['Total'], errors='coerce').fillna(0)
    rank = df_q.groupby("Usuario")['Total'].sum().reset_index().sort_values("Total", ascending=False)
    st.plotly_chart(px.bar(rank, x="Total", y="Usuario", orientation='h', color="Usuario"), use_container_width=True)
    
    detalhes = []
    for u in SQUAD_ACCESS.keys():
        du = df_q[df_q['Usuario'] == u]
        tot = du['Total'].sum()
        streak, _ = calcular_metricas_streak(du)
        detalhes.append({"Guerreiro": u, "Questões": int(tot), "🔥 Streak": streak})
    st.table(pd.DataFrame(detalhes).sort_values("Questões", ascending=False))

# === GESTÃO EDITADOS (PROTEGIDA) ===
elif selected == "Gestão Editais":
    st.title("📑 Editais")
    with st.expander("➕ Novo Edital"):
        n_conc = st.text_input("Nome")
        if st.button("Criar"):
            editais[n_conc] = {"materias": {}, "criador": usuario_atual}
            salvar_editais(editais)
            st.rerun()
    
    if editais:
        ed_sel = st.selectbox("Editar:", list(editais.keys()))
        ed_data = editais[ed_sel]
        st.caption(f"Criado por: {ed_data.get('criador', 'Sistema')}")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            n_mat = st.text_input("Matéria")
            if st.button("Add"):
                ed_data["materias"][n_mat] = []
                salvar_editais(editais)
                st.rerun()
        with c2:
            for m, t in ed_data["materias"].items():
                with st.expander(m):
                    txt = st.text_area(f"Importar p/ {m}", key=f"t_{m}")
                    if st.button("OK", key=f"b_{m}"):
                        ed_data["materias"][m].extend([x.strip() for x in txt.split(";") if x.strip()])
                        salvar_editais(editais)
                        st.rerun()

# === HISTÓRICO (PRIVADO) ===
elif selected == "Histórico":
    st.title("🗂️ Meus Dados")
    st.info("Aqui você só vê e edita os SEUS registros.")
    # Filtro automático: usuário só vê o que é dele
    df_user_edit = st.data_editor(df_user, use_container_width=True, num_rows="dynamic")
    
    if not df_user_edit.equals(df_user):
        df_limpo = df[df['Usuario'] != usuario_atual]
        df_final = pd.concat([df_limpo, df_user_edit], ignore_index=True)
        st.session_state.df_dados = df_final
        salvar_dados(df_final)
        st.success("Dados salvos!")
