"""
auth.py - Módulo de Autenticação
Versão simplificada e garantida
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional
import re


class AuthManager:
    """Gerenciador de autenticação com Supabase"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self._init_session()
    
    def _init_session(self):
        """Inicializa e restaura sessão"""
        # Tentar restaurar sessão do Supabase
        if not st.session_state.get('authenticated', False):
            try:
                session = self.supabase.auth.get_session()
                if session and session.user:
                    st.session_state['authenticated'] = True
                    st.session_state['user_id'] = session.user.id
                    st.session_state['user_email'] = session.user.email
                    st.session_state['user_name'] = session.user.email.split('@')[0]
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
        return st.session_state.get('authenticated', False)
    
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
        """Renderiza página de login"""
        st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.title("🔐 MonitorPro")
        st.markdown("Sistema de Monitoramento de Estudos")
        
        tab1, tab2 = st.tabs(["Login", "Criar Conta"])
        
        # Tab Login
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Senha", type="password", key="login_password")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    if email and password:
                        result = self.login(email, password)
                        if result['success']:
                            st.success(result['message'])
                            st.rerun()
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("Preencha todos os campos")
        
        # Tab Cadastro
        with tab2:
            with st.form("signup_form"):
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Senha (mín. 6 caracteres)", type="password", key="signup_password")
                password2 = st.text_input("Confirmar senha", type="password", key="signup_password2")
                terms = st.checkbox("Aceito os termos de uso")
                submit = st.form_submit_button("Criar Conta", use_container_width=True)
                
                if submit:
                    if not terms:
                        st.warning("Você deve aceitar os termos de uso")
                    elif password != password2:
                        st.error("As senhas não coincidem")
                    elif email and password:
                        result = self.signup(email, password)
                        if result['success']:
                            st.success(result['message'])
                            st.info("Você pode fazer login agora!")
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("Preencha todos os campos")
        
        st.markdown('</div>', unsafe_allow_html=True)
