"""
auth.py - Módulo de Autenticação
Versão RENOVADA com persistência de sessão
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional
import re
import time


class AuthManager:
    """Gerenciador de autenticação com Supabase"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self._init_session()
    
    def _init_session(self):
        """Inicializa e restaura sessão - CORRIGIDO PARA PERSISTIR NO F5"""
        
        # SEMPRE tentar restaurar sessão do Supabase primeiro
        try:
            session = self.supabase.auth.get_session()
            if session and session.user:
                # Atualizar session_state com dados do Supabase
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                return  # Sessão restaurada com sucesso
        except Exception as e:
            # Se falhar, continua para valores padrão
            pass
        
        # Se não conseguiu restaurar, inicializar valores padrão
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
        """Verifica se usuário está autenticado"""
        # Verificar tanto session_state quanto Supabase
        if st.session_state.get('authenticated', False):
            return True
        
        # Double-check com Supabase
        try:
            session = self.supabase.auth.get_session()
            if session and session.user:
                # Restaurar session_state
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                return True
        except:
            pass
        
        return False
    
    def get_user_id(self) -> Optional[str]:
        """Retorna ID do usuário"""
        return st.session_state.get('user_id')
    
    def get_user_email(self) -> Optional[str]:
        """Retorna email do usuário"""
        return st.session_state.get('user_email', 'Usuário')
    
    def get_user_name(self) -> str:
        """Retorna nome do usuário"""
        return st.session_state.get('user_name', 'Usuário')
    
    def login(self, email: str, password: str) -> Dict:
        """Realiza login"""
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
                
                return {
                    'success': True,
                    'message': 'Login realizado com sucesso!'
                }
            
            return {
                'success': False,
                'message': 'Credenciais inválidas'
            }
            
        except Exception as e:
            st.session_state.login_attempts = st.session_state.get('login_attempts', 0) + 1
            return {
                'success': False,
                'message': f'Erro ao fazer login: {str(e)}'
            }
    
    def signup(self, email: str, password: str) -> Dict:
        """Registra novo usuário"""
        try:
            # Validar email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {
                    'success': False,
                    'message': 'Email inválido'
                }
            
            # Validar senha
            if len(password) < 6:
                return {
                    'success': False,
                    'message': 'Senha deve ter no mínimo 6 caracteres'
                }
            
            # Criar usuário
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {
                    'success': True,
                    'message': 'Conta criada! Faça login para continuar.'
                }
            
            return {
                'success': False,
                'message': 'Erro ao criar conta'
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'already registered' in error_msg or 'already exists' in error_msg:
                return {
                    'success': False,
                    'message': 'Este email já está cadastrado'
                }
            return {
                'success': False,
                'message': f'Erro ao criar conta: {str(e)}'
            }
    
    def logout(self) -> Dict:
        """Realiza logout"""
        try:
            self.supabase.auth.sign_out()
        except Exception:
            pass
        
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.session_state.login_attempts = 0
        
        return {
            'success': True,
            'message': 'Logout realizado com sucesso'
        }
    
    def render_login_page(self):
        """Renderiza página de login RENOVADA - Design Moderno"""
        
        # CSS Moderno
        st.markdown("""
        <style>
        /* Reset e Base */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Container Principal */
        .login-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 48px;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.5s ease-out;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Header */
        .login-header {
            text-align: center;
            margin-bottom: 32px;
        }
        
        .login-logo {
            font-size: 64px;
            margin-bottom: 16px;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.05);
            }
        }
        
        .login-title {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -0.5px;
        }
        
        .login-subtitle {
            color: #64748b;
            font-size: 15px;
            margin-top: 8px;
            font-weight: 500;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f1f5f9;
            border-radius: 12px;
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            color: #64748b;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        /* Inputs */
        .stTextInput input {
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            padding: 14px 16px;
            font-size: 15px;
            transition: all 0.3s ease;
            background: white;
        }
        
        .stTextInput input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Botões */
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 14px 24px;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        .stButton button:active {
            transform: translateY(0);
        }
        
        /* Checkbox */
        .stCheckbox {
            margin-top: 12px;
        }
        
        /* Mensagens */
        .stAlert {
            border-radius: 12px;
            border: none;
            padding: 12px 16px;
            font-size: 14px;
        }
        
        /* Footer */
        .login-footer {
            text-align: center;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 13px;
        }
        
        .login-footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        
        /* Responsivo */
        @media (max-width: 640px) {
            .login-container {
                padding: 32px 24px;
            }
            
            .login-title {
                font-size: 28px;
            }
        }
        
        /* Esconder elementos do Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
        
        # HTML da página
        st.markdown("""
        <div class="login-wrapper">
            <div class="login-container">
                <div class="login-header">
                    <div class="login-logo">📚</div>
                    <h1 class="login-title">MonitorPro</h1>
                    <p class="login-subtitle">Sistema Inteligente de Estudos</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs com formulários
        tab1, tab2 = st.tabs(["🔐 Login", "✨ Criar Conta"])
        
        # ============== TAB LOGIN ==============
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input(
                    "📧 Email",
                    placeholder="seu@email.com",
                    key="login_email"
                )
                
                password = st.text_input(
                    "🔒 Senha",
                    type="password",
                    placeholder="••••••••",
                    key="login_password"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    remember = st.checkbox("Lembrar-me", value=True)
                
                with col2:
                    st.markdown(
                        '<p style="text-align: right; font-size: 13px;">'
                        '<a href="#" style="color: #667eea;">Esqueceu a senha?</a></p>',
                        unsafe_allow_html=True
                    )
                
                submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
                
                if submit:
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
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("signup_form", clear_on_submit=True):
                email = st.text_input(
                    "📧 Email",
                    placeholder="seu@email.com",
                    key="signup_email"
                )
                
                password = st.text_input(
                    "🔒 Senha",
                    type="password",
                    placeholder="Mínimo 6 caracteres",
                    key="signup_password",
                    help="Use uma senha forte com letras e números"
                )
                
                password2 = st.text_input(
                    "🔒 Confirmar Senha",
                    type="password",
                    placeholder="Digite a senha novamente",
                    key="signup_password2"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                terms = st.checkbox(
                    "Li e aceito os termos de uso e política de privacidade",
                    key="terms"
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                submit = st.form_submit_button("✨ Criar Conta", use_container_width=True)
                
                if submit:
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
                                st.info("💡 Agora você pode fazer login na aba ao lado!")
                            else:
                                st.error("❌ " + result['message'])
        
        # Footer
        st.markdown("""
        <div class="login-footer">
            <p>© 2026 MonitorPro • Desenvolvido com ❤️</p>
            <p style="margin-top: 8px;">
                <a href="#">Suporte</a> • 
                <a href="#">Privacidade</a> • 
                <a href="#">Termos</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
