def get_notion_errors_count():
    try:
        print("🔍 A verificar o Notion...") # Isso aparecerá na tela preta
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={"property": "Revisado", "checkbox": {"equals": False}}
        )
        total = len(response.get("results", []))
        print(f"✅ Sucesso! Encontrei {total} erros pendentes.")
        return total
    except Exception as e:
        print(f"❌ ERRO NO NOTION: {e}") # O erro aparecerá em letras claras na tela preta
        return 0
