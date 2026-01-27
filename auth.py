"""
auth.py - Módulo de Autenticação
Versão FINAL - Layout corrigido e funcional
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
        """Inicializa e restaura sessão"""
        # SEMPRE verificar Supabase primeiro
        try:
            session = self.supabase.auth.get_session()
            if session and hasattr(session, 'user') and session.user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session.user.id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_name'] = session.user.email.split('@')[0]
                st.session_state['login_attempts'] = 0
                return
        except Exception:
            pass
        
        # Valores padrão
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
        if st.session_state.get('authenticated', False):
            return True
        
        # Double-check com Supabase
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
                
                return {'success': True, 'message': 'Login realizado com sucesso!'}
            
            return {'success': False, 'message': 'Credenciais inválidas'}
            
        except Exception as e:
            st.session_state.login_attempts = st.session_state.get('login_attempts', 0) + 1
            return {'success': False, 'message': f'Erro ao fazer login: {str(e)}'}
    
    def signup(self, email: str, password: str) -> Dict:
        """Registra novo usuário"""
        try:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {'success': False, 'message': 'Email inválido'}
            
            if len(password) < 6:
                return {'success': False, 'message': 'Senha deve ter no mínimo 6 caracteres'}
            
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {'success': True, 'message': 'Conta criada! Faça login para continuar.'}
            
            return {'success': False, 'message': 'Erro ao criar conta'}
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'already registered' in error_msg or 'already exists' in error_msg:
                return {'success': False, 'message': 'Este email já está cadastrado'}
            return {'success': False, 'message': f'Erro ao criar conta: {str(e)}'}
    
    def logout(self) -> Dict:
        """Realiza logout"""
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
        """Renderiza página de login - VERSÃO FINAL CORRIGIDA"""
        
        # Esconder elementos do Streamlit
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        </style>
        """, unsafe_allow_html=True)
        
        # CSS Principal
        st.markdown("""
        <style>
        /* Background */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Resetar padding padrão */
        .block-container {
            padding: 0 !important;
            max-width: none !important;
        }
        
        /* Inputs - TEXTO ESCURO E VISÍVEL */
        input {
            color: #1e293b !important;
            background-color: #ffffff !important;
        }
        
        input::placeholder {
            color: #94a3b8 !important;
        }
        
        input:focus {
            color: #1e293b !important;
            background-color: #ffffff !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Criar layout centralizado
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Espaçamento superior
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            
            # Card de Login
            st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.98);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            ">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 56px; margin-bottom: 10px;">📚</div>
                    <h1 style="
                        font-size: 32px;
                        font-weight: 800;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        margin: 0;
                    ">MonitorPro</h1>
                    <p style="color: #64748b; font-size: 14px; margin-top: 5px;">Sistema Inteligente de Estudos</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Tabs
            tab1, tab2 = st.tabs(["🔐 Entrar", "✨ Cadastrar"])
            
            # ============== TAB LOGIN ==============
            with tab1:
                with st.form("login_form", clear_on_submit=False):
                    st.text_input(
                        "📧 Email",
                        placeholder="seu@email.com",
                        key="login_email"
                    )
                    
                    st.text_input(
                        "🔒 Senha",
                        type="password",
                        placeholder="Digite sua senha",
                        key="login_password"
                    )
                    
                    st.checkbox("Lembrar-me", value=True)
                    
                    submitted = st.form_submit_button(
                        "🚀 Entrar",
                        use_container_width=True
                    )
                    
                    if submitted:
                        email = st.session_state.login_email
                        password = st.session_state.login_password
                        
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
                    st.text_input(
                        "📧 Email",
                        placeholder="seu@email.com",
                        key="signup_email"
                    )
                    
                    st.text_input(
                        "🔒 Senha",
                        type="password",
                        placeholder="Mínimo 6 caracteres",
                        key="signup_password"
                    )
                    
                    st.text_input(
                        "🔒 Confirmar Senha",
                        type="password",
                        placeholder="Digite novamente",
                        key="signup_password2"
                    )
                    
                    terms = st.checkbox("Aceito os termos de uso")
                    
                    submitted = st.form_submit_button(
                        "✨ Criar Conta",
                        use_container_width=True
                    )
                    
                    if submitted:
                        email = st.session_state.signup_email
                        password = st.session_state.signup_password
                        password2 = st.session_state.signup_password2
                        
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
            <div style="text-align: center; margin-top: 30px; color: rgba(255,255,255,0.7); font-size: 12px;">
                © 2026 MonitorPro • Desenvolvido com ❤️
            </div>
            """, unsafe_allow_html=True)
