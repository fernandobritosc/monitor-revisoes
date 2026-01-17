import pandas as pd
import datetime

def get_editais(supabase):
    try:
        res = supabase.table("editais_materias").select("*").execute()
        editais = {}
        for row in res.data:
            c = row['concurso']
            if c not in editais:
                editais[c] = {"cargo": row.get('cargo') or "Geral", "materias": {}}
            if row.get('materia'): 
                editais[c]["materias"][row['materia']] = row.get('topicos') or []
        return editais
    except: return {}

def calcular_pendencias(df):
    if df.empty: return pd.DataFrame()
    hoje = datetime.date.today()
    df['dt_temp'] = pd.to_datetime(df['data_estudo']).dt.date
    pendencias = []
    for col in ['rev_24h', 'rev_07d', 'rev_15d', 'rev_30d']:
        if col not in df.columns: df[col] = False
    for _, row in df.iterrows():
        delta = (hoje - row['dt_temp']).days
        taxa = row.get('taxa', 0)
        css = "perf-bad" if taxa < 60 else "perf-med" if taxa < 80 else "perf-good"
        base = {"id": row['id'], "Mat": row['materia'], "Ass": row['assunto'], "Data": row['dt_temp'].strftime('%d/%m'), "Taxa": taxa, "CSS": css}
        if delta >= 30 and not row['rev_30d']: pendencias.append({**base, "Fase": "30d", "Label": "💎 D30"})
        elif delta >= 15 and not row['rev_15d']: pendencias.append({**base, "Fase": "15d", "Label": "🧠 D15"})
        elif delta >= 7 and not row['rev_07d']: pendencias.append({**base, "Fase": "07d", "Label": "📅 D7"})
        elif delta >= 1 and not row['rev_24h']: pendencias.append({**base, "Fase": "24h", "Label": "🔥 D1"})
    return pd.DataFrame(pendencias)
def excluir_concurso_completo(supabase, nome_concurso):
    try:
        # Remove todas as matérias vinculadas a este concurso
        supabase.table("editais_materias").delete().eq("concurso", nome_concurso).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir concurso: {e}")
        return False
