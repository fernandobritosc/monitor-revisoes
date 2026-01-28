"""
auth.py - Módulo de Autenticação
VERSÃO FINAL - Campos totalmente visíveis
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
        """Verifica autenticação"""
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
            return {'success': False, 'message': f'Erro: {str(e)}'}
    
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
            return {'success': False, 'message': f'Erro: {str(e)}'}
    
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
        """Renderiza página de login - CAMPOS VISÍVEIS"""
        
        # Configurar página
        st.set_page_config(
            page_title="MonitorPro - Login",
            page_icon="📚",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        
        # CSS Mínimo - SÓ O ESSENCIAL
        st.markdown("""
        <style>
        /* Esconder menu e sidebar */
        #MainMenu, footer, header {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stSidebar"] {display: none !important;}
        section[data-testid="stSidebar"] {display: none !important;}
        button[kind="header"] {display: none !important;}
        
        /* Background */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .block-container {
            padding-top: 3rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Header em card branco
            st.markdown("""
            <div style="
                background: white;
                padding: 32px;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                margin-bottom: 24px;
            ">
                <div style="font-size: 48px; margin-bottom: 12px;">📚</div>
                <h1 style="
                    margin: 0 0 8px 0;
                    font-size: 28px;
                    font-weight: 800;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                ">MonitorPro</h1>
                <p style="margin: 0; color: #64748b; font-size: 14px;">Sistema de Estudos</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Tabs
            tab1, tab2 = st.tabs(["🔐 Login", "✨ Cadastrar"])
            
            # TAB LOGIN
            with tab1:
                st.markdown("<div style='background: white; padding: 24px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);'>", unsafe_allow_html=True)
                
                with st.form("login_form"):
                    st.text_input("Email", placeholder="seu@email.com", key="login_email")
                    st.text_input("Senha", type="password", placeholder="••••••••", key="login_password")
                    st.checkbox("Lembrar-me", value=True)
                    
                    if st.form_submit_button("Entrar", use_container_width=True):
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
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # TAB CADASTRO
            with tab2:
                st.markdown("<div style='background: white; padding: 24px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);'>", unsafe_allow_html=True)
                
                with st.form("signup_form"):
                    st.text_input("Email", placeholder="seu@email.com", key="signup_email")
                    st.text_input("Senha", type="password", placeholder="Min. 6 caracteres", key="signup_password")
                    st.text_input("Confirmar", type="password", placeholder="Digite novamente", key="signup_password2")
                    terms = st.checkbox("Aceito os termos")
                    
                    if st.form_submit_button("Criar Conta", use_container_width=True):
                        email = st.session_state.signup_email
                        password = st.session_state.signup_password
                        password2 = st.session_state.signup_password2
                        
                        if not terms:
                            st.warning("⚠️ Aceite os termos")
                        elif password != password2:
                            st.error("❌ Senhas diferentes")
                        elif email and password:
                            with st.spinner("Criando conta..."):
                                result = self.signup(email, password)
                                if result['success']:
                                    st.success("✅ " + result['message'])
                                else:
                                    st.error("❌ " + result['message'])
                        else:
                            st.warning("⚠️ Preencha tudo")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Footer
            st.markdown("""
            <div style="text-align: center; margin-top: 24px; color: white; opacity: 0.8; font-size: 12px;">
                © 2026 MonitorPro
            </div>
            """, unsafe_allow_html=True)
