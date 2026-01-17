import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import re
import time
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

from database import supabase
from logic import get_editais, excluir_concurso_completo
from styles import apply_styles

# Aplicar estilos base
apply_styles()

# CSS Customizado para Layout Moderno
st.markdown("""
    <style>
    /* Importar Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Estilo dos Cards (Glassmorphism) */
    .modern-card {
        background: rgba(26, 28, 35, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s ease, border 0.2s ease;
    }
    .modern-card:hover {
        border: 1px solid rgba(255, 75, 75, 0.4);
        transform: translateY(-2px);
    }

    /* Títulos e Textos */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .section-subtitle {
        color: #adb5bd;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1.5rem;
    }

    /* Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-red { background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.3); }
    .badge-green { background: rgba(0, 255, 0, 0.1); color: #00FF00; border: 1px solid rgba(0, 255, 0, 0.2); }
    .badge-gray { background: rgba(173, 181, 189, 0.1); color: #adb5bd; border: 1px solid rgba(173, 181, 189, 0.2); }

    /* Progress Bar */
    .modern-progress-container {
        width: 100%;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        height: 8px;
        margin: 10px 0;
        overflow: hidden;
    }
    .modern-progress-fill {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #FF4B4B, #FF8E8E);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0E1117;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Inputs e Botões */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES ---
def formatar_tempo_para_bigint(valor_bruto):
    numeros = re.sub(r'\D', '', str(valor_bruto)).zfill(4)
    return (int(numeros[:-2]) * 60) + int(numeros[-2:])

def render_metric_card(label, value, icon="📊"):
    st.markdown(f"""
        <div class="modern-card" style="text-align: center; padding: 15px;">
            <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: #adb5bd; font-size: 0.8rem; text-transform: uppercase;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #fff;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Selecione sua missão ou inicie um novo ciclo</p>', unsafe_allow_html=True)
    
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 Missões Ativas", "➕ Novo Cadastro"])
    
    with tabs[0]:
        if not ed: 
            st.info("Nenhuma missão ativa no momento.")
        else:
            cols = st.columns(2)
            for i, (nome, d_concurso) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="modern-card">
                            <h3 style="margin:0; color:#FF4B4B;">{nome}</h3>
                            <p style="color:#adb5bd; font-size:0.9rem; margin-bottom:15px;">{d_concurso['cargo']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Acessar Missão", key=f"ac_{nome}", use_container_width=True, type="primary"):
                        st.session_state.missao_ativa = nome
                        st.rerun()
else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except: df = pd.DataFrame()
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.markdown(f"<h2 style='color:#FF4B4B; margin-bottom:0;'>{missao}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#adb5bd; font-size:0.8rem; margin-bottom:20px;'>{dados.get('cargo', '')}</p>", unsafe_allow_html=True)
        
        if st.button("← Voltar à Central", use_container_width=True): 
            st.session_state.missao_ativa = None
            st.rerun()
        
        st.write("")
        menu = option_menu(None, ["Revisões", "Registrar", "Dashboard", "Histórico", "Configurar"], 
                           icons=["arrow-repeat", "pencil-square", "grid", "list", "gear"], 
                           default_index=0,
                           styles={
                               "container": {"padding": "0!important", "background-color": "transparent"},
                               "icon": {"color": "#FF4B4B", "font-size": "18px"}, 
                               "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "rgba(255,75,75,0.1)"},
                               "nav-link-selected": {"background-color": "rgba(255,75,75,0.2)", "border-left": "3px solid #FF4B4B"}
                           })

    # --- ABA: REVISÕES ---
    if menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            filtro_rev = st.segmented_control("Visualizar:", ["Pendentes/Hoje", "Todas (incluindo futuras)"], default="Pendentes/Hoje")
        
        hoje = datetime.date.today()
        pend = []
        if not df.empty:
            for _, row in df.iterrows():
                dt_est = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt_est).days
                tx = row.get('taxa', 0)
                
                # Lógica de Revisão 24h
                if not row.get('rev_24h', False):
                    dt_prev = dt_est + timedelta(days=1)
                    if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                        atraso = (hoje - dt_prev).days
                        pend.append({
                            "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                            "tipo": "Revisão 24h", "col": "rev_24h", "atraso": atraso, 
                            "data_prevista": dt_prev, "coment": row.get('comentarios', '')
                        })
                
                # Lógica de Ciclos Longos
                elif row.get('rev_24h', True):
                    d_alvo, col_alv, lbl = (7, "rev_07d", "Revisão 7d") if tx <= 75 else (15, "rev_15d", "Revisão 15d") if tx <= 79 else (20, "rev_30d", "Revisão 20d")
                    if not row.get(col_alv, False):
                        dt_prev = dt_est + timedelta(days=d_alvo)
                        if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                            atraso = (hoje - dt_prev).days
                            pend.append({
                                "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                                "tipo": lbl, "col": col_alv, "atraso": atraso, 
                                "data_prevista": dt_prev, "coment": row.get('comentarios', '')
                            })
        
        if not pend: 
            st.success("✨ Tudo em dia! Aproveite para avançar no conteúdo.")
        else:
            pend = sorted(pend, key=lambda x: x['data_prevista'])
            for p in pend:
                with st.container():
                    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                    c_info, c_input, c_action = st.columns([2, 1.5, 1])
                    
                    with c_info:
                        badge_class = "badge-red" if p['atraso'] > 0 else "badge-green" if p['atraso'] == 0 else "badge-gray"
                        status_text = f"⚠️ {p['atraso']}d atraso" if p['atraso'] > 0 else "🎯 Vence hoje" if p['atraso'] == 0 else "📅 Futura"
                        
                        st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                                <span class="badge {badge_class}">{status_text}</span>
                                <span style="color: #adb5bd; font-size: 12px;">{p['data_prevista'].strftime('%d/%m/%Y')}</span>
                            </div>
                            <h4 style="margin:0; color:#fff;">{p['materia']}</h4>
                            <p style="color:#adb5bd; font-size:0.85rem; margin:0;">{p['assunto']} • <b>{p['tipo']}</b></p>
                        """, unsafe_allow_html=True)
                        
                        if p['coment']:
                            with st.expander("📝 Ver Anotações"):
                                st.info(p['coment'])
                    
                    with c_input:
                        ci1, ci2 = st.columns(2)
                        acr_rev = ci1.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['col']}")
                        tor_rev = ci2.number_input("Total", 0, key=f"to_{p['id']}_{p['col']}")
                    
                    with c_action:
                        st.write("") # Alinhamento
                        if st.button("CONCLUIR", key=f"btn_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                            res_db = supabase.table("registros_estudos").select("acertos, total").eq("id", p['id']).execute()
                            n_ac = res_db.data[0]['acertos'] + acr_rev
                            n_to = res_db.data[0]['total'] + tor_rev
                            supabase.table("registros_estudos").update({
                                p['col']: True, 
                                "comentarios": f"{p['coment']} | {p['tipo']}: {acr_rev}/{tor_rev}", 
                                "acertos": n_ac, "total": n_to, 
                                "taxa": (n_ac/n_to*100 if n_to > 0 else 0)
                            }).eq("id", p['id']).execute()
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: REGISTRAR ---
    elif menu == "Registrar":
        st.markdown('<h2 class="main-title">📝 Novo Registro de Estudo</h2>', unsafe_allow_html=True)
        mats = list(dados.get('materias', {}).keys())
        
        if not mats:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'Configurar' para adicionar disciplinas.")
        else:
            with st.container():
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                # Usando formulário para garantir que o botão dispare a ação corretamente
                with st.form("form_registro", clear_on_submit=True):
                    c1, c2 = st.columns([2, 1])
                    dt_reg = c1.date_input("Data do Estudo", format="DD/MM/YYYY")
                    tm_reg = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30min")
                    
                    mat_reg = st.selectbox("Disciplina", mats)
                    ass_reg = st.selectbox("Assunto", dados['materias'].get(mat_reg, ["Geral"]), key=f"assunto_{mat_reg}")
                    
                    st.divider()
                    ca_reg, ct_reg = st.columns(2)
                    ac_reg = ca_reg.number_input("Questões Acertadas", 0)
                    to_reg = ct_reg.number_input("Total de Questões", 1)
                    
                    com_reg = st.text_area("Anotações / Comentários", placeholder="O que você aprendeu ou sentiu dificuldade?")
                    
                    btn_salvar = st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True, type="primary")
                    
                    if btn_salvar:
                        try:
                            t_b = formatar_tempo_para_bigint(tm_reg)
                            payload = {
                                "concurso": missao, "materia": mat_reg, "assunto": ass_reg, 
                                "data_estudo": dt_reg.strftime('%Y-%m-%d'), "acertos": ac_reg, 
                                "total": to_reg, "taxa": (ac_reg/to_reg*100 if to_reg > 0 else 0), "comentarios": com_reg, 
                                "tempo": t_b, "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False
                            }
                            supabase.table("registros_estudos").insert(payload).execute()
                            st.success("✅ Registro salvo com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        if df.empty:
            st.info("Ainda não há dados suficientes para gerar o dashboard.")
        else:
            # Métricas Principais
            t_q = df['total'].sum()
            a_q = df['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q>0 else 0)
            horas = df['tempo'].sum()/60
            
            m1, m2, m3 = st.columns(3)
            with m1: render_metric_card("Total de Questões", int(t_q), "📝")
            with m2: render_metric_card("Precisão Média", f"{precisao:.1f}%", "🎯")
            with m3: render_metric_card("Horas Estudadas", f"{horas:.1f}h", "⏱️")
            
            st.write("")
            
            # Gráficos
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Distribuição por Matéria")
                fig_pie = px.pie(df, values='total', names='materia', hole=0.6, 
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True, 
                                     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                     font=dict(color="#fff"))
                st.plotly_chart(fig_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c_g2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### Evolução de Precisão")
                df_ev = df.groupby('data_estudo')['taxa'].mean().reset_index()
                fig_line = px.line(df_ev, x='data_estudo', y='taxa', markers=True)
                fig_line.update_traces(line_color='#FF4B4B', marker=dict(size=8))
                fig_line.update_layout(margin=dict(t=20, b=0, l=0, r=0), 
                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      font=dict(color="#fff"), xaxis_title=None, yaxis_title="Taxa %")
                st.plotly_chart(fig_line, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Detalhamento por Matéria
            st.markdown("### 📁 Detalhamento por Disciplina")
            df_mat = df.groupby('materia').agg({'total': 'sum', 'taxa': 'mean'}).reset_index().sort_values('total', ascending=False)
            
            for _, m in df_mat.iterrows():
                with st.expander(f"{m['materia'].upper()} — {m['taxa']:.1f}% de Precisão"):
                    df_ass = df[df['materia'] == m['materia']].groupby('assunto').agg({'total': 'sum', 'acertos': 'sum', 'taxa': 'mean'}).reset_index()
                    for _, a in df_ass.iterrows():
                        ca1, ca2 = st.columns([4, 1])
                        ca1.markdown(f"<span style='color:#fff; font-size:0.9rem;'>{a['assunto']}</span>", unsafe_allow_html=True)
                        ca2.markdown(f"<p style='text-align: right; color:#adb5bd; font-size: 0.8rem;'>{int(a['acertos'])}/{int(a['total'])}</p>", unsafe_allow_html=True)
                        st.markdown(f"""
                            <div class="modern-progress-container">
                                <div class="modern-progress-fill" style="width: {a['taxa']}%;"></div>
                            </div>
                        """, unsafe_allow_html=True)

    # --- ABA: HISTÓRICO ---
    elif menu == "Histórico":
        st.markdown('<h2 class="main-title">📜 Histórico de Estudos</h2>', unsafe_allow_html=True)
        if not df.empty:
            df_h = df.copy()
            df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.data_editor(
                df_h[['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "taxa": st.column_config.ProgressColumn("Precisão", format="%.1f%%", min_value=0, max_value=100),
                    "data_estudo": "Data",
                    "tempo": "Minutos"
                }
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: CONFIGURAR ---
    elif menu == "Configurar":
        st.markdown('<h2 class="main-title">⚙️ Configurações do Edital</h2>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### Adicionar Nova Disciplina")
            with st.form("add_mat", clear_on_submit=True):
                nm = st.text_input("Nome da Matéria")
                if st.form_submit_button("➕ ADICIONAR MATÉRIA", use_container_width=True):
                    if nm:
                        supabase.table("editais_materias").insert({
                            "concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []
                        }).execute()
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        if dados.get('materias'):
            st.markdown("### 📚 Matérias Cadastradas")
            for m, t in dados['materias'].items():
                with st.expander(f"📖 {m}"):
                    tx = st.text_area("Tópicos (um por linha)", value="\n".join(t), key=f"tx_{m}", height=150)
                    cs, cd = st.columns(2)
                    if cs.button("💾 SALVAR TÓPICOS", key=f"s_{m}", use_container_width=True, type="primary"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute()
                        st.toast("Tópicos atualizados!")
                    if cd.button("🗑️ EXCLUIR MATÉRIA", key=f"d_{m}", use_container_width=True):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute()
                        st.rerun()
