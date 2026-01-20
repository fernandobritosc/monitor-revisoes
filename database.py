import os
from supabase import create_client, Client

# Configurar conexão com Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://seu-projeto.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sua-chave-supabase")

# Inicializar cliente Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conectado ao Supabase")
except Exception as e:
    print(f"❌ Erro ao conectar ao Supabase: {e}")
    supabase = None
