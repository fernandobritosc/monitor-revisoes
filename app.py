if menu == "Histórico":
        st.subheader("📜 Histórico de Estudos")
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            df_hist = df.copy()
            df_hist['data_estudo'] = pd.to_datetime(df_hist['data_estudo']).dt.strftime('%d/%m/%Y')
            df_hist['id'] = df_hist['id'].astype(str)
            df_hist['taxa'] = pd.to_numeric(df_hist['taxa'], errors='coerce').fillna(0).astype(float)
            
            # FILTRO NO TOPO
            filtro_mat = st.multiselect("Filtrar por Disciplina", options=df_hist['materia'].unique())
            if filtro_mat:
                df_hist = df_hist[df_hist['materia'].isin(filtro_mat)]
            
            # --- PAINEL DE MÉTRICAS RÁPIDAS (KPIs) ---
            st.divider()
            kpi1, kpi2, kpi3 = st.columns(3)
            total_questoes = df_hist['total'].sum()
            media_acertos = df_hist['taxa'].mean()
            
            kpi1.metric("Questões Resolvidas", f"{int(total_questoes):,}".replace(",", "."))
            kpi2.metric("Precisão Média", f"{media_acertos:.1f}%")
            kpi3.metric("Registros na Tela", len(df_hist))
            st.divider()

            # EDITOR COM LAYOUT WIDE E BARRA DE PROGRESSO
            cols_show = ['id', 'data_estudo', 'materia', 'assunto', 'acertos', 'total', 'taxa', 'tempo', 'comentarios']
            
            ed = st.data_editor(
                df_hist[cols_show], 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "taxa": st.column_config.ProgressColumn("Precisão", min_value=0, max_value=100, format="%.1f%%"),
                    "acertos": st.column_config.NumberColumn("✅", width="small"),
                    "total": st.column_config.NumberColumn("📊", width="small"),
                    "data_estudo": "Data",
                    "tempo": "⏱️ Tempo",
                    "comentarios": st.column_config.TextColumn("Comentários", width="large")
                }
            )
            
            if st.button("💾 CONFIRMAR ALTERAÇÕES", use_container_width=True):
                for _, r in ed.iterrows():
                    dt_iso = datetime.datetime.strptime(r['data_estudo'], '%d/%m/%Y').strftime('%Y-%m-%d')
                    supabase.table("registros_estudos").update({
                        "acertos": r['acertos'], "total": r['total'], "data_estudo": dt_iso,
                        "tempo": r['tempo'], "comentarios": r['comentarios'],
                        "taxa": (r['acertos']/r['total']*100) if r['total'] > 0 else 0
                    }).eq("id", r['id']).execute()
                st.success("Alterações salvas!"); time.sleep(1); st.rerun()
