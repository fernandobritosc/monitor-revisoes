"""
auth.py - Módulo de Autenticação
Versão simplificada e garantida
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional, Tuple
import re


class AuthManager:
    """Gerenciador de autenticação com Supabase"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self._init_session()
    
    def _init_session(self):
        """Inicializa e restaura sessão"""
        # Limpar estado de autenticação inicialmente
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
        
        # Tentar restaurar sessão do Supabase
        if not st.session_state['authenticated']:
            try:
                session = self.supabase.auth.get_session()
                if session and session.user:
                    self._update_session_state(session.user)
            except Exception as e:
                st.error(f"Erro ao restaurar sessão: {str(e)}")
    
    def _update_session_state(self, user):
        """Atualiza o estado da sessão com dados do usuário"""
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = user.id
        st.session_state['user_email'] = user.email
        st.session_state['user_name'] = user.email.split('@')[0]
        st.session_state['login_attempts'] = 0
    
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
            # Validação básica
            if not email or not password:
                return {
                    'success': False,
                    'message': 'Email e senha são obrigatórios'
                }
            
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                self._update_session_state(response.user)
                
                return {
                    'success': True,
                    'message': 'Login realizado com sucesso!',
                    'user': response.user
                }
            
            return {
                'success': False,
                'message': 'Credenciais inválidas'
            }
            
        except Exception as e:
            st.session_state.login_attempts = st.session_state.get('login_attempts', 0) + 1
            
            # Tratamento de erros específicos
            error_msg = str(e).lower()
            if 'invalid login credentials' in error_msg:
                return {
                    'success': False,
                    'message': 'Email ou senha incorretos'
                }
            elif 'email not confirmed' in error_msg:
                return {
                    'success': False,
                    'message': 'Confirme seu email antes de fazer login'
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro ao fazer login: {str(e)}'
                }
    
    def signup(self, email: str, password: str) -> Dict:
        """Registra novo usuário"""
        try:
            # Validar email
            if not email or not password:
                return {
                    'success': False,
                    'message': 'Email e senha são obrigatórios'
                }
            
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {
                    'success': False,
                    'message': 'Formato de email inválido'
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
                "password": password,
                "options": {
                    "email_redirect_to": "http://localhost:8501"  # Ajuste conforme sua URL
                }
            })
            
            if response.user:
                return {
                    'success': True,
                    'message': 'Conta criada com sucesso! Verifique seu email para confirmar.',
                    'user': response.user
                }
            elif response:
                return {
                    'success': True,
                    'message': 'Conta criada! Verifique seu email para confirmar.'
                }
            
            return {
                'success': False,
                'message': 'Erro ao criar conta'
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'already registered' in error_msg or 'already exists' in error_msg or 'user already exists' in error_msg:
                return {
                    'success': False,
                    'message': 'Este email já está cadastrado'
                }
            elif 'password should be at least' in error_msg:
                return {
                    'success': False,
                    'message': 'Senha muito curta'
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro ao criar conta: {str(e)}'
                }
    
    def logout(self) -> Dict:
        """Realiza logout"""
        try:
            self.supabase.auth.sign_out()
        except Exception as e:
            st.warning(f"Erro ao fazer logout no servidor: {str(e)}")
        
        # Limpar estado da sessão
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.session_state.login_attempts = 0
        
        # Limpar cache do Streamlit
        st.cache_data.clear()
        
        return {
            'success': True,
            'message': 'Logout realizado com sucesso'
        }
    
    def render_login_page(self) -> Tuple[bool, Optional[str]]:
        """
        Renderiza página de login
        Retorna: (autenticado, mensagem)
        """
        st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .stButton > button {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.title("🔐 MonitorPro")
        st.markdown("### Sistema de Monitoramento de Estudos")
        
        tab1, tab2 = st.tabs(["Login", "Criar Conta"])
        
        login_result = None
        
        # Tab Login
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email", 
                                    placeholder="seu@email.com")
                password = st.text_input("Senha", type="password", 
                                       key="login_password", 
                                       placeholder="Sua senha")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    if email and password:
                        with st.spinner("Autenticando..."):
                            result = self.login(email, password)
                            login_result = result
                            if result['success']:
                                st.success(result['message'])
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(result['message'])
                    else:
                        st.warning("Preencha todos os campos")
        
        # Tab Cadastro
        with tab2:
            with st.form("signup_form"):
                email = st.text_input("Email", key="signup_email",
                                    placeholder="seu@email.com")
                password = st.text_input("Senha (mín. 6 caracteres)", 
                                       type="password", 
                                       key="signup_password",
                                       placeholder="Mínimo 6 caracteres")
                password2 = st.text_input("Confirmar senha", 
                                        type="password", 
                                        key="signup_password2",
                                        placeholder="Digite a senha novamente")
                terms = st.checkbox("Aceito os termos de uso e política de privacidade")
                submit = st.form_submit_button("Criar Conta", use_container_width=True)
                
                if submit:
                    if not terms:
                        st.warning("Você deve aceitar os termos de uso")
                    elif password != password2:
                        st.error("As senhas não coincidem")
                    elif email and password:
                        with st.spinner("Criando conta..."):
                            result = self.signup(email, password)
                            if result['success']:
                                st.success(result['message'])
                                st.info("Verifique seu email e faça login após a confirmação.")
                            else:
                                st.error(result['message'])
                    else:
                        st.warning("Preencha todos os campos")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Informações úteis
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("🔒 Segurança garantida")
        with col2:
            st.caption("📊 Monitoramento em tempo real")
        with col3:
            st.caption("🔄 Sincronização automática")
        
        return self.is_authenticated(), login_result.get('message') if login_result else None
    
    def get_session_info(self) -> Dict:
        """Retorna informações da sessão atual"""
        return {
            'authenticated': st.session_state.get('authenticated', False),
            'user_id': st.session_state.get('user_id'),
            'user_email': st.session_state.get('user_email'),
            'user_name': st.session_state.get('user_name'),
            'login_attempts': st.session_state.get('login_attempts', 0)
        }


# Função auxiliar para uso rápido
def check_auth(supabase_client: Client) -> bool:
    """
    Verifica autenticação e redireciona para login se necessário
    Uso: if check_auth(supabase): mostrar_app()
    """
    auth_manager = AuthManager(supabase_client)
    
    if not auth_manager.is_authenticated():
        auth_manager.render_login_page()
        st.stop()  # Para a execução do app
        return False
    
    return True
