"""
auth.py - Módulo de Autenticação
VERSÃO PROFISSIONAL COMPLETA
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional
import re
import time


class AuthManager:
    """Gerenciador de autenticação com Supabase - VERSÃO PROFISSIONAL"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self._init_session()
    
    def _init_session(self):
        """Inicializa e restaura sessão - SEMPRE verifica Supabase primeiro"""
        try:
            session = self.supabase.auth.get_session()
            if session and hasattr(session, 'user') and session.user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                st.session_state['login_attempts'] = 0
                return
        except:
            pass
        
        defaults = {
            'authenticated': False,
            'user_id': None,
            'user_email': None,
            'user_name': None,
            'login_attempts': 0
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def is_authenticated(self) -> bool:
        """Verifica autenticação com double-check no Supabase"""
        if st.session_state.get('authenticated', False):
            return True
        
        try:
            session = self.supabase.auth.get_session()
            if session and hasattr(session, 'user') and session.user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                return True
        except:
            pass
        
        return False
    
    def get_user_id(self) -> Optional[str]:
        return st.session_state.get('user_id')
    
    def get_user_email(self) -> Optional[str]:
        return st.session_state.get('user_email', 'Usuário')
    
    def get_user_name(self) -> str:
        return st.session_state.get('user_name', 'Usuário')
    
    def login(self, email: str, password: str) -> Dict:
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                st.session_state.authenticated = True
                st.session_state.user_id = response.user.id
                st.session_state.user_email = response.user.email
                st.session_state.user_name = response.user.email.split('@')[0]
                st.session_state.login_attempts = 0
                return {'success': True, 'message': 'Login realizado com sucesso!'}
            
            return {'success': False, 'message': 'Credenciais inválidas'}
        except Exception as e:
            st.session_state.login_attempts = st.session_state.get('login_attempts', 0) + 1
            return {'success': False, 'message': f'Erro ao fazer login: {str(e)}'}
    
    def signup(self, email: str, password: str) -> Dict:
        try:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {'success': False, 'message': 'Email inválido'}
            
            if len(password) < 6:
                return {'success': False, 'message': 'Senha deve ter no mínimo 6 caracteres'}
            
            response = self.supabase.auth.sign_up({"email": email, "password": password})
            
            if response.user:
                return {'success': True, 'message': 'Conta criada! Faça login para continuar.'}
            
            return {'success': False, 'message': 'Erro ao criar conta'}
        except Exception as e:
            if 'already registered' in str(e).lower():
                return {'success': False, 'message': 'Este email já está cadastrado'}
            return {'success': False, 'message': f'Erro ao criar conta: {str(e)}'}
    
    def logout(self) -> Dict:
        try:
            self.supabase.auth.sign_out()
        except:
            pass
        
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.session_state.login_attempts = 0
        
        return {'success': True, 'message': 'Logout realizado com sucesso'}
    
    def render_login_page(self):
        """Renderiza página de login PROFISSIONAL"""
        
        # CONFIGURAÇÃO DA PÁGINA - IMPORTANTE!
        st.set_page_config(
            page_title="MonitorPro - Login",
            page_icon="📚",
            layout="centered",
            initial_sidebar_state="collapsed"  # SIDEBAR OCULTA!
        )
        
        # CSS PROFISSIONAL COMPLETO
        st.markdown("""
        <style>
        /* ========================================
           ESCONDER ELEMENTOS STREAMLIT
           ======================================== */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* ESCONDER SIDEBAR COMPLETAMENTE */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        
        .css-1d391kg {
            display: none !important;
        }
        
        /* Remover botão de abrir sidebar */
        button[kind="header"] {
            display: none !important;
        }
        
        /* ========================================
           BACKGROUND E LAYOUT PRINCIPAL
           ======================================== */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .block-container {
            padding: 0 !important;
            max-width: none !important;
        }
        
        /* ========================================
           CONTAINER DE LOGIN
           ======================================== */
        .login-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-card {
            background: white;
            border-radius: 24px;
            padding: 48px;
            width: 100%;
            max-width: 450px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            animation: fadeInUp 0.6s ease-out;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* ========================================
           HEADER DO LOGIN
           ======================================== */
        .login-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .login-icon {
            font-size: 64px;
            margin-bottom: 16px;
            display: inline-block;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .login-title {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 8px 0;
            letter-spacing: -1px;
        }
        
        .login-subtitle {
            color: #64748b;
            font-size: 15px;
            font-weight: 500;
        }
        
        /* ========================================
           TABS
           ======================================== */
        .stTabs {
            margin-bottom: 24px;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f1f5f9;
            border-radius: 12px;
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 48px;
            border-radius: 10px;
            padding: 0 24px;
            font-weight: 600;
            color: #64748b;
            background-color: transparent;
            border: none;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 24px;
        }
        
        /* ========================================
           INPUTS - TEXTO VISÍVEL E ESCURO
           ======================================== */
        .stTextInput label {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #1e293b !important;
            margin-bottom: 8px !important;
        }
        
        .stTextInput input {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput input::placeholder {
            color: #94a3b8 !important;
        }
        
        .stTextInput input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
            background-color: #ffffff !important;
            color: #1e293b !important;
        }
        
        /* ========================================
           CHECKBOX
           ======================================== */
        .stCheckbox {
            margin: 16px 0;
        }
        
        .stCheckbox label {
            font-size: 14px !important;
            color: #475569 !important;
            font-weight: 500 !important;
        }
        
        /* ========================================
           BOTÕES
           ======================================== */
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 14px 24px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
            cursor: pointer !important;
        }
        
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
        }
        
        .stButton button:active {
            transform: translateY(0) !important;
        }
        
        /* ========================================
           MENSAGENS (SUCCESS, ERROR, WARNING)
           ======================================== */
        .stAlert {
            border-radius: 12px !important;
            border: none !important;
            padding: 14px 16px !important;
            font-size: 14px !important;
            margin-top: 16px !important;
        }
        
        /* ========================================
           FOOTER
           ======================================== */
        .login-footer {
            text-align: center;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 13px;
        }
        
        /* ========================================
           RESPONSIVO
           ======================================== */
        @media (max-width: 640px) {
            .login-card {
                padding: 32px 24px;
            }
            
            .login-title {
                font-size: 28px;
            }
            
            .login-icon {
                font-size: 48px;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # HTML ESTRUTURA
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        # HEADER
        st.markdown("""
        <div class="login-header">
            <div class="login-icon">📚</div>
            <h1 class="login-title">MonitorPro</h1>
            <p class="login-subtitle">Sistema Inteligente de Estudos</p>
        </div>
        """, unsafe_allow_html=True)
        
        # TABS
        tab1, tab2 = st.tabs(["🔐 Entrar", "✨ Cadastrar"])
        
        # ============== TAB LOGIN ==============
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input(
                    "Email",
                    placeholder="seu@email.com",
                    key="login_email"
                )
                
                password = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Digite sua senha",
                    key="login_password"
                )
                
                st.checkbox("Lembrar-me", value=True, key="remember_me")
                
                submitted = st.form_submit_button("Entrar", use_container_width=True)
                
                if submitted:
                    if email and password:
                        with st.spinner("Autenticando..."):
                            result = self.login(email, password)
                            
                            if result['success']:
                                st.success("✅ " + result['message'])
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ " + result['message'])
                    else:
                        st.warning("⚠️ Preencha todos os campos")
        
        # ============== TAB CADASTRO ==============
        with tab2:
            with st.form("signup_form", clear_on_submit=True):
                email = st.text_input(
                    "Email",
                    placeholder="seu@email.com",
                    key="signup_email"
                )
                
                password = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Mínimo 6 caracteres",
                    key="signup_password"
                )
                
                password2 = st.text_input(
                    "Confirmar Senha",
                    type="password",
                    placeholder="Digite novamente",
                    key="signup_password2"
                )
                
                terms = st.checkbox("Aceito os termos de uso e política de privacidade")
                
                submitted = st.form_submit_button("Criar Conta", use_container_width=True)
                
                if submitted:
                    if not terms:
                        st.warning("⚠️ Você deve aceitar os termos de uso")
                    elif not email or not password:
                        st.warning("⚠️ Preencha todos os campos")
                    elif password != password2:
                        st.error("❌ As senhas não coincidem")
                    elif len(password) < 6:
                        st.error("❌ A senha deve ter no mínimo 6 caracteres")
                    else:
                        with st.spinner("Criando sua conta..."):
                            result = self.signup(email, password)
                            
                            if result['success']:
                                st.success("✅ " + result['message'])
                                st.info("💡 Agora você pode fazer login na aba 'Entrar'!")
                            else:
                                st.error("❌ " + result['message'])
        
        # FOOTER
        st.markdown("""
        <div class="login-footer">
            <p>© 2026 MonitorPro • Desenvolvido com ❤️</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
