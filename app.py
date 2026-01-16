import streamlit as st
import pandas as pd
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO (SEM FIRULAS VISUAIS EXTRAS) ---
st.set_page_config(page_title="SQUAD COMMANDER", page_icon="💀", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    header {visibility: hidden;}
    
    /* Cores de Urgência baseadas no acerto */
    .card-critico { border-left: 5px solid #EF4444 !important; background-color: #1F1111; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #333; }
    .card-atencao { border-left: 5px solid #F59E0B !important; background-color: #1F1A11; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #333; }
    .card-safe    { border-left: 5px solid #10B981 !important; background-color: #111F15; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #333; }
    
    .txt-meta { font-size: 0.8em; color: #888; }
    .txt-strong { font-weight: bold; color: #FFF; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DATABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. FUNÇÕES ---
def get_editais():
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {"cargo": row.get('cargo') or "Geral", "data_iso": row.get('data_prova'), "materias": {}}
            if row.get('materia'): editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

def get_stats(concurso):
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", concurso).order("data_estudo", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- LÓGICA PURA DE REVISÃO (STICKY + PERFORMANCE) ---
def calcular_pendencias(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    
    pendencias = []
    
    # Proteção contra falta de colunas no banco
    for col in ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']:
        if col not in df.columns: df[col] = False
    
    for _, row in df.iterrows():
        dias = (hoje - row['dt_temp']).days
        # Define cor baseada no desempenho (Critério do Usuário: Errou muito = Treina mais)
        taxa = row['taxa'] if 'taxa' in row else 0
        if taxa < 60: css = "card-critico" # Vermelho
        elif taxa < 80: css = "card-atencao" # Amarelo
        else: css = "card-safe" # Verde
        
        base_obj = {
            "id": row['id'], "Materia": row['materia'], "Assunto": row['assunto'],
            "Data": row['dt_temp'].strftime('%d/%m'), "Taxa": taxa, "CSS": css
        }
        
        # Lógica Cumulativa: Se passou do dia E não marcou feito, entra na lista.
        if dias >= 1 and not row['rev_24h']:
            p = base_obj.copy(); p["Fase"] = "24h"; pendencias.append(p)
            
        if dias >= 7 and not row['rev_07d']:
            p = base_obj.copy(); p["Fase"] = "07d"; pendencias.append(p)
            
        if dias >= 15 and not row['rev_15d']:
            p = base_obj.copy(); p["Fase"] = "15d"; pendencias.append(p)
            
        if dias >= 30 and not row['rev_30d']:
            p = base_obj.copy(); p["Fase"] = "30d"; pendencias.append(p)
            
    return pd.DataFrame(pendencias)

# --- 4. APP ---
if 'missao_ativa' not in st.session_state: st.session_state.missao_ativa = None

# TELA INICIAL
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    editais = get_editais()
    if not editais: st.warning("Cadastre uma missão no menu lateral ou abaixo.")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        for nome, dados in editais.items():
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                col_a.markdown(f"### {nome}\n*{dados['cargo']}*")
                if col_b.button("ACESSAR", key=f"go_{nome}"):
                    st.session_state.missao_ativa = nome
                    st.rerun()
    with c2:
        with st.form("new_mission"):
            st.markdown("**Nova Missão**")
            n = st.text_input("Nome (Ex: PF)")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova")
            if st.form_submit_button("CRIAR"):
                supabase.table("editais_materias").insert({"concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), "materia": "Geral"}).execute()
                st.rerun()

# TELA DA MISSÃO
else:
    missao = st.session_state.missao_ativa
    dados = get_editais().get(missao, {})
    df = get_stats(missao)
    
    with st.sidebar:
        st.header(missao)
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["graph-up", "check-square", "pencil", "gear", "clock"], default_index=1)

    if menu == "Dashboard":
        st.title("📊 Indicadores")
        if df.empty: st.info("Sem dados.")
        else:
            tot = int(df['total'].sum())
            ac = int(df['acertos'].sum())
            if 'tempo' in df.columns: mins = df['tempo'].fillna(0).sum()
            else: mins = 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Questões", tot)
            c2.metric("Precisão Geral", f"{(ac/tot*100):.1f}%")
            c3.metric("Tempo Total", f"{int(mins//60)}h {int(mins%60)}m")

    # --- O CORAÇÃO DO SISTEMA: REVISÕES ---
    elif menu == "Revisões":
        st.title("🔄 Cronograma de Repetição")
        st.markdown("**Regra:** Errou muito (Vermelho)? Revisão Pesada. Acertou muito (Verde)? Leitura Rápida.")
        
        df_pend = calcular_pendencias(df)
        
        if df_pend.empty:
            st.success("✅ Tudo limpo. Nenhuma pendência nas camadas de memória.")
        else:
            cols = st.columns(4)
            phases = ["24h", "07d", "15d", "30d"]
            titles = ["🔥 D1 (Fixação)", "📅 D7 (Consolidação)", "🧠 D15 (Automação)", "💎 D30 (Manutenção)"]
            
            for i, fase in enumerate(phases):
                with cols[i]:
                    st.markdown(f"### {titles[i]}")
                    itens = df_pend[df_pend['Fase'] == fase]
                    if itens.empty:
                        st.caption("Vazio")
                    else:
                        for _, row in itens.iterrows():
                            # Card HTML Simples e Direto
                            st.markdown(f"""
                            <div class="{row['CSS']}">
                                <div class="txt-strong">{row['Materia']}</div>
                                <div style="font-size:0.9em">{row['Assunto']}</div>
                                <div class="txt-meta">
                                    Origem: {row['Data']} | Acerto: <b>{row['Taxa']:.0f}%</b>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Botão de Conclusão da Fase
                            key_btn = f"chk_{row['id']}_{fase}"
                            if st.button("Concluir", key=key_btn):
                                col_db = f"rev_{fase}" # Ex: rev_24h
                                try:
                                    supabase.table("registros_estudos").update({col_db: True}).eq("id", row['id']).execute()
                                    st.toast("Revisão registrada!")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error("Erro: Verifique se criou as colunas rev_24h, rev_07d... no Supabase.")

    elif menu == "Registrar":
        st.title("📝 Registrar Sessão")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias primeiro.")
        else:
            c1, c2 = st.columns(2)
            mat = c1.selectbox("Matéria", mats)
            top = dados['materias'].get(mat, []) or ["Geral"]
            assunto = c1.selectbox("Assunto", top)
            dt = c2.date_input("Data Estudo")
            
            c3, c4, c5, c6 = st.columns(4)
            ac = c3.number_input("Acertos", 0)
            tot = c4.number_input("Total", 1)
            h = c5.selectbox("Hs", range(13))
            m = c6.selectbox("Min", range(60))
            
            if st.button("SALVAR", type="primary"):
                try:
                    supabase.table("registros_estudos").insert({
                        "concurso": missao, "materia": mat, "assunto": assunto,
                        "data_estudo": dt.strftime('%Y-%m-%d'), 
                        "acertos": ac, "total": tot, "taxa": (ac/tot)*100, 
                        "tempo": h*60+m,
                        # Reseta as revisões para o novo registro
                        "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                    }).execute()
                    st.success("Salvo! Revisões agendadas.")
                except Exception as e: st.error(str(e))

    elif menu == "Configurar":
        st.title("⚙️ Matérias")
        n = st.text_input("Nova Matéria")
        if st.button("Adicionar"):
            supabase.table("editais_materias").insert({"concurso": missao, "materia": n, "topicos": []}).execute()
            st.rerun()
        
        st.divider()
        for m, t in dados.get('materias', {}).items():
            with st.expander(m):
                txt = st.text_area("Tópicos (;)", "; ".join(t), key=f"t_{m}")
                if st.button("Salvar", key=f"s_{m}"):
                    l = [x.strip() for x in txt.split(";") if x.strip()]
                    supabase.table("editais_materias").update({"topicos": l}).eq("concurso", missao).eq("materia", m).execute()
                    st.rerun()

    elif menu == "Histórico":
        st.title("📜 Histórico")
        if not df.empty:
            df['data_estudo'] = pd.to_datetime(df['data_estudo']).dt.date
            # Tabela Editável
            edited = st.data_editor(df[['id','data_estudo','materia','acertos','total']], hide_index=True, key='edit_hist')
            col_btn_1, col_btn_2 = st.columns(2)
            
            if col_btn_1.button("Salvar Alterações"):
                # Lógica de update simples
                for i, r in edited.iterrows():
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], 
                        "taxa": (r['acertos']/r['total']*100)
                    }).eq("id", r['id']).execute()
                st.rerun()
                
            # Zona de Exclusão Simples
            to_del = st.selectbox("Apagar registro:", df['id'].astype(str) + " - " + df['materia'], index=None)
            if to_del and col_btn_2.button("Excluir"):
                rid = to_del.split(" - ")[0]
                supabase.table("registros_estudos").delete().eq("id", rid).execute()
                st.rerun()
