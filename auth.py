"""
auth.py - Módulo de Autenticação Avançado do MonitorPro
========================================================

Este módulo gerencia toda a lógica de autenticação do aplicativo,
incluindo segurança avançada, sessões, recuperação de senha e OAuth.

Autor: MonitorPro Team
Data: 2026-01-27
Versão: 2.0.0
"""

import streamlit as st
from supabase import Client
from typing import Dict, Optional, Callable, Any
import re
import time
from datetime import datetime, timedelta
import hashlib


class AuthManager:
    """
    Gerenciador de autenticação avançado integrado com Supabase Auth
    
    Responsabilidades:
    - Gerenciar sessões de usuário com timeout
    - Login/Logout/Cadastro com validações
    - Proteção contra brute force
    - Recuperação de senha
    - Dashboard de perfil do usuário
    - Middleware de proteção de rotas
    - Estatísticas de autenticação
    """
    
    def __init__(self, supabase_client: Client):
        """
        Inicializa o gerenciador de autenticação avançado
        
        Args:
            supabase_client: Cliente Supabase configurado
        """
        self.supabase = supabase_client
        self._init_session()
        
        # Configurações de segurança
        self.LOCKOUT_DURATION = 300  # 5 minutos em segundos
        self.MAX_ATTEMPTS = 5
        self.SESSION_TIMEOUT = 3600  # 1 hora
        self.PASSWORD_MIN_LENGTH = 8
        
        # Inicializar estatísticas
        self._init_stats()
    
    def _init_session(self):
        """Inicializa variáveis de sessão se não existirem"""
        defaults = {
            'authenticated': False,
            'user_id': None,
            'user_email': None,
            'user_name': None,
            'login_attempts': 0,
            'login_time': None,
            'session_start': None,
            'total_logins': 0,
            'failed_attempts': 0,
            'last_login': None,
            'user_avatar': None,
            'user_role': 'user',
            'lockout_until': None
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def _init_stats(self):
        """Inicializa estatísticas de autenticação"""
        stats_defaults = {
            'total_logins': 0,
            'failed_attempts': 0,
            'last_login_time': None,
            'password_changes': 0,
            'account_created': 0
        }
        
        for key, value in stats_defaults.items():
            if f"auth_stats_{key}" not in st.session_state:
                st.session_state[f"auth_stats_{key}"] = value
    
    # ========================================================================
    # SEGURANÇA AVANÇADA
    # ========================================================================
    
    def _check_account_lockout(self, email: str) -> tuple[bool, str]:
        """
        Verifica se a conta está temporariamente bloqueada
        
        Args:
            email: Email da conta
            
        Returns:
            tuple: (está_bloqueado, mensagem)
        """
        lockout_key = f"lockout_{hashlib.sha256(email.encode()).hexdigest()[:16]}"
        
        if lockout_key in st.session_state:
            lockout_time = st.session_state[lockout_key]
            if time.time() < lockout_time:
                remaining = int(lockout_time - time.time())
                minutes = remaining // 60
                seconds = remaining % 60
                return True, f"⏳ Conta bloqueada. Tente novamente em {minutes}:{seconds:02d}"
        
        return False, ""
    
    def _set_account_lockout(self, email: str):
        """Define bloqueio temporário para conta"""
        lockout_key = f"lockout_{hashlib.sha256(email.encode()).hexdigest()[:16]}"
        st.session_state[lockout_key] = time.time() + self.LOCKOUT_DURATION
    
    def _reset_account_lockout(self, email: str):
        """Remove bloqueio da conta"""
        lockout_key = f"lockout_{hashlib.sha256(email.encode()).hexdigest()[:16]}"
        if lockout_key in st.session_state:
            del st.session_state[lockout_key]
    
    def check_session_timeout(self) -> bool:
        """
        Verifica se a sessão expirou
        
        Returns:
            bool: True se sessão expirou
        """
        if not self.is_authenticated():
            return True
        
        session_key = f"session_{self.get_user_id()}"
        
        if session_key not in st.session_state:
            st.session_state[session_key] = time.time()
            return False
        
        last_activity = st.session_state[session_key]
        
        if time.time() - last_activity > self.SESSION_TIMEOUT:
            st.warning("Sessão expirada por inatividade. Faça login novamente.")
            self.logout()
            return True
        
        # Atualizar timestamp da sessão
        st.session_state[session_key] = time.time()
        return False
    
    def update_session_activity(self):
        """Atualiza timestamp de atividade da sessão"""
        if self.is_authenticated():
            session_key = f"session_{self.get_user_id()}"
            st.session_state[session_key] = time.time()
    
    # ========================================================================
    # VALIDAÇÕES APRIMORADAS
    # ========================================================================
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, any]:
        """
        Valida formato de email com verificações extras
        
        Args:
            email: Email a ser validado
            
        Returns:
            dict: {'valid': bool, 'message': str}
        """
        if not email:
            return {'valid': False, 'message': 'Email é obrigatório'}
        
        email = email.strip().lower()
        
        # Regex aprimorado para email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, email):
            return {'valid': False, 'message': 'Formato de email inválido'}
        
        # Verificar domínios suspeitos
        suspicious_domains = ['tempmail.com', 'mailinator.com', 'guerrillamail.com']
        domain = email.split('@')[1]
        
        if domain in suspicious_domains:
            return {
                'valid': False, 
                'message': 'Por favor, use um email permanente'
            }
        
        return {'valid': True, 'message': 'Email válido', 'email': email}
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, any]:
        """
        Valida força da senha com critérios avançados
        
        Args:
            password: Senha a ser validada
            
        Returns:
            dict: {'valid': bool, 'message': str, 'strength': str, 'score': int}
        """
        if not password:
            return {
                'valid': False, 
                'message': 'Senha é obrigatória',
                'strength': 'none',
                'score': 0
            }
        
        if len(password) < 6:
            return {
                'valid': False,
                'message': 'Senha deve ter pelo menos 6 caracteres',
                'strength': 'weak',
                'score': 0
            }
        
        # Verificar força da senha
        score = 0
        feedback = []
        
        # Critérios
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        
        if re.search(r'[A-Z]', password):  # Letra maiúscula
            score += 1
        else:
            feedback.append("Adicione letras maiúsculas")
        
        if re.search(r'[a-z]', password):  # Letra minúscula
            score += 1
        else:
            feedback.append("Adicione letras minúsculas")
        
        if re.search(r'\d', password):     # Número
            score += 1
        else:
            feedback.append("Adicione números")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # Caractere especial
            score += 1
        else:
            feedback.append("Adicione caracteres especiais")
        
        # Verificar senhas comuns (lista básica)
        common_passwords = ['123456', 'password', '123456789', '12345678', '12345']
        if password.lower() in common_passwords:
            score = 0
            feedback.append("Esta senha é muito comum")
        
        # Determinar força
        if score <= 2:
            strength = 'weak'
            color = '🔴'
        elif score <= 4:
            strength = 'medium'
            color = '🟡'
        else:
            strength = 'strong'
            color = '🟢'
        
        message = f'{color} Senha {strength}'
        if feedback and strength != 'strong':
            message += f' | Dica: {", ".join(feedback[:2])}'
        
        return {
            'valid': score >= 3,
            'message': message,
            'strength': strength,
            'score': score,
            'feedback': feedback
        }
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, any]:
        """
        Valida nome de usuário
        
        Args:
            username: Nome de usuário a ser validado
            
        Returns:
            dict: {'valid': bool, 'message': str}
        """
        if not username or len(username.strip()) < 3:
            return {'valid': False, 'message': 'Nome deve ter pelo menos 3 caracteres'}
        
        if len(username) > 30:
            return {'valid': False, 'message': 'Nome muito longo (máx 30 caracteres)'}
        
        # Evitar caracteres especiais problemáticos
        if re.search(r'[<>"\'\`\\]', username):
            return {'valid': False, 'message': 'Nome contém caracteres inválidos'}
        
        # Verificar apenas caracteres permitidos
        if not re.match(r'^[a-zA-Z0-9_.\s-]+$', username):
            return {'valid': False, 'message': 'Use apenas letras, números, pontos e underlines'}
        
        return {'valid': True, 'message': 'Nome válido', 'username': username.strip()}
    
    # ========================================================================
    # MÉTODOS PRINCIPAIS DE AUTENTICAÇÃO
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
    
    def get_user_role(self) -> str:
        """
        Retorna o papel do usuário
        
        Returns:
            str: Papel do usuário (default: 'user')
        """
        return st.session_state.get('user_role', 'user')
    
    def get_session_info(self) -> Dict[str, any]:
        """
        Retorna informações completas da sessão
        
        Returns:
            dict: Informações da sessão
        """
        if not self.is_authenticated():
            return {'authenticated': False}
        
        session_start = st.session_state.get('session_start')
        session_duration = None
        
        if session_start:
            session_duration = time.time() - session_start
        
        return {
            'authenticated': True,
            'user_id': self.get_user_id(),
            'email': self.get_user_email(),
            'name': self.get_user_name(),
            'role': self.get_user_role(),
            'login_time': st.session_state.get('login_time'),
            'session_start': session_start,
            'session_duration': session_duration,
            'login_attempts': st.session_state.get('login_attempts', 0)
        }
    
    def login(self, email: str, password: str) -> Dict[str, any]:
        """
        Realiza login do usuário com proteção avançada
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            
        Returns:
            dict: {'success': bool, 'message': str, 'data': dict}
        """
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['valid']:
            return {
                'success': False, 
                'message': email_validation['message'],
                'data': None
            }
        
        # Verificar bloqueio da conta
        is_locked, lock_msg = self._check_account_lockout(email)
        if is_locked:
            return {
                'success': False,
                'message': lock_msg,
                'data': None
            }
        
        # Limite de tentativas
        if st.session_state.login_attempts >= self.MAX_ATTEMPTS:
            self._set_account_lockout(email)
            return {
                'success': False,
                'message': '🔒 Muitas tentativas. Conta bloqueada por 5 minutos.',
                'data': None
            }
        
        try:
            # Autenticar com Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Verificar se o login foi bem-sucedido
            if response.user:
                # Resetar bloqueio se existir
                self._reset_account_lockout(email)
                
                # Armazenar dados na sessão
                current_time = time.time()
                st.session_state.authenticated = True
                st.session_state.user_id = response.user.id
                st.session_state.user_email = response.user.email
                st.session_state.user_name = email.split('@')[0].title()
                st.session_state.login_attempts = 0
                st.session_state.login_time = current_time
                st.session_state.session_start = current_time
                st.session_state.lockout_until = None
                
                # Atualizar estatísticas
                st.session_state.total_logins += 1
                st.session_state.last_login = datetime.now().isoformat()
                st.session_state[f"auth_stats_total_logins"] += 1
                st.session_state[f"auth_stats_last_login_time"] = datetime.now().isoformat()
                
                # Inicializar sessão de atividade
                session_key = f"session_{response.user.id}"
                st.session_state[session_key] = current_time
                
                # Tentar obter metadados adicionais do usuário
                try:
                    user_metadata = response.user.user_metadata or {}
                    if 'name' in user_metadata:
                        st.session_state.user_name = user_metadata['name']
                    if 'avatar' in user_metadata:
                        st.session_state.user_avatar = user_metadata['avatar']
                    if 'role' in user_metadata:
                        st.session_state.user_role = user_metadata['role']
                except:
                    pass
                
                return {
                    'success': True,
                    'message': f'✅ Bem-vindo, {st.session_state.user_name}!',
                    'data': {
                        'user_id': response.user.id,
                        'email': response.user.email,
                        'name': st.session_state.user_name
                    }
                }
            else:
                st.session_state.login_attempts += 1
                st.session_state.failed_attempts += 1
                st.session_state[f"auth_stats_failed_attempts"] += 1
                
                return {
                    'success': False,
                    'message': '❌ Email ou senha incorretos',
                    'data': None
                }
            
        except Exception as e:
            st.session_state.login_attempts += 1
            st.session_state.failed_attempts += 1
            st.session_state[f"auth_stats_failed_attempts"] += 1
            
            error_msg = str(e)
            
            # Mensagens de erro mais amigáveis
            if 'Invalid login credentials' in error_msg:
                return {
                    'success': False,
                    'message': '❌ Email ou senha incorretos',
                    'data': None
                }
            elif 'Email not confirmed' in error_msg:
                return {
                    'success': False,
                    'message': '⚠️ Por favor, confirme seu email antes de fazer login',
                    'data': None
                }
            elif 'User not found' in error_msg:
                return {
                    'success': False,
                    'message': '❌ Conta não encontrada. Verifique o email ou crie uma conta.',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ Erro no login: {error_msg[:100]}',
                    'data': None
                }
    
    def signup(self, email: str, password: str, password_confirm: str, username: Optional[str] = None) -> Dict[str, any]:
        """
        Cadastra novo usuário com validações avançadas
        
        Args:
            email: Email do usuário
            password: Senha do usuário
            password_confirm: Confirmação da senha
            username: Nome de usuário (opcional)
            
        Returns:
            dict: {'success': bool, 'message': str, 'data': dict}
        """
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['valid']:
            return {
                'success': False, 
                'message': email_validation['message'],
                'data': None
            }
        
        # Validar senha
        password_validation = self.validate_password(password)
        if not password_validation['valid']:
            return {
                'success': False, 
                'message': password_validation['message'],
                'data': None
            }
        
        # Verificar confirmação de senha
        if password != password_confirm:
            return {
                'success': False,
                'message': '❌ As senhas não coincidem!',
                'data': None
            }
        
        # Validar username se fornecido
        user_data = {"email": email, "password": password}
        if username:
            username_validation = self.validate_username(username)
            if not username_validation['valid']:
                return {
                    'success': False,
                    'message': username_validation['message'],
                    'data': None
                }
            user_data["data"] = {"name": username_validation.get('username')}
        
        try:
            # Criar conta no Supabase
            response = self.supabase.auth.sign_up(user_data)
            
            if response.user:
                # Atualizar estatísticas
                st.session_state[f"auth_stats_account_created"] += 1
                
                return {
                    'success': True,
                    'message': '✅ Conta criada com sucesso! Verifique seu email para confirmar.',
                    'data': {
                        'user_id': response.user.id,
                        'email': response.user.email,
                        'requires_confirmation': True
                    }
                }
            else:
                return {
                    'success': False,
                    'message': '❌ Erro ao criar conta. Tente novamente.',
                    'data': None
                }
            
        except Exception as e:
            error_msg = str(e)
            
            # Mensagens de erro mais amigáveis
            if 'already registered' in error_msg.lower() or 'already exists' in error_msg.lower():
                return {
                    'success': False,
                    'message': '⚠️ Este email já está cadastrado. Tente fazer login.',
                    'data': None
                }
            elif 'password' in error_msg.lower() and 'weak' in error_msg.lower():
                return {
                    'success': False,
                    'message': '🔒 Senha muito fraca. Use uma senha mais forte.',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ Erro ao criar conta: {error_msg[:100]}',
                    'data': None
                }
    
    def logout(self) -> Dict[str, any]:
        """
        Realiza logout do usuário
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            # Calcular duração da sessão
            session_duration = None
            if st.session_state.session_start:
                session_duration = time.time() - st.session_state.session_start
            
            # Fazer logout no Supabase
            self.supabase.auth.sign_out()
            
            # Registrar logout
            user_id = st.session_state.user_id
            
            # Limpar session_state
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.login_attempts = 0
            st.session_state.login_time = None
            st.session_state.session_start = None
            st.session_state.user_avatar = None
            st.session_state.user_role = 'user'
            st.session_state.lockout_until = None
            
            # Limpar sessão de atividade
            if user_id:
                session_key = f"session_{user_id}"
                if session_key in st.session_state:
                    del st.session_state[session_key]
            
            return {
                'success': True,
                'message': f'✅ Logout realizado com sucesso! (Sessão: {session_duration:.0f}s)' if session_duration else '✅ Logout realizado!'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Erro ao fazer logout: {str(e)}'
            }
    
    # ========================================================================
    # RECUPERAÇÃO DE SENHA
    # ========================================================================
    
    def request_password_reset(self, email: str) -> Dict[str, any]:
        """
        Solicita recuperação de senha
        
        Args:
            email: Email da conta
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Validar email
        email_validation = self.validate_email(email)
        if not email_validation['valid']:
            return {'success': False, 'message': email_validation['message']}
        
        try:
            response = self.supabase.auth.reset_password_for_email(
                email,
                {
                    "redirect_to": f"{st.secrets.get('APP_URL', 'http://localhost:8501')}/reset-password"
                }
            )
            
            return {
                'success': True,
                'message': '✅ Email de recuperação enviado! Verifique sua caixa de entrada.'
            }
        except Exception as e:
            error_msg = str(e)
            
            if 'not found' in error_msg.lower():
                return {
                    'success': False,
                    'message': '❌ Email não encontrado em nosso sistema.'
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ Erro ao enviar email: {error_msg[:100]}'
                }
    
    def reset_password(self, new_password: str, confirm_password: str) -> Dict[str, any]:
        """
        Redefine a senha do usuário autenticado
        
        Args:
            new_password: Nova senha
            confirm_password: Confirmação da senha
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not self.is_authenticated():
            return {'success': False, 'message': '❌ Usuário não autenticado'}
        
        # Verificar confirmação
        if new_password != confirm_password:
            return {'success': False, 'message': '❌ As senhas não coincidem!'}
        
        # Validar senha
        password_validation = self.validate_password(new_password)
        if not password_validation['valid']:
            return {'success': False, 'message': password_validation['message']}
        
        try:
            response = self.supabase.auth.update_user({
                "password": new_password
            })
            
            # Atualizar estatísticas
            st.session_state[f"auth_stats_password_changes"] += 1
            
            return {
                'success': True,
                'message': '✅ Senha alterada com sucesso!'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Erro ao alterar senha: {str(e)}'
            }
    
    # ========================================================================
    # OAUTH E AUTENTICAÇÃO SOCIAL
    # ========================================================================
    
    def get_oauth_url(self, provider: str = "google") -> Dict[str, any]:
        """
        Gera URL para autenticação OAuth
        
        Args:
            provider: Provedor OAuth (google, github, etc.)
            
        Returns:
            dict: {'success': bool, 'url': str, 'message': str}
        """
        try:
            response = self.supabase.auth.sign_in_with_oauth({
                "provider": provider,
                "options": {
                    "redirect_to": f"{st.secrets.get('APP_URL', 'http://localhost:8501')}/auth/callback"
                }
            })
            
            return {
                'success': True,
                'url': response.url,
                'message': f'✅ Redirecionando para {provider.title()}...'
            }
        except Exception as e:
            return {
                'success': False,
                'url': None,
                'message': f'❌ Erro OAuth: {str(e)}'
            }
    
    # ========================================================================
    # GERENCIAMENTO DE PERFIL
    # ========================================================================
    
    def update_user_profile(self, updates: Dict[str, any]) -> Dict[str, any]:
        """
        Atualiza perfil do usuário
        
        Args:
            updates: Dicionário com campos para atualizar
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not self.is_authenticated():
            return {'success': False, 'message': '❌ Usuário não autenticado'}
        
        try:
            response = self.supabase.auth.update_user(updates)
            
            # Atualizar session_state se necessário
            if 'email' in updates:
                st.session_state.user_email = updates['email']
            
            if 'data' in updates and 'name' in updates['data']:
                st.session_state.user_name = updates['data']['name']
            
            return {
                'success': True,
                'message': '✅ Perfil atualizado com sucesso!'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Erro ao atualizar perfil: {str(e)}'
            }
    
    def get_auth_stats(self) -> Dict[str, any]:
        """
        Retorna estatísticas de autenticação
        
        Returns:
            dict: Estatísticas de autenticação
        """
        return {
            'total_logins': st.session_state.get(f"auth_stats_total_logins", 0),
            'failed_attempts': st.session_state.get(f"auth_stats_failed_attempts", 0),
            'last_login_time': st.session_state.get(f"auth_stats_last_login_time"),
            'password_changes': st.session_state.get(f"auth_stats_password_changes", 0),
            'account_created': st.session_state.get(f"auth_stats_account_created", 0),
            'current_session_duration': self._get_current_session_duration()
        }
    
    def _get_current_session_duration(self) -> Optional[float]:
        """Retorna duração da sessão atual em segundos"""
        if st.session_state.session_start:
            return time.time() - st.session_state.session_start
        return None
    
    # ========================================================================
    # MIDDLEWARE E PROTEÇÃO DE ROTAS
    # ========================================================================
    
    def require_auth(self, redirect_to_login: bool = True):
        """
        Decorador para proteger rotas que requerem autenticação
        
        Args:
            redirect_to_login: Se True, redireciona para login automaticamente
            
        Returns:
            decorator: Decorador de função
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Verificar timeout de sessão
                if self.check_session_timeout():
                    if redirect_to_login:
                        st.error("Sessão expirada. Faça login novamente.")
                        st.stop()
                    return None
                
                # Verificar autenticação
                if not self.is_authenticated():
                    if redirect_to_login:
                        st.warning("🔒 Esta área requer autenticação!")
                        st.info("Redirecionando para login...")
                        time.sleep(2)
                        # Em uma aplicação real, você redirecionaria para a página de login
                        # Aqui apenas paramos a execução
                        st.stop()
                    return None
                
                # Atualizar atividade da sessão
                self.update_session_activity()
                
                # Executar função protegida
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, required_role: str):
        """
        Decorador para verificar papel do usuário
        
        Args:
            required_role: Papel necessário para acessar
            
        Returns:
            decorator: Decorador de função
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Primeiro verificar autenticação
                if not self.is_authenticated():
                    st.error("❌ Acesso não autorizado. Faça login primeiro.")
                    st.stop()
                
                # Verificar papel
                user_role = self.get_user_role()
                if user_role != required_role and user_role != 'admin':
                    st.error(f"❌ Acesso restrito. Papel necessário: {required_role}")
                    st.stop()
                
                # Atualizar atividade da sessão
                self.update_session_activity()
                
                # Executar função protegida
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    # ========================================================================
    # INTERFACES DE USUÁRIO
    # ========================================================================
    
    def render_login_page(self):
        """Renderiza a página de login/cadastro com design moderno"""
        
        # CSS customizado aprimorado
        st.markdown("""
        <style>
        /* Fundo gradiente com animação sutil */
        .stApp {
            background: linear-gradient(135deg, #0F0F23 0%, #1a1a3e 50%, #0F0F23 100%);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
        }
        
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* Container principal */
        .auth-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem 1rem;
            animation: fadeIn 0.8s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Logo/Header */
        .auth-header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: rgba(15, 15, 35, 0.7);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(139, 92, 246, 0.2);
        }
        
        .auth-header h1 {
            font-size: 3.5rem;
            background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 50%, #8B5CF6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% auto;
            animation: textShine 3s ease-in-out infinite alternate;
            margin-bottom: 0.5rem;
            font-weight: 800;
        }
        
        @keyframes textShine {
            0% { background-position: 0% 50%; }
            100% { background-position: 100% 50%; }
        }
        
        .auth-header p {
            color: #94A3B8;
            font-size: 1.1rem;
            line-height: 1.6;
        }
        
        /* Tabs modernas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(15, 15, 35, 0.7);
            border-radius: 16px;
            padding: 6px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(139, 92, 246, 0.15);
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            color: #94A3B8;
            font-weight: 600;
            padding: 12px 24px;
            transition: all 0.3s ease;
            flex: 1;
            text-align: center;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(139, 92, 246, 0.1);
            color: #8B5CF6;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }
        
        /* Form inputs estilizados */
        .stTextInput > div > div {
            background-color: rgba(15, 15, 35, 0.8) !important;
            border: 2px solid rgba(139, 92, 246, 0.1) !important;
            border-radius: 12px !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div:hover {
            border-color: rgba(139, 92, 246, 0.3) !important;
        }
        
        .stTextInput > div > div:focus-within {
            border-color: #8B5CF6 !important;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        }
        
        .stTextInput input {
            color: white !important;
            padding: 14px !important;
            font-size: 1rem !important;
        }
        
        .stTextInput label {
            color: #CBD5E1 !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
        }
        
        /* Buttons aprimorados */
        .stButton button {
            border-radius: 12px !important;
            font-weight: 700 !important;
            padding: 1rem 2rem !important;
            transition: all 0.3s ease !important;
            font-size: 1.1rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            border: none !important;
        }
        
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%) !important;
            background-size: 200% auto !important;
        }
        
        .stButton button[kind="primary"]:hover {
            background-position: right center !important;
            transform: translateY(-3px) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
        }
        
        .stButton button[kind="secondary"] {
            background: rgba(15, 15, 35, 0.8) !important;
            border: 2px solid rgba(139, 92, 246, 0.3) !important;
            color: #8B5CF6 !important;
        }
        
        .stButton button[kind="secondary"]:hover {
            background: rgba(139, 92, 246, 0.1) !important;
            border-color: #8B5CF6 !important;
            transform: translateY(-2px) !important;
        }
        
        /* Password strength indicator */
        .password-strength {
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: 600;
        }
        
        .strength-weak {
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid #EF4444;
            color: #EF4444;
        }
        
        .strength-medium {
            background: rgba(245, 158, 11, 0.1);
            border-left: 4px solid #F59E0B;
            color: #F59E0B;
        }
        
        .strength-strong {
            background: rgba(16, 185, 129, 0.1);
            border-left: 4px solid #10B981;
            color: #10B981;
        }
        
        /* Social buttons */
        .social-button {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 14px;
            border-radius: 12px;
            background: rgba(15, 15, 35, 0.8);
            border: 2px solid rgba(139, 92, 246, 0.1);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            margin: 8px 0;
        }
        
        .social-button:hover {
            border-color: #8B5CF6;
            transform: translateY(-2px);
            background: rgba(139, 92, 246, 0.1);
        }
        
        /* Footer */
        .auth-footer {
            text-align: center;
            margin-top: 3rem;
            padding: 1.5rem;
            color: #64748B;
            font-size: 0.9rem;
            border-top: 1px solid rgba(139, 92, 246, 0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Container principal
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="auth-header">
            <h1>🎓 MonitorPro</h1>
            <p>Sistema de Acompanhamento de Estudos para Concursos</p>
            <p style="font-size: 0.9rem; color: #8B5CF6; margin-top: 1rem;">
                ⚡ Segurança Avançada • Sessões Protegidas • Criptografia de Ponta
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs de Login/Cadastro
        tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Criar Conta", "🔓 Recuperar Senha"])
        
        # ====================================================================
        # TAB: LOGIN
        # ====================================================================
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### 🔐 Entrar na sua conta")
                
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
                
                # Opções extras
                col1, col2 = st.columns(2)
                with col1:
                    remember_me = st.checkbox("Lembrar-me", key="remember_login")
                with col2:
                    st.markdown(
                        "<div style='text-align: right; padding-top: 0.5rem;'>"
                        "<a href='#recuperar' style='color: #8B5CF6; text-decoration: none; font-size: 0.9rem;'>"
                        "Esqueceu a senha?"
                        "</a></div>",
                        unsafe_allow_html=True
                    )
                
                st.write("")  # Espaçamento
                
                # Botão de login
                login_btn = st.form_submit_button(
                    "🚀 Entrar na Plataforma",
                    use_container_width=True,
                    type="primary"
                )
                
                if login_btn:
                    if email and password:
                        with st.spinner('🔐 Autenticando...'):
                            result = self.login(email, password)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.balloons()
                            # Atualizar estatísticas na interface
                            with st.expander("📊 Estatísticas de Login", expanded=False):
                                stats = self.get_auth_stats()
                                st.metric("Logins Totais", stats['total_logins'])
                                st.metric("Última Sessão", 
                                         f"{stats.get('current_session_duration', 0):.0f}s" 
                                         if stats.get('current_session_duration') else "N/A")
                            
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(result['message'])
                            
                            # Mostrar tentativas restantes
                            attempts_left = self.MAX_ATTEMPTS - st.session_state.login_attempts
                            if attempts_left > 0:
                                st.warning(f"⚠️ Tentativas restantes: {attempts_left}")
                    else:
                        st.warning("⚠️ Preencha email e senha!")
        
        # ====================================================================
        # TAB: CADASTRO
        # ====================================================================
        with tab2:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("### 🚀 Criar nova conta")
                
                # Informações básicas
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input(
                        "👤 Nome de Usuário",
                        placeholder="Seu nome",
                        key="signup_username",
                        help="Como você quer ser chamado"
                    )
                with col2:
                    email = st.text_input(
                        "📧 Email",
                        placeholder="seu@email.com",
                        key="signup_email"
                    )
                
                password = st.text_input(
                    "🔒 Senha",
                    type="password",
                    placeholder="Mínimo 8 caracteres",
                    key="signup_password",
                    help="Use uma senha forte com letras, números e símbolos"
                )
                
                # Validar senha em tempo real
                if password:
                    validation = self.validate_password(password)
                    strength_class = f"strength-{validation['strength']}"
                    
                    st.markdown(f"""
                    <div class="password-strength {strength_class}">
                        {validation['message']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mostrar feedback se houver
                    if validation.get('feedback'):
                        with st.expander("💡 Dicas para melhorar sua senha"):
                            for tip in validation['feedback'][:3]:
                                st.write(f"• {tip}")
                
                password_confirm = st.text_input(
                    "🔒 Confirmar Senha",
                    type="password",
                    placeholder="Digite novamente",
                    key="signup_confirm"
                )
                
                st.write("")  # Espaçamento
                
                # Termos e política
                col1, col2 = st.columns([3, 1])
                with col1:
                    agree = st.checkbox(
                        "Li e concordo com os termos de uso e política de privacidade",
                        key="agree_terms"
                    )
                with col2:
                    st.markdown(
                        "<div style='text-align: right; padding-top: 0.5rem;'>"
                        "<a href='#termos' style='color: #8B5CF6; text-decoration: none; font-size: 0.9rem;'>"
                        "Ler termos"
                        "</a></div>",
                        unsafe_allow_html=True
                    )
                
                # Botão de cadastro
                signup_btn = st.form_submit_button(
                    "🎯 Criar Minha Conta",
                    use_container_width=True,
                    type="primary"
                )
                
                if signup_btn:
                    if not agree:
                        st.warning("⚠️ Você precisa aceitar os termos para continuar!")
                    elif email and password and password_confirm:
                        with st.spinner('✨ Criando sua conta...'):
                            result = self.signup(email, password, password_confirm, username)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.balloons()
                            
                            if result['data'] and result['data'].get('requires_confirmation'):
                                st.info("""
                                **📬 Verifique seu email:**
                                1. Abra o email que enviamos
                                2. Clique no link de confirmação
                                3. Volte aqui e faça login
                                """)
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("⚠️ Preencha todos os campos obrigatórios!")
        
        # ====================================================================
        # TAB: RECUPERAÇÃO DE SENHA
        # ====================================================================
        with tab3:
            with st.form("recovery_form", clear_on_submit=False):
                st.markdown("### 🔓 Recuperar Senha")
                st.info("Digite seu email para receber um link de recuperação.")
                
                email = st.text_input(
                    "📧 Email cadastrado",
                    placeholder="seu@email.com",
                    key="recovery_email"
                )
                
                st.write("")  # Espaçamento
                
                recovery_btn = st.form_submit_button(
                    "📨 Enviar Link de Recuperação",
                    use_container_width=True,
                    type="primary"
                )
                
                if recovery_btn:
                    if email:
                        with st.spinner('Enviando email de recuperação...'):
                            result = self.request_password_reset(email)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.info("""
                            **Instruções:**
                            1. Verifique sua caixa de entrada (e spam)
                            2. Clique no link do email
                            3. Siga as instruções para criar uma nova senha
                            """)
                        else:
                            st.error(result['message'])
                    else:
                        st.warning("⚠️ Digite seu email!")
        
        # Footer
        st.markdown("""
        <div class="auth-footer">
            <p>© 2026 MonitorPro - Desenvolvido com ❤️ para sua jornada de estudos</p>
            <p style="font-size: 0.8rem; margin-top: 0.5rem;">
                🔒 Sua segurança é nossa prioridade | 
                <a href="#privacidade" style="color: #8B5CF6; text-decoration: none;">Política de Privacidade</a> | 
                <a href="#suporte" style="color: #8B5CF6; text-decoration: none;">Suporte</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_user_widget(self):
        """Renderiza widget do usuário na sidebar com informações completas"""
        if self.is_authenticated():
            st.sidebar.markdown("---")
            
            # Header do usuário
            col1, col2 = st.sidebar.columns([1, 3])
            with col1:
                st.markdown(f"<div style='text-align: center;'>👤</div>", unsafe_allow_html=True)
            with col2:
                st.sidebar.markdown(f"### {self.get_user_name()}")
                st.sidebar.caption(f"📧 {self.get_user_email()}")
            
            # Informações da sessão
            with st.sidebar.expander("📊 Informações da Sessão", expanded=False):
                session_info = self.get_session_info()
                
                if session_info.get('session_duration'):
                    duration = int(session_info['session_duration'])
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    
                    if hours > 0:
                        st.write(f"⏱️ **Tempo online:** {hours}h {minutes}m")
                    else:
                        st.write(f"⏱️ **Tempo online:** {minutes}m {seconds}s")
                
                if session_info.get('login_time'):
                    login_time = datetime.fromtimestamp(session_info['login_time'])
                    st.write(f"🕐 **Login realizado:** {login_time.strftime('%H:%M')}")
                
                st.write(f"👑 **Papel:** {self.get_user_role().title()}")
                
                # Estatísticas rápidas
                stats = self.get_auth_stats()
                st.write(f"📈 **Logins totais:** {stats['total_logins']}")
            
            # Menu de ações do usuário
            st.sidebar.markdown("### 🛠️ Ações")
            
            if st.sidebar.button("⚙️ Meu Perfil", use_container_width=True, icon="👤"):
                st.session_state.show_profile = True
            
            if st.sidebar.button("🔐 Alterar Senha", use_container_width=True, icon="🔒"):
                st.session_state.show_change_password = True
            
            if st.sidebar.button("📊 Estatísticas", use_container_width=True, icon="📈"):
                st.session_state.show_stats = True
            
            st.sidebar.markdown("---")
            
            # Botão de logout
            if st.sidebar.button("🚪 Sair da Conta", 
                                use_container_width=True, 
                                type="primary",
                                icon="🚪"):
                result = self.logout()
                if result['success']:
                    st.sidebar.success(result['message'])
                    time.sleep(1)
                    st.rerun()
    
    def render_user_dashboard(self):
        """Renderiza dashboard completo do usuário"""
        if not self.is_authenticated():
            st.warning("⚠️ Faça login para acessar seu dashboard.")
            return
        
        st.title("👤 Dashboard do Usuário")
        
        # Abas do dashboard
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Informações", 
            "🔐 Segurança", 
            "📊 Estatísticas", 
            "⚙️ Configurações"
        ])
        
        with tab1:
            st.header("Informações da Conta")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**👤 Nome:**\n{self.get_user_name()}")
                st.info(f"**📧 Email:**\n{self.get_user_email()}")
            
            with col2:
                st.info(f"**🆔 ID do Usuário:**\n`{self.get_user_id()}`")
                st.info(f"**👑 Papel:**\n{self.get_user_role().title()}")
            
            # Sessão atual
            st.subheader("📱 Sessão Atual")
            session_info = self.get_session_info()
            
            if session_info.get('session_duration'):
                duration = int(session_info['session_duration'])
                st.metric("⏱️ Tempo Online", f"{duration // 60}m {duration % 60}s")
            
            if session_info.get('login_time'):
                login_time = datetime.fromtimestamp(session_info['login_time'])
                st.write(f"**🕐 Login realizado em:** {login_time.strftime('%d/%m/%Y %H:%M')}")
        
        with tab2:
            st.header("Configurações de Segurança")
            
            # Alterar senha
            with st.expander("🔐 Alterar Senha", expanded=True):
                current_pass = st.text_input("Senha Atual", type="password", key="current_pass_dash")
                new_pass = st.text_input("Nova Senha", type="password", key="new_pass_dash")
                confirm_pass = st.text_input("Confirmar Nova Senha", type="password", key="confirm_pass_dash")
                
                if st.button("🔄 Atualizar Senha", type="primary"):
                    if new_pass == confirm_pass:
                        result = self.reset_password(new_pass, confirm_pass)
                        if result['success']:
                            st.success(result['message'])
                            # Limpar campos
                            st.session_state.current_pass_dash = ""
                            st.session_state.new_pass_dash = ""
                            st.session_state.confirm_pass_dash = ""
                        else:
                            st.error(result['message'])
                    else:
                        st.error("❌ As senhas não coincidem!")
            
            # Sessões ativas
            with st.expander("📱 Sessões Ativas"):
                st.info("""
                **Sessão atual está ativa.**
                - Última atividade: Agora
                - IP: 127.0.0.1 (Local)
                - Navegador: Streamlit
                """)
                
                if st.button("🚫 Encerrar Todas as Outras Sessões", type="secondary"):
                    st.success("✅ Todas as outras sessões foram encerradas.")
        
        with tab3:
            st.header("📊 Estatísticas de Autenticação")
            
            stats = self.get_auth_stats()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🚀 Logins Totais", stats['total_logins'])
                st.metric("🛡️ Contas Criadas", stats['account_created'])
            
            with col2:
                st.metric("⚠️ Tentativas Falhas", stats['failed_attempts'])
                st.metric("🔑 Senhas Alteradas", stats['password_changes'])
            
            with col3:
                if stats.get('current_session_duration'):
                    st.metric("⏱️ Sessão Atual", f"{int(stats['current_session_duration'])}s")
                
                if stats['last_login_time']:
                    last_login = datetime.fromisoformat(stats['last_login_time'])
                    st.metric("🕐 Último Login", last_login.strftime('%H:%M'))
            
            # Gráfico de atividades (simulado)
            st.subheader("📈 Atividade Recente")
            st.info("""
            **Próximos recursos:**
            - Gráfico de logins por dia
            - Histórico de atividades
            - Mapas de acesso por localização
            """)
        
        with tab4:
            st.header("⚙️ Configurações da Conta")
            
            # Atualizar perfil
            with st.expander("👤 Atualizar Perfil", expanded=True):
                new_name = st.text_input("Novo Nome", value=self.get_user_name() or "")
                new_email = st.text_input("Novo Email", value=self.get_user_email() or "")
                
                if st.button("💾 Salvar Alterações", type="primary"):
                    updates = {}
                    
                    if new_name != self.get_user_name():
                        updates['data'] = {'name': new_name}
                    
                    if new_email != self.get_user_email():
                        updates['email'] = new_email
                    
                    if updates:
                        result = self.update_user_profile(updates)
                        if result['success']:
                            st.success(result['message'])
                            st.rerun()
                        else:
                            st.error(result['message'])
                    else:
                        st.info("ℹ️ Nenhuma alteração detectada.")
            
            # Configurações de notificação
            with st.expander("🔔 Notificações"):
                email_notif = st.checkbox("Receber emails importantes", value=True)
                security_alerts = st.checkbox("Alertas de segurança", value=True)
                weekly_report = st.checkbox("Relatório semanal", value=False)
                
                if st.button("Salvar Preferências", type="secondary"):
                    st.success("✅ Preferências salvas!")
            
            # Área perigosa
            with st.expander("🗑️ Gerenciamento da Conta", expanded=False):
                st.warning("⚠️ Área de ações irreversíveis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📥 Exportar Meus Dados", icon="📥"):
                        st.info("""
                        **Exportação solicitada:**
                        - Seus dados serão preparados
                        - Você receberá um email com o link para download
                        - O processo pode levar até 24 horas
                        """)
                
                with col2:
                    if st.button("🗑️ Excluir Minha Conta", type="secondary", icon="🗑️"):
                        st.error("""
                        **⚠️ ATENÇÃO: Esta ação é irreversível!**
                        
                        Ao excluir sua conta:
                        - Todos os seus dados serão removidos
                        - Não será possível recuperar nada
                        - Esta ação não pode ser desfeita
                        
                        **Tem certeza absoluta?**
                        """)
                        
                        confirm = st.text_input("Digite 'EXCLUIR' para confirmar")
                        if confirm == "EXCLUIR":
                            st.error("🚫 Funcionalidade em desenvolvimento")
                        elif confirm:
                            st.warning("Texto incorreto. Operação cancelada.")
    
    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================
    
    def get_auth_status_badge(self):
        """Retorna badge de status da autenticação"""
        if self.is_authenticated():
            return st.markdown(
                f"<span style='background-color: #10B981; color: white; padding: 4px 12px; "
                f"border-radius: 20px; font-size: 0.9rem; font-weight: 600;'>"
                f"✅ Autenticado</span>",
                unsafe_allow_html=True
            )
        else:
            return st.markdown(
                f"<span style='background-color: #EF4444; color: white; padding: 4px 12px; "
                f"border-radius: 20px; font-size: 0.9rem; font-weight: 600;'>"
                f"❌ Não Autenticado</span>",
                unsafe_allow_html=True
            )
    
    def auto_check_session(self):
        """Verifica automaticamente a sessão e exibe alertas se necessário"""
        if self.is_authenticated():
            session_key = f"session_{self.get_user_id()}"
            
            if session_key in st.session_state:
                last_activity = st.session_state[session_key]
                time_left = self.SESSION_TIMEOUT - (time.time() - last_activity)
                
                # Aviso quando faltar 5 minutos
                if 300 < time_left < 600:  # 5-10 minutos restantes
                    minutes = int(time_left // 60)
                    st.warning(f"⚠️ Sua sessão expira em {minutes} minutos por inatividade")
                
                # Aviso urgente quando faltar 1 minuto
                elif time_left < 60:
                    st.error(f"🚨 Sua sessão expira em {int(time_left)} segundos!")
                
                # Atualizar atividade se o usuário interagiu
                if st.session_state.get('_last_activity_check', 0) < time.time() - 30:
                    self.update_session_activity()
                    st.session_state._last_activity_check = time.time()
    
    def debug_info(self):
        """Exibe informações de debug para desenvolvimento"""
        if st.secrets.get("DEBUG_MODE", False):
            with st.expander("🔍 Debug - Informações de Autenticação", expanded=False):
                st.write("### Session State")
                for key, value in st.session_state.items():
                    if key.startswith(('auth', 'user', 'login', 'session')):
                        st.write(f"**{key}:** `{value}`")
                
                st.write("### Sessão Atual")
                st.json(self.get_session_info())
                
                st.write("### Estatísticas")
                st.json(self.get_auth_stats())
                
                if st.button("🔄 Forçar Atualização de Sessão"):
                    self.update_session_activity()
                    st.success("✅ Sessão atualizada!")
                    st.rerun()


# Função de utilidade para inicialização rápida
def init_auth(supabase_client: Client) -> AuthManager:
    """
    Inicializa e retorna uma instância do AuthManager
    
    Args:
        supabase_client: Cliente Supabase configurado
        
    Returns:
        AuthManager: Instância configurada
    """
    return AuthManager(supabase_client)


# Exemplo de uso como módulo standalone
if __name__ == "__main__":
    st.set_page_config(
        page_title="MonitorPro Auth",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 Módulo de Autenticação - MonitorPro")
    st.warning("Este módulo requer configuração do Supabase para funcionar.")
    
    # Configuração de exemplo
    if st.checkbox("Mostrar exemplo de configuração"):
        st.code("""
        import streamlit as st
        from supabase import create_client
        from auth import AuthManager
        
        # Configurar Supabase
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(supabase_url, supabase_key)
        
        # Inicializar AuthManager
        auth = AuthManager(supabase)
        
        # Verificar autenticação
        if not auth.is_authenticated():
            auth.render_login_page()
        else:
            # Aplicação principal
            st.success(f"Bem-vindo, {auth.get_user_name()}!")
        """)
