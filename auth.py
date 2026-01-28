import streamlit as st
from supabase import Client
from typing import Dict, Optional
import re
import time


class AuthManager:
    """Gerenciador de autenticação com Supabase"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self._restore_session()

    # ------------------------------------------------------------------
    # SESSÃO
    # ------------------------------------------------------------------
    def _restore_session(self):
        """Restaura sessão se existir"""
        defaults = {
            "authenticated": False,
            "user_id": None,
            "user_email": None,
            "user_name": None,
            "login_attempts": 0,
        }

        for k, v in defaults.items():
            st.session_state.setdefault(k, v)

        try:
            session = self.supabase.auth.get_session()
            if session and session.user:
                self._set_user(session.user)
        except Exception:
            pass

    def _set_user(self, user):
        st.session_state.authenticated = True
        st.session_state.user_id = user.id
        st.session_state.user_email = user.email
        st.session_state.user_name = user.email.split("@")[0]
        st.session_state.login_attempts = 0

    def is_authenticated(self) -> bool:
        return bool(st.session_state.get("authenticated"))

    # ------------------------------------------------------------------
    # GETTERS
    # ------------------------------------------------------------------
    def get_user_id(self) -> Optional[str]:
        return st.session_state.get("user_id")

    def get_user_email(self) -> Optional[str]:
        return st.session_state.get("user_email")

    def get_user_name(self) -> str:
        return st.session_state.get("user_name", "Usuário")

    # ------------------------------------------------------------------
    # LOGIN / SIGNUP
    # ------------------------------------------------------------------
    def login(self, email: str, password: str) -> Dict:
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response and response.user:
                self._set_user(response.user)
                return {"success": True, "message": "Login realizado com sucesso"}

            return {"success": False, "message": "Credenciais inválidas"}

        except Exception as e:
            st.session_state.login_attempts += 1
            return {"success": False, "message": str(e)}

    def signup(self, email: str, password: str) -> Dict:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return {"success": False, "message": "Email inválido"}

        if len(password) < 6:
            return {"success": False, "message": "Senha mínima de 6 caracteres"}

        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if response and response.user:
                return {
                    "success": True,
                    "message": "Conta criada! Faça login."
                }

            return {"success": False, "message": "Erro ao criar conta"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # LOGOUT
    # ------------------------------------------------------------------
    def logout(self) -> Dict:
        try:
            self.supabase.auth.sign_out()
        except Exception:
            pass

        for k in ["authenticated", "user_id", "user_email", "user_name"]:
            st.session_state[k] = None

        return {"success": True}
