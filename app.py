import streamlit as st
import pandas as pd
import time
import datetime
import plotly.express as px
import re
from streamlit_option_menu import option_menu

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="Monitor de Revisões", layout="wide")

from database import supabase
from logic import get_editais, calcular_pendencias, excluir_concurso_completo
from styles import apply_styles

apply_styles()

if 'missao_ativa' not in st.session_state:
    st.session_state.missao_ativa = None

# REGRA HHMM: 0130 -> 01:30:00 (OK)
def formatar_tempo_estudo(valor_bruto):
    numeros = re.sub(r'\D', '', valor_bruto) 
    if not numeros: return "00:00:00"
    numeros = numeros.zfill(4)
    horas = numeros[:-2].zfill(2)
    minutos = numeros[-2:].zfill(2)
    return f"{horas}:{minutos}:00"

# --- 2. CENTRAL DE COMANDO ---
if st.session_state.missao_ativa is None:
    st.title("💀 CENTRAL DE COMANDO")
    tabs = st.tabs(["🎯 Missões Ativas", "➕ Novo Concurso"])
    
    with tabs[0]:
        ed = get_editais(supabase)
        if not ed: st.info("Nenhum concurso cadastrado.")
        for nome, dados in ed.items():
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 0.5])
                c1.markdown(f"### {nome}\n*{dados['cargo']}*")
                if c2.button("ACESSAR", key=f"ac_{nome}"):
                    st.session_state.missao_ativa = nome; st.rerun()
                if c3.button("🗑️", key=f"del_{nome}"):
                    st.session_state[f"confirm_del_{nome}"] = True
                if st.session_state.get(f"confirm_del_{nome}", False):
                    st.warning(f"Excluir **{nome}**?")
                    cs, cn = st.columns(2)
                    if cs.button("✅ SIM", key=f"y_{nome}"):
                        if excluir_concurso_completo(supabase, nome):
                            st.toast("Removido!"); del st.session_state[f"confirm_del_{nome}"]; st.rerun()
                    if cn.button("❌ NÃO", key=f"n_{nome}"):
                        del st.session_state[f"confirm_del_{nome}"]; st.rerun()

    with tabs[1]:
        st.subheader("📝 Cadastro de Nova Missão")
        with st.form("f_novo"):
            n_n, n_c = st.text_input("Nome"), st.text_input("Cargo")
            if st.form_submit_button("CRIAR"):
                if n_n:
                    supabase.table("editais_materias").insert({"concurso": n_n, "cargo": n_c, "materia": "Geral", "topicos": []}).execute()
                    st.rerun()

# --- 3. PAINEL INTERNO ---
else:
    missao = st.session_state.missao_ativa
    try:
        res = supabase.table("registros_estudos").select("*").eq("concurso", missao).order("data_estudo", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()
        
    dados = get_editais(supabase).get(missao, {})

    with st.sidebar:
        st.title(f"🎯 {missao}")
        if st.button("🔙 VOLTAR"): st.session_state.missao_ativa = None; st.rerun()
        st.divider()
        menu = option_menu(None, ["Dashboard", "Revisões", "Registrar", "Configurar", "Histórico"], 
                           icons=["speedometer2", "arrow-repeat", "pencil-square", "gear", "list-task"], default_index=0)

    # --- ABA DASHBOARD (v133.0 - INTELIGÊNCIA DE DADOS) ---
    if menu == "Dashboard":
        st.subheader("📊 Painel de Performance Tática")
        if df.empty:
            st.info("Aguardando dados para gerar as análises...")
        else:
            # Cálculos de tempo
            def conv_min(t_str):
                try:
                    h, m, s = map(int, t_str.split(':'))
                    return h * 60 + m
                except: return 0
            df['minutos'] = df['tempo'].apply(conv_min)
            
            # KPIs
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            tot_q = df['total'].sum()
            acc_q = df['acertos'].sum()
            c1.metric("Questões Totais", f"{int(tot_q)}")
            c2.metric("Precisão Geral", f"{(acc_q/tot_q*100 if tot_q > 0 else 0):.1f}%")
            c3.metric("Sessões", len(df))
            c4.metric("Horas de Voo", f"{(df['minutos'].sum()/60):.1f}h")
            st.divider()

            # Gráficos
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("#### 📈 Evolução de Precisão (%)")
                df_ev = df.groupby('data_estudo')['taxa'].mean().reset_index().sort_values('data_estudo')
                fig_l = px.line(df_ev, x='data_estudo', y='taxa', markers=True, color_discrete_sequence=['#ff4b4b'])
                fig_l.update_layout(yaxis_range=[0, 100])
                st.plotly_chart(fig_l, use_container_width=True)
            with g2:
                st.markdown("#### ⏳ Carga Horária por Matéria")
                df_t = df.groupby('materia')['minutos'].sum().reset_index()
                fig_p = px.pie(df_t, values='minutos', names='materia', hole=0.4)
                st.plotly_chart(fig_p, use_container_width=True)

    # --- ABA REVISÕES (DESIGN PREMIUM) ---
    elif menu == "Revisões":
        st.subheader("🔄 Radar de Revisões")
        if df.empty: st.info("Sem registros.")
        else:
            hoje = datetime.date.today()
            pend = []
            cores = {"Revisão 24h": "blue", "Revisão 7d": "orange", "Revisão 15d": "purple", "Revisão 20d": "green"}
            for _, row in df.iterrows():
                dt = pd.to_datetime(row['data_estudo']).date()
                dias = (hoje - dt).days
                tx = row.get('taxa', 0)
                if dias >= 1 and not row.get('rev_24h', False):
                    pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": "Revisão 24h", "col": "rev_24h", "atraso": dias - 1, "c": row.get('comentarios', '')})
                if row.get('rev_24h', False):
                    if tx <= 75: d, col, lbl = 7, "rev_07d", "Revisão 7d"
                    elif 76 <= tx <= 79: d, col, lbl = 15, "rev_15d", "Revisão 15d"
                    else: d, col, lbl = 20, "rev_30d", "Revisão 20d"
                    if dias >= d and not row.get(col, False):
                        pend.append({"id": row['id'], "materia": row['materia'], "assunto": row['assunto'], "tipo": lbl, "col": col, "atraso": dias - d, "c": row.get('comentarios', '')})
            
            if not pend: st.success("✅ Tudo em dia!")
            else:
                for p in pend:
                    with st.container(border=True):
                        c_i, c_a = st.columns([1.8, 1])
                        with c_i:
                            st.markdown(f"### {p['materia']}\n**{p['assunto']}**\n\n:{cores.get(p['tipo'], 'grey')}[**{p['tipo']}**]")
                            if p['c']: 
                                with st.expander("🔗 Links/Caderno"): st.write(p['c'])
                        with c_a:
                            st.write("")
                            ca, ct = st.columns(2)
                            ac_r = ca.number_input("Acertos", 0, key=f"ac_{p['id']}_{p['col']}")
                            to_r = ct.number_input("Total", 0, key=f"to_{p['id']}_{p['col']}")
                            if st.button("CONCLUIR", key=f"b_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                                tx_r = (ac_r/to_r*100) if to_r > 0 else 0
                                n_c = f"{p['c']} | {p['tipo']}: {ac_r}/{to_r} ({tx_r:.1f}%)".strip(" | ")
                                supabase.table("registros_estudos").update({p['col']: True, "comentarios": n_c}).eq("id", p['id']).execute()
                                st.rerun()
                            if p['atraso'] > 0: st.error(f"⚠️ {p['atraso']}d de atraso")
                            else: st.success("🟢 No prazo")

    # --- DEMAIS ABAS (CONFIGURAR, REGISTRAR, HISTÓRICO) ---
    elif menu == "Registrar":
        st.subheader("📝 Novo Registro")
        mats = list(dados.get('materias', {}).keys())
        if not mats: st.warning("Cadastre matérias no menu Configurar.")
        else:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                dt = c1.date_input("Data", datetime.date.today(), format="DD/MM/YYYY")
                t_b = c2.text_input("Tempo (HHMM)", placeholder="0130")
                t_f = formatar_tempo_estudo(t_b)
                st.info(f"Tempo: **{t_f}**")
                mat = st.selectbox("Disciplina", mats); ass = st.selectbox("Tópico", dados['materias'].get(mat, ["Geral"]))
                ca, ct = st.columns(2); ac = ca.number_input("Acertos", 0); tot = ct.number_input("Total", 1)
                com = st.text_area("Comentários (Links TEC)")
                if st.button("💾 SALVAR", type="primary", use_container_width=True):
                    supabase.table("registros_estudos").insert({"concurso": missao, "materia": mat, "assunto": ass, "data_estudo": dt.strftime('%Y-%m-%d'), "acertos": ac, "total": tot, "taxa": (ac/tot*100), "comentarios": str(com), "tempo": str(t_f), "rev_24h": False, "rev_07d": False, "rev_15d": False, "rev_30d": False}).execute()
                    st.success("✅ SALVO!"); st.rerun()

    elif menu == "Histórico":
        st.subheader("📜 Histórico")
        if df.empty: st.info("Sem dados.")
        else:
            df_h = df.copy()
            df_h['data_estudo'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            df_h['id'] = df_h['id'].astype(str)
            df_h['taxa'] = pd.to_numeric(df_h['taxa'], errors='coerce').fillna(0).astype(float)
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Questões", int(df_h['total'].sum())); k2.metric("Precisão", f"{df_h['taxa'].mean():.1f}%"); k3.metric("Lançamentos", len(df_h))
            st.divider()
            cols = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']
            ed = st.data_editor(df_h[cols], hide_index=True, use_container_width=True, column_config={"taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%")})
            c_s, c_d = st.columns([4, 1])
            if c_s.button("💾 SALVAR ALTERAÇÕES"):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({"acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso, "tempo": r['tempo'], "comentarios": r['comentarios'], "taxa": (r['acertos']/r['total']*100)}).eq("id", r['id']).execute()
                st.rerun()
            with c_d.popover("🗑️ APAGAR"):
                id_del = st.text_input("ID")
                if st.button("CONFIRMAR"):
                    supabase.table("registros_estudos").delete().eq("id", id_del).execute(); st.rerun()

    elif menu == "Configurar":
        st.subheader("⚙️ Configurar Edital")
        with st.form("add_m"):
            c1, c2 = st.columns([3, 1])
            nm = c1.text_input("Disciplina")
            if c2.form_submit_button("➕ ADD"):
                if nm: supabase.table("editais_materias").insert({"concurso": missao, "cargo": dados['cargo'], "materia": nm, "topicos": []}).execute(); st.rerun()
        if dados.get('materias'):
            for m, t in dados['materias'].items():
                with st.expander(f"📚 {m}"):
                    tx = st.text_area("Tópicos", value="\n".join(t), key=f"tx_{m}")
                    if st.button("💾 SALVAR", key=f"s_{m}"):
                        novos = [l.strip() for l in tx.split('\n') if l.strip()]
                        supabase.table("editais_materias").update({"topicos": novos}).eq("concurso", missao).eq("materia", m).execute(); st.rerun()
                    if st.button("🗑️ EXCLUIR", key=f"d_{m}"):
                        supabase.table("editais_materias").delete().eq("concurso", missao).eq("materia", m).execute(); st.rerun()
