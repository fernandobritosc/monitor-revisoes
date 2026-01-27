auth.py - Módulo de Autenticação do MonitorPro
================================================

Este módulo gerencia toda a lógica de autenticação do aplicativo,
incluindo login, logout, cadastro e verificação de sessão.

Autor: MonitorPro Team
Data: 2026-01-26
"""

"""
auth.py - Módulo de Autenticação do MonitorPro
================================================

Este módulo gerencia toda a lógica de autenticação do aplicativo,
incluindo login, logout, cadastro e verificação de sessão.

ATUALIZADO: Agora com persistência de sessão (não desloga ao recarregar!)

Autor: MonitorPro Team
Data: 2026-01-26
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional
import re
import time



class AuthManager:
    """
    Gerenciador de autenticação integrado com Supabase Auth
    
    Responsabilidades:
    - Gerenciar sessões de usuário
    - Login/Logout/Cadastro
    - Validações de segurança
    - Interface de autenticação
    """
    
    def __init__(self, supabase_client: Client):
        """
        Inicializa o gerenciador de autenticação
        
        Args:
            supabase_client: Cliente Supabase configurado
        """
        self.supabase = supabase_client
        self._init_session()
    
    def _init_session(self):
        """Inicializa e verifica sessão persistente"""
        # Tentar recuperar sessão do Supabase
        if not st.session_state.get('authenticated', False):
            try:
                # Verificar se há sessão ativa no Supabase
                session = self.supabase.auth.get_session()
                
                if session and session.user:
                    # Sessão encontrada! Restaurar
                    st.session_state['authenticated'] = True
                    st.session_state['user_id'] = session.user.id
                    st.session_state['user_email'] = session.user.email
                    st.session_state['user_name'] = session.user.email.split('@')[0]
                    st.session_state['access_token'] = session.access_token
                    st.session_state['refresh_token'] = session.refresh_token
                    return
            except Exception:
                pass
        
        # Defaults se não houver sessão
        defaults = {
            'authenticated': False,
            'user_id': None,
            'user_email': None,
            'user_name': None,
            'login_attempts': 0,
            'access_token': None,
            'refresh_token': None
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    # ========================================================================
    # MÉTODOS PRINCIPAIS
    # ========================================================================
    
    def is_authenticated(self) -> bool:
        """
        Verifica se o usuário está autenticado
        
        Returns:
            bool: True se autenticado, False caso contrário
        """
        return st.session_state.get('authenticated', False)
    
    def get_user_id(self) -> Optional[str]:
        """
        Retorna o ID do usuário autenticado
        
        Returns:
            str ou None: ID do usuário ou None se não autenticado
        """
        return st.session_state.get('user_id')
    
    def get_user_email(self) -> Optional[str]:
        """
        Retorna o email do usuário autenticado
        
        Returns:
            str ou None: Email do usuário ou None se não autenticado
        """
        return st.session_state.get('user_email')
    
    def get_user_name(self) -> Optional[str]:
        """
        Retorna o nome do usuário autenticado
        
        Returns:
            str ou None: Nome do usuário ou None se não autenticado
        """
        return st.session_state.get('user_name')
    
    # ========================================================================
    # VALIDAÇÕES
    # ========================================================================
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, any]:
        """
        Valida formato de email
        
        Args:
            email: Email a ser validado
            
        Returns:
            dict: {'valid': bool, 'message': str}
        """
        if not email:
            return {'valid': False, 'message': 'Email é obrigatório'}
        
        # Regex básico para email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, email):
            return {'valid': False, 'message': 'Formato de email inválido'}
        
        return {'valid': True, 'message': 'Email válido'}
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, any]:
        """
        Valida força da senha
        
        Args:
            password: Senha a ser validada
            
        Returns:
            dict: {'valid': bool, 'message': str, 'strength': str}
        """
        if not password:
            return {
                'valid': False, 
                'message': 'Senha é obrigatória',
                'strength': 'none'
            }
        
        if len(password) < 6:
            return {
                'valid': False,
                'message': 'Senha deve ter pelo menos 6 caracteres',
                'strength': 'weak'
            }
        
        # Verificar força da senha
        strength = 'weak'
        score = 0
        
        if len(password) >= 8:
            score += 1
        if re.search(r'[A-Z]', password):  # Letra maiúscula
            score += 1
        if re.search(r'[a-z]', password):  # Letra minúscula
            score += 1
        if re.search(r'\d', password):     # Número
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # Caractere especial
            score += 1
        
        if score <= 2:
            strength = 'weak'
        elif score <= 3:
            strength = 'medium'
        else:
            strength = 'strong'
        
        return {
            'valid': True,
            'message': f'Senha {strength}',
            'strength': strength
        }
    
    # ========================================================================
    # AUTENTICAÇÃO
    # ========================================================================
    
    def login(self, email: str, password: str) -> Dict[str, any]:
        """
        Realiza login do usuário
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['valid']:
            return {'success': False, 'message': email_validation['message']}
        
        # Limite de tentativas
        if st.session_state.login_attempts >= 5:
            return {
                'success': False,
                'message': '❌ Muitas tentativas. Aguarde alguns minutos.'
            }
        
        try:
            # Autenticar com Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Verificar se o login foi bem-sucedido
            if response.user:
                # Armazenar dados na sessão
                st.session_state.authenticated = True
                st.session_state.user_id = response.user.id
                st.session_state.user_email = response.user.email
                st.session_state.user_name = email.split('@')[0].title()
                st.session_state.login_attempts = 0  # Reset tentativas
                
                return {
                    'success': True,
                    'message': f'✅ Bem-vindo, {st.session_state.user_name}!'
                }
            else:
                st.session_state.login_attempts += 1
                return {
                    'success': False,
                    'message': '❌ Email ou senha incorretos'
                }
            
        except Exception as e:
            st.session_state.login_attempts += 1
            error_msg = str(e)
            
            # Mensagens de erro mais amigáveis
            if 'Invalid login credentials' in error_msg:
                return {
                    'success': False,
                    'message': '❌ Email ou senha incorretos'
                }
            elif 'Email not confirmed' in error_msg:
                return {
                    'success': False,
                    'message': '⚠️ Por favor, confirme seu email antes de fazer login'
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ Erro no login: {error_msg}'
                }
    
    def signup(self, email: str, password: str, password_confirm: str) -> Dict[str, any]:
        """
        Cadastra novo usuário
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            password_confirm: Confirmação da senha
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['valid']:
            return {'success': False, 'message': email_validation['message']}
        
        # Validar senha
        password_validation = self.validate_password(password)
        if not password_validation['valid']:
            return {'success': False, 'message': password_validation['message']}
        
        # Verificar confirmação de senha
        if password != password_confirm:
            return {
                'success': False,
                'message': '❌ As senhas não coincidem!'
            }
        
        try:
            # Criar conta no Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {
                    'success': True,
                    'message': '✅ Conta criada! Verifique seu email para confirmar.'
                }
            else:
                return {
                    'success': False,
                    'message': '❌ Erro ao criar conta. Tente novamente.'
                }
            
        except Exception as e:
            error_msg = str(e)
            
            # Mensagens de erro mais amigáveis
            if 'already registered' in error_msg or 'already exists' in error_msg:
                return {
                    'success': False,
                    'message': '⚠️ Este email já está cadastrado. Tente fazer login.'
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ Erro ao criar conta: {error_msg}'
                }
    
    def logout(self) -> Dict[str, any]:
        """
        Realiza logout do usuário
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # Fazer logout no Supabase
            self.supabase.auth.sign_out()
            
            # Limpar session_state
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.login_attempts = 0
            
            return {
                'success': True,
                'message': '✅ Logout realizado com sucesso!'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Erro ao fazer logout: {str(e)}'
            }
    
    # ========================================================================
    # INTERFACE
    # ========================================================================
    
    def render_login_page(self):
        """Renderiza a página de login/cadastro com design moderno"""
        
        # CSS customizado
        st.markdown("""
        <style>
        /* Fundo gradiente */
        .stApp {
            background: linear-gradient(135deg, #0F0F23 0%, #1a1a3e 100%);
        }
        
        /* Container principal */
        .auth-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }
        
        /* Logo/Header */
        .auth-header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .auth-header h1 {
            font-size: 3rem;
            background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .auth-header p {
            color: #94A3B8;
            font-size: 1rem;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(15, 15, 35, 0.5);
            border-radius: 12px;
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: #94A3B8;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #8B5CF6 !important;
            color: white !important;
        }
        
        /* Form inputs */
        .stTextInput input {
            background-color: rgba(15, 15, 35, 0.7) !important;
            border: 1px solid rgba(139, 92, 246, 0.15) !important;
            border-radius: 8px !important;
            color: white !important;
            padding: 12px !important;
        }
        
        .stTextInput input:focus {
            border-color: #8B5CF6 !important;
            box-shadow: 0 0 0 1px #8B5CF6 !important;
        }
        
        /* Buttons */
        .stButton button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.75rem 1.5rem !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%) !important;
            border: none !important;
        }
        
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="auth-header">
            <h1>🎓 MonitorPro</h1>
            <p>Sistema de Acompanhamento de Estudos para Concursos</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs de Login/Cadastro
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Criar Conta"])
        
        # ====================================================================
        # TAB: LOGIN
        # ====================================================================
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### Entrar na sua conta")
                
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
                
                st.write("")  # Espaçamento
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    login_btn = st.form_submit_button(
                        "Entrar",
                        use_container_width=True,
                        type="primary"
                    )
                
                with col2:
                    st.markdown(
                        "<small style='color: #94A3B8;'>Esqueceu a senha?</small>",
                        unsafe_allow_html=True
                    )
                
                if login_btn:
                    if email and password:
                        with st.spinner('Autenticando...'):
                            result = self.login(email, password)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("⚠️ Preencha email e senha!")
        
        # ====================================================================
        # TAB: CADASTRO
        # ====================================================================
        with tab2:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("### Criar nova conta")
                
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
                    help="Use uma senha forte com letras, números e símbolos"
                )
                
                # Validar senha em tempo real
                if password:
                    validation = self.validate_password(password)
                    if validation['strength'] == 'weak':
                        st.warning(f"⚠️ {validation['message']}")
                    elif validation['strength'] == 'medium':
                        st.info(f"ℹ️ {validation['message']}")
                    else:
                        st.success(f"✅ {validation['message']}")
                
                password_confirm = st.text_input(
                    "🔒 Confirmar Senha",
                    type="password",
                    placeholder="••••••••",
                    key="signup_confirm"
                )
                
                st.write("")  # Espaçamento
                
                agree = st.checkbox(
                    "Aceito os termos de uso e política de privacidade",
                    key="agree_terms"
                )
                
                signup_btn = st.form_submit_button(
                    "Criar Conta",
                    use_container_width=True,
                    type="primary"
                )
                
                if signup_btn:
                    if not agree:
                        st.warning("⚠️ Você precisa aceitar os termos para continuar!")
                    elif email and password and password_confirm:
                        with st.spinner('Criando conta...'):
                            result = self.signup(email, password, password_confirm)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.info("💡 Você pode fazer login após confirmar seu email.")
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("⚠️ Preencha todos os campos!")
        
        # Footer
        st.markdown("---")
        st.markdown(
            "<p style='text-align: center; color: #64748B; font-size: 0.85rem;'>"
            "© 2026 MonitorPro - Desenvolvido com ❤️ por você"
            "</p>",
            unsafe_allow_html=True
        )
    
    def render_user_widget(self):
        """Renderiza widget do usuário na sidebar"""
        if self.is_authenticated():
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### 👤 {self.get_user_name()}")
            st.sidebar.caption(f"📧 {self.get_user_email()}")
            
            if st.sidebar.button("🚪 Sair", use_container_width=True):
                result = self.logout()
                if result['success']:
                    st.rerun()
