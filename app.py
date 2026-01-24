# ============================================================================
# 🚀 IDEIA PRO: TREEMAP E MOMENTUM INDICATORS
# ============================================================================

def render_treemap_performance(df):
    """Gera um Treemap onde o tamanho é a Relevância e a cor é a Precisão"""
    fig = px.treemap(
        df, 
        path=['materia'], 
        values='relevancia', # O tamanho do bloco depende do quanto a matéria cai
        color='precisao',    # A cor depende do seu acerto
        color_continuous_scale=[COLORS["danger"], COLORS["warning"], COLORS["success"]],
        range_color=[0, 100]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )
    # Remove as bordas brancas padrão para manter o look dark
    fig.update_traces(marker_line_width=1, marker_line_color="rgba(255,255,255,0.1)")
    return fig

# --- NOVO BLOCO PARA O DASHBOARD ---

st.markdown("### 🧠 Inteligência Preditiva")

# Banner de Recomendação (Simulado)
st.info("🤖 **IA de Performance:** Você atingiu 90% em Direito Adm. Sugiro reduzir a carga horária desta matéria e focar 20min extras em RLM para recuperar o Momentum.")

col_tree, col_delta = st.columns([1.5, 1])

with col_tree:
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("#### 📐 Mapa de Calor de Relevância")
    st.plotly_chart(render_treemap_performance(df_data), use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with col_delta:
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    st.markdown("#### ⚡ Momentum (Últimos 7 dias)")
    
    # Exemplo de como exibir deltas de performance
    materias_momentum = [
        {"nome": "Português", "valor": "+5.2%", "status": "up"},
        {"nome": "RLM", "valor": "-2.1%", "status": "down"},
        {"nome": "Informática", "valor": "+12.0%", "status": "up"}
    ]
    
    for m in materias_momentum:
        cor = COLORS["success"] if m["status"] == "up" else COLORS["danger"]
        seta = "▲" if m["status"] == "up" else "▼"
        st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span>{m['nome']}</span>
                <span style="color: {cor}; font-weight: bold;">{seta} {m['valor']}</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
