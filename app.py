# ... (mantenha os imports e as funções de login iguais ao código anterior) ...

# 4. GESTÃO DE EDITAIS (VERSÃO COM EDIÇÃO E EXCLUSÃO)
elif selected == "Gestão Editais":
    st.title("📑 Gestão de Editais")
    t1, t2 = st.tabs(["➕ Novo Concurso", "📚 Matérias e Assuntos"])
    
    with t1:
        with st.form("n"):
            n = st.text_input("Concurso")
            c = st.text_input("Cargo")
            d = st.date_input("Data Prova", format="DD/MM/YYYY")
            if st.form_submit_button("Criar"):
                supabase.table("editais_materias").insert({
                    "concurso": n, "cargo": c, "data_prova": d.strftime('%Y-%m-%d'), 
                    "materia": "Geral", "topicos": []
                }).execute()
                st.cache_data.clear()
                st.rerun()

    with t2:
        if editais:
            sel = st.selectbox("Escolha o Edital", list(editais.keys()))
            st.success(f"Cargo: {editais[sel]['cargo']} | Prova: {editais[sel]['data_br']}")
            
            # --- ADICIONAR NOVA MATÉRIA ---
            with st.expander("➕ Adicionar Nova Matéria"):
                m_n = st.text_input("Nome da Matéria")
                if st.button("Confirmar Matéria"):
                    try:
                        supabase.table("editais_materias").insert({
                            "concurso": sel, "materia": m_n, "topicos": [], 
                            "cargo": editais[sel]['cargo'], "data_prova": editais[sel]['data_iso']
                        }).execute()
                        st.cache_data.clear()
                        st.rerun()
                    except: st.error("Erro ou Matéria já existe.")

            st.markdown("---")
            st.subheader("Gerenciar Matérias Cadastradas")
            
            # --- LISTA DE MATÉRIAS PARA EDITAR/EXCLUIR ---
            for m, t in editais[sel]["materias"].items():
                with st.expander(f"📚 {m}"):
                    # 1. RENOMEAR MATÉRIA
                    novo_nome = st.text_input("Renomear Matéria", value=m, key=f"ren_{m}")
                    if novo_nome != m:
                        if st.button(f"Confirmar Novo Nome para {m}", key=f"btn_ren_{m}"):
                            supabase.table("editais_materias").update({"materia": novo_nome}).eq("concurso", sel).eq("materia", m).execute()
                            st.cache_data.clear()
                            st.rerun()

                    st.markdown("---")
                    
                    # 2. GESTÃO DE ASSUNTOS (TÓPICOS)
                    txt_assuntos = st.text_area(f"Tópicos de {m} (separe por ;)", value="; ".join(t), key=f"txt_{m}")
                    if st.button(f"Atualizar Tópicos de {m}", key=f"btn_top_{m}"):
                        novos_t = [x.strip() for x in txt_assuntos.split(";") if x.strip()]
                        supabase.table("editais_materias").update({"topicos": novos_t}).eq("concurso", sel).eq("materia", m).execute()
                        st.cache_data.clear()
                        st.rerun()

                    st.markdown("---")

                    # 3. EXCLUIR MATÉRIA INTEIRA
                    st.warning(f"Zona de Perigo: A exclusão de '{m}' não pode ser desfeita.")
                    # Checkbox de confirmação para evitar cliques acidentais
                    confirma_exclusao = st.checkbox(f"Eu quero excluir a matéria {m}", key=f"check_{m}")
                    if confirma_exclusao:
                        if st.button(f"🗑️ EXCLUIR {m.upper()} AGORA", key=f"del_{m}"):
                            supabase.table("editais_materias").delete().eq("concurso", sel).eq("materia", m).execute()
                            st.cache_data.clear()
                            st.success(f"{m} removida!")
                            st.rerun()

# ... (mantenha o restante do código igual) ...
