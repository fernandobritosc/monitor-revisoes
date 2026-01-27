"""
CSS COMPLETO COM LAYOUT FIXO PARA MONITORPRO
Cole esta função no seu app.py e chame após st.set_page_config()
"""

import streamlit as st

def aplicar_css_completo_layout_fixo(COLORS):
    """
    CSS completo com layout fixo e todos os estilos do MonitorPro
    
    USO:
    1. Cole esta função no início do seu app.py (após os imports)
    2. Logo após st.set_page_config(), adicione: aplicar_css_completo_layout_fixo(COLORS)
    """
    st.markdown(f"""
        <style>
        /* ===============================================
           VARIÁVEIS GLOBAIS - LAYOUT FIXO
           =============================================== */
        :root {{
            /* Cores */
            --primary: {COLORS['primary']};
            --secondary: {COLORS['secondary']};
            --accent: {COLORS['accent']};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --danger: {COLORS['danger']};
            --bg-dark: {COLORS['bg_dark']};
            --bg-card: {COLORS['bg_card']};
            --text-primary: {COLORS['text_primary']};
            --text-secondary: {COLORS['text_secondary']};
            --border: {COLORS['border']};
            
            /* LAYOUT FIXO - Dimensões fixas */
            --sidebar-width: 280px;
            --content-max-width: 1400px;
            --card-min-height: 140px;
            --button-height: 44px;
            --input-height: 44px;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        /* ===============================================
           FUNDO
           =============================================== */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #0F0F23 0%, #1a1a3e 50%, #0F0F23 100%);
            background-attachment: fixed;
        }}
        
        [data-testid="stAppViewContainer"]::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 30%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(6, 182, 212, 0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}
        
        /* ===============================================
           CONTEÚDO - LARGURA MÁXIMA FIXA
           =============================================== */
        
        /* Container principal que envolve tudo */
        .appview-container {{
            display: flex !important;
            flex-direction: row !important;
        }}
        
        /* Área de conteúdo */
        .main {{
            background: transparent;
            max-width: var(--content-max-width) !important;
            margin: 0 auto !important;
            padding: 2rem 1.5rem !important;
            flex: 1 !important;
        }}
        
        .block-container {{
            max-width: var(--content-max-width) !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            margin: 0 auto !important;
        }}
        
        /* ===============================================
           SIDEBAR - LARGURA FIXA (NÃO EXPANDE)
           =============================================== */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, 
                rgba(15, 15, 35, 0.95) 0%, 
                rgba(26, 26, 62, 0.95) 100%
            ) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border-right: 1px solid rgba(139, 92, 246, 0.15) !important;
            box-shadow: 4px 0 30px rgba(0, 0, 0, 0.3) !important;
            width: var(--sidebar-width) !important;
            min-width: var(--sidebar-width) !important;
            max-width: var(--sidebar-width) !important;
            flex-shrink: 0 !important;
            position: relative !important;
        }}
        
        [data-testid="stSidebar"] > div:first-child {{
            width: var(--sidebar-width) !important;
            min-width: var(--sidebar-width) !important;
            max-width: var(--sidebar-width) !important;
        }}
        
        /* Garantir que o container interno também seja fixo */
        [data-testid="stSidebar"] .css-1d391kg,
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
            width: var(--sidebar-width) !important;
            min-width: var(--sidebar-width) !important;
            max-width: var(--sidebar-width) !important;
        }}
        
        /* Desabilitar transições de width */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] * {{
            transition: none !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
            color: {COLORS['text_primary']};
        }}
        
        /* ===============================================
           GRID - ALTURA CONSISTENTE
           =============================================== */
        [data-testid="column"] {{
            padding: 0.5rem !important;
        }}
        
        [data-testid="column"] > div > div {{
            min-height: var(--card-min-height);
            height: 100%;
        }}
        
        /* ===============================================
           CARDS
           =============================================== */
        .stCard {{
            background: {COLORS['bg_card']};
            backdrop-filter: blur(20px);
            border: 1px solid {COLORS['border']};
            border-radius: 16px;
            padding: 1.25rem !important;
            transition: all 0.3s ease;
            min-height: var(--card-min-height);
            height: 100%;
        }}
        
        .stCard:hover {{
            border-color: rgba(139, 92, 246, 0.4);
            box-shadow: 0 8px 32px rgba(139, 92, 246, 0.15);
            transform: translateY(-2px);
        }}
        
        /* ===============================================
           BOTÕES
           =============================================== */
        .stButton > button {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.75rem 1.75rem !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
            cursor: pointer !important;
            min-height: var(--button-height) !important;
            width: 100% !important;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 25px rgba(139, 92, 246, 0.4) !important;
        }}
        
        .stButton > button[kind="secondary"] {{
            background: rgba(139, 92, 246, 0.1) !important;
            color: {COLORS['primary']} !important;
            border: 1px solid {COLORS['primary']} !important;
            box-shadow: none !important;
        }}
        
        /* ===============================================
           INPUTS
           =============================================== */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {{
            background: rgba(15, 15, 35, 0.6) !important;
            border: 1px solid rgba(139, 92, 246, 0.2) !important;
            border-radius: 10px !important;
            color: {COLORS['text_primary']} !important;
            padding: 0.625rem 0.875rem !important;
            transition: all 0.3s ease !important;
            min-height: var(--input-height) !important;
            font-size: 14px !important;
        }}
        
        .stTextArea > div > div > textarea {{
            background: rgba(15, 15, 35, 0.6) !important;
            border: 1px solid rgba(139, 92, 246, 0.2) !important;
            border-radius: 10px !important;
            color: {COLORS['text_primary']} !important;
            padding: 0.625rem 0.875rem !important;
            transition: all 0.3s ease !important;
            min-height: 100px !important;
            font-size: 14px !important;
        }}
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stSelectbox > div > div > select:focus {{
            border-color: {COLORS['primary']} !important;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15) !important;
            outline: none !important;
        }}
        
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {{
            color: {COLORS['text_secondary']} !important;
            opacity: 0.6 !important;
        }}
        
        /* ===============================================
           TABS
           =============================================== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px !important;
            background: rgba(15, 15, 35, 0.3) !important;
            padding: 6px !important;
            border-radius: 12px !important;
            min-height: 48px !important;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background: transparent !important;
            border: none !important;
            border-radius: 8px !important;
            color: {COLORS['text_secondary']} !important;
            padding: 0.625rem 1.25rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            min-height: 36px !important;
        }}
        
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(139, 92, 246, 0.1) !important;
            color: {COLORS['primary']} !important;
        }}
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
            color: white !important;
        }}
        
        /* ===============================================
           EXPANDERS
           =============================================== */
        .streamlit-expanderHeader {{
            background: rgba(139, 92, 246, 0.08) !important;
            border: 1px solid rgba(139, 92, 246, 0.15) !important;
            border-radius: 10px !important;
            color: {COLORS['text_primary']} !important;
            font-weight: 600 !important;
            padding: 0.75rem 1rem !important;
            transition: all 0.3s ease !important;
            min-height: 48px !important;
        }}
        
        .streamlit-expanderHeader:hover {{
            background: rgba(139, 92, 246, 0.12) !important;
            border-color: rgba(139, 92, 246, 0.3) !important;
        }}
        
        /* ===============================================
           MÉTRICAS
           =============================================== */
        [data-testid="stMetricValue"] {{
            font-size: 2rem !important;
            font-weight: 800 !important;
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.2 !important;
        }}
        
        [data-testid="stMetricLabel"] {{
            color: {COLORS['text_secondary']} !important;
            font-size: 0.75rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            font-weight: 600 !important;
            margin-bottom: 0.5rem !important;
        }}
        
        /* ===============================================
           TABELAS
           =============================================== */
        .dataframe {{
            background: {COLORS['bg_card']} !important;
            border: 1px solid {COLORS['border']} !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            width: 100% !important;
        }}
        
        .dataframe thead tr th {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
            color: white !important;
            font-weight: 700 !important;
            padding: 0.875rem !important;
            border: none !important;
            font-size: 14px !important;
        }}
        
        .dataframe tbody tr {{
            border-bottom: 1px solid rgba(139, 92, 246, 0.1) !important;
            transition: all 0.2s ease !important;
        }}
        
        .dataframe tbody tr:hover {{
            background: rgba(139, 92, 246, 0.05) !important;
        }}
        
        .dataframe tbody tr td {{
            padding: 0.75rem !important;
            color: {COLORS['text_primary']} !important;
            font-size: 14px !important;
        }}
        
        /* ===============================================
           PROGRESS BAR
           =============================================== */
        .stProgress > div > div > div {{
            background: linear-gradient(90deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
            border-radius: 10px !important;
            min-height: 8px !important;
        }}
        
        .stProgress > div > div {{
            background: rgba(139, 92, 246, 0.1) !important;
            border-radius: 10px !important;
            min-height: 8px !important;
        }}
        
        /* ===============================================
           ALERTS
           =============================================== */
        .stSuccess, .stInfo, .stWarning, .stError {{
            border-radius: 12px !important;
            border-left-width: 4px !important;
            padding: 1rem !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            margin: 0.5rem 0 !important;
            font-size: 14px !important;
        }}
        
        .stSuccess {{
            background: rgba(16, 185, 129, 0.1) !important;
            border-left-color: {COLORS['success']} !important;
            color: {COLORS['success']} !important;
        }}
        
        .stInfo {{
            background: rgba(6, 182, 212, 0.1) !important;
            border-left-color: {COLORS['secondary']} !important;
            color: {COLORS['secondary']} !important;
        }}
        
        .stWarning {{
            background: rgba(245, 158, 11, 0.1) !important;
            border-left-color: {COLORS['warning']} !important;
            color: {COLORS['warning']} !important;
        }}
        
        .stError {{
            background: rgba(239, 68, 68, 0.1) !important;
            border-left-color: {COLORS['danger']} !important;
            color: {COLORS['danger']} !important;
        }}
        
        /* ===============================================
           SCROLLBAR
           =============================================== */
        ::-webkit-scrollbar {{
            width: 10px !important;
            height: 10px !important;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(15, 15, 35, 0.3) !important;
            border-radius: 10px !important;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%) !important;
            border-radius: 10px !important;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, {COLORS['secondary']} 0%, {COLORS['primary']} 100%) !important;
        }}
        
        /* ===============================================
           ANIMAÇÕES
           =============================================== */
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .animate-fade-in {{
            animation: fadeIn 0.5s ease-out;
        }}
        
        /* ===============================================
           RESPONSIVIDADE
           =============================================== */
        @media (max-width: 1400px) {{
            :root {{ --content-max-width: 1200px; }}
        }}
        
        @media (max-width: 1024px) {{
            :root {{ 
                --content-max-width: 960px;
                --sidebar-width: 240px;
            }}
            
            [data-testid="stMetricValue"] {{
                font-size: 1.75rem !important;
            }}
        }}
        
        @media (max-width: 768px) {{
            :root {{
                --sidebar-width: 220px;
                --card-min-height: 120px;
                --button-height: 40px;
                --input-height: 40px;
            }}
            
            .stButton > button {{
                padding: 0.625rem 1.25rem !important;
                font-size: 13px !important;
            }}
            
            [data-testid="stMetricValue"] {{
                font-size: 1.5rem !important;
            }}
            
            .main {{
                padding: 1rem !important;
            }}
            
            .block-container {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }}
        }}
        
        @media (max-width: 480px) {{
            :root {{
                --sidebar-width: 100%;
                --card-min-height: 100px;
            }}
            
            .stButton > button {{
                padding: 0.5rem 1rem !important;
                font-size: 12px !important;
            }}
            
            [data-testid="stMetricValue"] {{
                font-size: 1.25rem !important;
            }}
        }}
        
        /* ===============================================
           HIDE STREAMLIT BRANDING
           =============================================== */
        #MainMenu {{visibility: hidden !important;}}
        footer {{visibility: hidden !important;}}
        header {{visibility: hidden !important;}}
        .stDeployButton {{display: none !important;}}
        </style>
    """, unsafe_allow_html=True)
