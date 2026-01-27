"""
auth.py - Módulo de Autenticação
Versão CORRIGIDA - Centralizado + Senha visível + Persistência real
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
        """Inicializa e restaura sessão - CORRIGIDO para persistir no F5"""
        
        # CRÍTICO: Sempre verificar Supabase ANTES de inicializar valores padrão
        try:
            session = self.supabase.auth.get_session()
            
            # Se existe sessão válida no Supabase
            if session and hasattr(session, 'user') and session.user:
                # Forçar atualização do session_state
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                st.session_state['login_attempts'] = 0
                return  # Sair da função - sessão restaurada!
        except Exception as e:
            # Se der erro, continuar para valores padrão
            pass
        
        # Só inicializar valores padrão se NÃO tem sessão no Supabase
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
        """Verifica se usuário está autenticado - COM VERIFICAÇÃO DUPLA"""
        
        # Primeiro: verificar session_state
        if st.session_state.get('authenticated', False):
            return True
        
        # Segundo: verificar direto no Supabase (caso F5)
        try:
            session = self.supabase.auth.get_session()
            if session and hasattr(session, 'user') and session.user:
                # Restaurar session_state
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                return True
        except Exception:
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
        """Renderiza página de login - VERSÃO CORRIGIDA"""
        
        # CSS CORRIGIDO - Centralizado e campo de senha ESCURO
        st.markdown("""
        <style>
        /* IMPORTANTE: Esconder elementos padrão do Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* Background gradiente */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        }
        
        /* CORREÇÃO 1: Centralização vertical e horizontal */
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }
        
        /* Container de login centralizado */
        .login-box {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 420px;
            margin: 10vh auto;
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
            margin-bottom: 30px;
        }
        
        .login-logo {
            font-size: 56px;
            margin-bottom: 12px;
        }
        
        .login-title {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 8px 0;
        }
        
        .login-subtitle {
            color: #64748b;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f1f5f9;
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 24px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            color: #64748b;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        /* CORREÇÃO 2: Inputs com texto ESCURO e visível */
        .stTextInput > div > div > input {
            border-radius: 10px !important;
            border: 2px solid #e2e8f0 !important;
            padding: 12px 14px !important;
            font-size: 15px !important;
            background: white !important;
            color: #1e293b !important; /* TEXTO ESCURO */
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input::placeholder {
            color: #94a3b8 !important; /* Placeholder cinza claro */
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
            background: white !important;
            color: #1e293b !important; /* TEXTO ESCURO no foco também */
        }
        
        /* Labels dos inputs */
        .stTextInput > label {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-bottom: 6px !important;
        }
        
        /* Botões */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 24px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            width: 100%;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* Checkbox */
        .stCheckbox {
            margin: 12px 0;
        }
        
        .stCheckbox > label {
            font-size: 13px !important;
            color: #475569 !important;
        }
        
        /* Mensagens */
        .stAlert {
            border-radius: 10px !important;
            border: none !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            margin-top: 12px !important;
        }
        
        /* Footer */
        .login-footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 12px;
        }
        
        /* Responsivo */
        @media (max-width: 640px) {
            .login-box {
                margin: 5vh 20px;
                padding: 30px 20px;
            }
            
            .login-title {
                font-size: 24px;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Container de login
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="login-header">
            <div class="login-logo">📚</div>
            <h1 class="login-title">MonitorPro</h1>
            <p class="login-subtitle">Sistema Inteligente de Estudos</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs
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
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    remember = st.checkbox("Lembrar-me", value=True)
                
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
                
                terms = st.checkbox("Aceito os termos de uso")
                
                submit = st.form_submit_button("✨ Criar Conta", use_container_width=True)
                
                if submit:
                    if not terms:
                        st.warning("⚠️ Aceite os termos de uso")
                    elif not email or not password:
                        st.warning("⚠️ Preencha todos os campos")
                    elif password != password2:
                        st.error("❌ As senhas não coincidem")
                    elif len(password) < 6:
                        st.error("❌ Senha deve ter no mínimo 6 caracteres")
                    else:
                        with st.spinner("Criando conta..."):
                            result = self.signup(email, password)
                            
                            if result['success']:
                                st.success("✅ " + result['message'])
                                st.info("💡 Faça login na aba ao lado!")
                            else:
                                st.error("❌ " + result['message'])
        
        # Footer
        st.markdown("""
        <div class="login-footer">
            © 2026 MonitorPro • Desenvolvido com ❤️
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
