elif menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty:
            st.info("Aguardando dados...")
        else:
            df_hist = df.copy()
            # Formata a data para o padrão brasileiro no visual
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            
            # Definimos as colunas que queremos mostrar e editar
            # Adicionei 'tempo' e 'comentarios' para poderes preencher os que falharam
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'tempo', 'comentarios']
            
            # Verifica se as colunas existem no DataFrame antes de mostrar
            for col in cols_show:
                if col not in df_hist.columns:
                    df_hist[col] = ""

            st.write("📝 Podes editar o Tempo e os Comentários diretamente na tabela abaixo:")
            
            # Editor de dados interativo
            ed = st.data_editor(
                df_hist[cols_show], 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "tempo": st.column_config.TextColumn("Tempo (HH:MM:SS)"),
                    "comentarios": st.column_config.TextColumn("Comentários")
                }
            )
            
            if st.button("💾 CONFIRMAR ALTERAÇÕES"):
                try:
                    for _, r in ed.iterrows():
                        # Converte a data de volta para o formato do banco (AAAA-MM-DD)
                        dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                        
                        supabase.table("registros_estudos").update({
                            "acertos": r['acertos'], 
                            "total": r['total'], 
                            "data_estudo": dt_iso,
                            "tempo": r['tempo'],
                            "comentarios": r['comentarios']
                        }).eq("id", r['id']).execute()
                    
                    st.success("Registros atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")
