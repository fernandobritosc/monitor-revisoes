def get_notion_errors_count():
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            filter={"property": "Revisado", "checkbox": {"equals": False}}
        )
        return len(response.get("results", []))
    except Exception as e:
        # Isso vai mostrar o erro no rodapé do seu site para sabermos o que há de errado
        st.sidebar.error(f"Erro no Notion: {e}")
        return 0
