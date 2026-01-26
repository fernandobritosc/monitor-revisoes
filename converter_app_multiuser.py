#!/usr/bin/env python3
"""
converter_app_multiuser.py - Conversor Automático para Multi-Usuário
=====================================================================

Este script converte automaticamente o app.py para suportar multi-usuário.

Uso:
    python converter_app_multiuser.py app__5_.py app_multiuser.py

Autor: MonitorPro Team
Data: 2026-01-26
"""

import re
import sys

def converter_para_multiuser(conteudo):
    """Aplica todas as conversões necessárias"""
    
    print("🔄 Iniciando conversão para multi-usuário...")
    print()
    
    # =======================================================================
    # 1. ADICIONAR IMPORTS NO TOPO
    # =======================================================================
    print("  ✓ Adicionando imports de autenticação...")
    
    import_auth = """import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
import re
import time
from streamlit_option_menu import option_menu
from fpdf import FPDF
import io
import os  # MULTI-USER: Adicionado

# MULTI-USER: Import do módulo de autenticação
# IMPORTANTE: O arquivo auth.py deve estar na mesma pasta do app
try:
    from auth import AuthManager
except ImportError:
    st.error("❌ Erro: arquivo 'auth.py' não encontrado! Certifique-se de que está na mesma pasta do app.")
    st.stop()
"""
    
    # Substituir os imports originais
    conteudo = re.sub(
        r'import streamlit as st.*?import io',
        import_auth,
        conteudo,
        flags=re.DOTALL
    )
    
    # =======================================================================
    # 2. MODIFICAR CONFIGURAÇÃO DO SUPABASE
    # =======================================================================
    print("  ✓ Modificando configuração do Supabase...")
    
    supabase_config = """# --- INTEGRAÇÃO: SUPABASE (MULTI-USER MODE) ---
from supabase import create_client, Client

def init_supabase():
    \"\"\"
    Inicializa Supabase com suporte a autenticação multi-usuário
    Tenta ler de st.secrets primeiro, depois de variáveis de ambiente
    \"\"\"
    try:
        # Tentar secrets do Streamlit (produção)
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        try:
            # Tentar variáveis de ambiente (desenvolvimento)
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if url and key:
                return create_client(url, key)
            else:
                st.error("❌ Credenciais do Supabase não configuradas!")
                st.info("Configure SUPABASE_URL e SUPABASE_KEY em .streamlit/secrets.toml ou variáveis de ambiente")
                return None
        except Exception as e:
            st.error(f"❌ Erro ao conectar com Supabase: {e}")
            return None

# Inicializar Supabase
try:
    supabase: Client = init_supabase()
except Exception:
    supabase = None
    
# =============================================================================
# MULTI-USER: AUTENTICAÇÃO
# =============================================================================

if supabase:
    # Inicializar gerenciador de autenticação
    auth = AuthManager(supabase)
    
    # Verificar se usuário está autenticado
    if not auth.is_authenticated():
        # Usuário NÃO autenticado -> Mostrar tela de login
        auth.render_login_page()
        st.stop()  # Para execução aqui
    
    # Usuário AUTENTICADO -> Obter user_id para usar nas queries
    user_id = auth.get_user_id()
else:
    st.error("❌ Não foi possível conectar ao Supabase. Verifique as configurações.")
    st.stop()
"""
    
    # Substituir configuração antiga do Supabase
    conteudo = re.sub(
        r'# --- INTEGRAÇÃO: SUPABASE.*?supabase = None',
        supabase_config,
        conteudo,
        flags=re.DOTALL
    )
    
    # =======================================================================
    # 3. ADICIONAR user_id NAS QUERIES SELECT
    # =======================================================================
    print("  ✓ Adicionando filtros user_id nas queries SELECT...")
    
    modificacoes_select = 0
    
    # Padrão: .select(...).execute() sem user_id
    def adicionar_user_id_select(match):
        nonlocal modificacoes_select
        linha = match.group(0)
        
        # Não modificar se já tem user_id
        if 'user_id' in linha:
            return linha
        
        # Adicionar .eq("user_id", user_id) antes do .execute()
        nova_linha = linha.replace('.execute()', '.eq("user_id", user_id).execute()')
        modificacoes_select += 1
        return nova_linha
    
    # Encontrar todas as queries SELECT
    conteudo = re.sub(
        r'supabase\.table\([^)]+\)\.select\([^)]*\)[^e]*\.execute\(\)',
        adicionar_user_id_select,
        conteudo
    )
    
    print(f"    → {modificacoes_select} queries SELECT modificadas")
    
    # =======================================================================
    # 4. MODIFICAR GET_EDITAIS PARA INCLUIR USER_ID
    # =======================================================================
    print("  ✓ Modificando função get_editais()...")
    
    conteudo = re.sub(
        r'def get_editais\(supabase\):',
        'def get_editais(supabase, user_id):',
        conteudo
    )
    
    # Atualizar chamadas de get_editais
    conteudo = re.sub(
        r'get_editais\(supabase\)',
        'get_editais(supabase, user_id)',
        conteudo
    )
    
    # =======================================================================
    # 5. ADICIONAR WIDGET DE USUÁRIO NA SIDEBAR
    # =======================================================================
    print("  ✓ Adicionando widget de usuário...")
    
    # Procurar onde começa a sidebar (geralmente depois das configurações)
    # Vamos adicionar um marcador de posição
    sidebar_widget = """
# =============================================================================
# MULTI-USER: WIDGET DE USUÁRIO NA SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown(f'''
    <div style="
        background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">👤</div>
        <div style="font-weight: 700; color: white; font-size: 1.1rem; margin-bottom: 0.25rem;">
            {auth.get_user_name()}
        </div>
        <div style="font-size: 0.75rem; color: rgba(255,255,255,0.8); word-break: break-all;">
            {auth.get_user_email()}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    if st.button("🚪 Sair", use_container_width=True, type="secondary", key="logout_btn"):
        result = auth.logout()
        if result['success']:
            st.rerun()
    
    st.markdown("---")

# =============================================================================
# FIM DO WIDGET DE USUÁRIO
# =============================================================================

"""
    
    # Adicionar widget antes da primeira sidebar usage
    conteudo = conteudo.replace(
        '# --- INTEGRAÇÃO: LÓGICA ---',
        sidebar_widget + '\n# --- INTEGRAÇÃO: LÓGICA ---'
    )
    
    # =======================================================================
    # 6. ADICIONAR COMENTÁRIOS NOS INSERTS
    # =======================================================================
    print("  ⚠️  ATENÇÃO: INSERTs precisam de revisão manual!")
    print("     Adicione 'user_id': user_id em todos os payloads")
    
    # Não podemos modificar INSERTs automaticamente de forma segura
    # Apenas marcar onde estão
    conteudo = re.sub(
        r'(supabase\.table\([^)]+\)\.insert\()',
        r'# MULTI-USER: REVISAR - Adicionar "user_id": user_id no payload\n        \1',
        conteudo
    )
    
    return conteudo

def main():
    """Função principal"""
    
    if len(sys.argv) != 3:
        print("Uso: python converter_app_multiuser.py <arquivo_entrada> <arquivo_saida>")
        print()
        print("Exemplo:")
        print("  python converter_app_multiuser.py app__5_.py app_multiuser.py")
        sys.exit(1)
    
    arquivo_entrada = sys.argv[1]
    arquivo_saida = sys.argv[2]
    
    print("=" * 70)
    print("🔧 CONVERSOR AUTOMÁTICO PARA MULTI-USUÁRIO - MonitorPro")
    print("=" * 70)
    print()
    print(f"📂 Arquivo de entrada: {arquivo_entrada}")
    print(f"📄 Arquivo de saída: {arquivo_saida}")
    print()
    
    # Ler arquivo
    try:
        with open(arquivo_entrada, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        print("✅ Arquivo lido com sucesso")
        print()
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        sys.exit(1)
    
    # Converter
    conteudo_convertido = converter_para_multiuser(conteudo)
    
    # Salvar
    try:
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write(conteudo_convertido)
        print()
        print("✅ Arquivo convertido salvo com sucesso!")
        print()
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        sys.exit(1)
    
    # Instruções finais
    print("=" * 70)
    print("📝 PRÓXIMOS PASSOS OBRIGATÓRIOS")
    print("=" * 70)
    print("""
1. ✅ REVISAR MANUALMENTE o arquivo convertido

2. ✅ Procurar por todos os comentários:
   # MULTI-USER: REVISAR
   E adicionar "user_id": user_id nos payloads de INSERT

3. ✅ Procurar por .update() e .delete() e adicionar:
   .eq("user_id", user_id)

4. ✅ Colocar o arquivo auth.py na mesma pasta do app

5. ✅ Configurar secrets (.streamlit/secrets.toml):
   SUPABASE_URL = "sua_url"
   SUPABASE_KEY = "sua_key"

6. ✅ TESTAR LOCALMENTE antes de fazer deploy!

7. ✅ Verificar se migration.sql foi executada no Supabase

IMPORTANTE: Este conversor é uma AJUDA inicial.
A revisão manual é OBRIGATÓRIA para garantir que tudo funcione!
    """)
    print("=" * 70)

if __name__ == "__main__":
    main()
