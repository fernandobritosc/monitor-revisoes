import streamlit as st
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

# ============================================================================
# 🎨 DESIGN SYSTEM - TEMA MODERNO ROXO/CIANO
# ============================================================================

# Paleta de cores moderna
COLORS = {
    "primary": "#8B5CF6",      # Roxo elétrico
    "secondary": "#06B6D4",    # Ciano
    "accent": "#EC4899",       # Rosa neon
    "success": "#10B981",      # Verde neon
    "warning": "#F59E0B",      # Âmbar
    "danger": "#EF4444",       # Vermelho
    "bg_dark": "#0F0F23",      # Fundo principal
    "bg_card": "rgba(15, 15, 35, 0.7)",  # Cards
    "text_primary": "#FFFFFF",
    "text_secondary": "#94A3B8",
    "border": "rgba(139, 92, 246, 0.15)",
}

# --- FUNÇÃO: Anel circular de progresso (SVG) ---
def render_circular_progress(percentage, label, value, color_start=None, color_end=None, size=120, icon=""):
    """Renderiza um anel circular de progresso com SVG"""
    if color_start is None:
        color_start = COLORS["primary"]
    if color_end is None:
        color_end = COLORS["secondary"]
    
    # Calcular o offset do stroke (283 é a circunferência de um círculo com r=45)
    circumference = 283
    offset = circumference - (percentage / 100 * circumference)
    
    gradient_id = f"grad_{label.replace(' ', '_')}_{percentage}"
    
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 20px 15px;
            background: {COLORS['bg_card']};
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid {COLORS['border']};
            border-radius: 16px;
            min-height: 180px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        " onmouseover="this.style.borderColor='rgba(139, 92, 246, 0.5)'; this.style.boxShadow='0 0 30px rgba(139, 92, 246, 0.2)';"
        onmouseout="this.style.borderColor='{COLORS['border']}'; this.style.boxShadow='none';">
            <div style="position: relative; width: {size}px; height: {size}px; margin-bottom: 10px;">
                <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width: 100%; height: 100%;">
                    <defs>
                        <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:{color_start};stop-opacity:1" />
                            <stop offset="100%" style="stop-color:{color_end};stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <circle cx="50" cy="50" r="45" stroke="rgba(139, 92, 246, 0.1)" stroke-width="8" fill="none"/>
                    <circle cx="50" cy="50" r="45" stroke="url(#{gradient_id})" stroke-width="8" 
                            fill="none" stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
                            stroke-linecap="round" style="transition: stroke-dashoffset 1s ease;"/>
                </svg>
                <div style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                ">
                    <div style="font-size: 1.1rem; margin-bottom: 2px;">{icon}</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #fff;">{value}</div>
                </div>
            </div>
            <div style="
                color: {COLORS['text_secondary']};
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 600;
            ">{label}</div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 📄 GERAÇÃO DE RELATÓRIOS PDF
# ============================================================================

def fix_text(text):
    """
    Corrige problemas de encoding para o FPDF (Arial/Core fonts).
    Converte UTF-8 para Latin-1 e substitui caracteres não suportados.
    """
    if text is None:
        return ""
    try:
        # Normalizar para Latin-1, substituindo erros por '?'
        return str(text).encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return str(text)

class EstudoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(139, 92, 246) # Roxo
        self.cell(0, 10, fix_text('RELATÓRIO ESTRATÉGICO DE DESEMPENHO'), 0, 1, 'C')
        
        agora_br = (datetime.datetime.utcnow() - datetime.timedelta(hours=3))
        self.set_font('Arial', '', 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, fix_text(f'Gerado em: {agora_br.strftime("%d/%m/%Y %H:%M")}'), 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, fix_text(f'Página {self.page_no()}'), 0, 0, 'C')

def safe_pdf_output(pdf):
    """
    Retorna os bytes do PDF de forma segura, compatível com diferentes versões do FPDF.
    """
    try:
        # FPDF2 pode retornar bytearray ou str dependendo da versão/config
        output = pdf.output(dest='S')
        
        # Se for string (versões antigas), codifica para latin-1
        if isinstance(output, str):
            return output.encode('latin-1', 'replace')
        
        # Se for bytearray ou bytes (versões novas), converte para bytes
        return bytes(output)
    except Exception as e:
        # Fallback de emergência
        return str(e).encode('utf-8')

def gerar_pdf_estratégico(df_estudos, missao, df_bruto, proj=None):
    pdf = EstudoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Métricas
    t_q = df_estudos['total'].sum()
    a_q = df_estudos['acertos'].sum()
    precisao = (a_q / t_q * 100) if t_q > 0 else 0
    tempo_total = df_estudos['tempo'].sum() / 60
    
    # 1. RESUMO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, fix_text('1. RESUMO GERAL'), 0, 1, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(248, 248, 255)
    pdf.set_text_color(100, 100, 100)
    
    pdf.cell(95, 8, fix_text(' MISSÃO'), 1, 0, 'L', True)
    pdf.cell(95, 8, fix_text(' TEMPO TOTAL'), 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 10, f' {fix_text(missao)}', 1, 0, 'L')
    pdf.cell(95, 10, f' {tempo_total:.1f} horas', 1, 1, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(95, 8, fix_text(' QUESTÕES'), 1, 0, 'L', True)
    pdf.cell(95, 8, fix_text(' PRECISÃO'), 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 10, f' {int(t_q)}', 1, 0, 'L')
    pdf.cell(95, 10, f' {precisao:.1f}%', 1, 1, 'L')
    pdf.ln(10)
    
    # 2. MATRIZ
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, fix_text('2. MATRIZ DE PRIORIZAÇÃO'), 0, 1, 'L')
    
    df_matriz = df_estudos.groupby('materia').agg({'acertos': 'sum', 'total': 'sum'}).reset_index()
    df_matriz['taxa'] = (df_matriz['acertos'] / df_matriz['total'] * 100).fillna(0)
    media_volume = df_matriz['total'].mean() if not df_matriz.empty else 0
    
    focar = []
    manter = []
    
    for _, row in df_matriz.iterrows():
        if row['taxa'] < 75 and row['total'] >= media_volume:
            focar.append(f"{row['materia']} ({row['taxa']:.0f}%)")
        elif row['taxa'] >= 75:
            manter.append(f"{row['materia']} ({row['taxa']:.0f}%)")
            
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    
    if focar:
        pdf.set_fill_color(254, 242, 242)
        pdf.multi_cell(0, 6, fix_text(f"FOCO CRÍTICO (Prioridade Alta): {', '.join(focar)}"), 1, 'L', True)
        pdf.ln(2)
    
    if manter:
        pdf.set_fill_color(240, 253, 244)
        pdf.multi_cell(0, 6, fix_text(f"MANUTENÇÃO (Bom desempenho): {', '.join(manter)}"), 1, 'L', True)
        
    pdf.ln(5)
    
    # 3. DETALHAMENTO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, fix_text('3. DETALHAMENTO'), 0, 1, 'L')
    
    df_assuntos = df_estudos.groupby(['materia', 'assunto']).agg({'acertos': 'sum', 'total': 'sum'}).reset_index()
    df_assuntos['taxa'] = (df_assuntos['acertos'] / df_assuntos['total'] * 100).fillna(0)
    
    for _, row_mat in df_matriz.sort_values('taxa').iterrows():
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(240, 240, 245)
        pdf.set_text_color(139, 92, 246)
        pdf.cell(0, 8, f" {fix_text(row_mat['materia'])}", 1, 1, 'L', True)
        
        topicos = df_assuntos[df_assuntos['materia'] == row_mat['materia']].sort_values('taxa')
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(60, 60, 60)
        
        for _, row_ass in topicos.iterrows():
            nome = row_ass['assunto']
            # Truncar nome muito longo para evitar quebra de layout
            if len(nome) > 75: nome = nome[:72] + "..."
            
            pdf.cell(140, 6, fix_text(f"  - {nome}"), 0, 0, 'L')
            pdf.cell(0, 6, f"{row_ass['taxa']:.0f}% ({int(row_ass['total'])})", 0, 1, 'R')
        pdf.ln(2)

    return safe_pdf_output(pdf)

def gerar_pdf_carga_horaria(df, missao):
    pdf = EstudoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Métricas Globais
    minutos_totais = df['tempo'].sum()
    horas_totais = minutos_totais / 60
    
    # Calcular Matéria com Maior Dedicação (Top 1)
    df_agrup_mat = df.groupby('materia').agg({'tempo': 'sum'}).reset_index()
    if not df_agrup_mat.empty:
        top_mat = df_agrup_mat.sort_values('tempo', ascending=False).iloc[0]
        nome_top = top_mat['materia']
        horas_top = top_mat['tempo'] / 60
        pct_top = (top_mat['tempo'] / minutos_totais * 100) if minutos_totais > 0 else 0
        txt_top = f"{nome_top} ({pct_top:.1f}%)"
    else:
        txt_top = "N/A"
        
    # --- 1. DASHBOARD DE RESUMO ---
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(139, 92, 246)
    pdf.cell(0, 10, fix_text('1. DASHBOARD DE CARGA HORÁRIA'), 0, 1, 'L')
    
    # Layout de Cards em Grid
    pdf.set_fill_color(248, 250, 252) # Fundo cinza muito claro
    
    # Linha de Títulos dos Cards
    pdf.set_font('Arial', 'B', 8)
    pdf.set_text_color(148, 163, 184) # Cinza texto secundário
    pdf.cell(95, 8, fix_text("  TEMPO TOTAL ACUMULADO"), 0, 0, 'L', True)
    pdf.cell(0, 8, fix_text("  FOCO PRINCIPAL (Maior Dedicação)"), 0, 1, 'L', True)
    
    # Linha de Valores dos Cards
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(15, 23, 42) # Preto texto principal
    pdf.cell(95, 12, f"  {horas_totais:.1f}h", 0, 0, 'L', True)
    pdf.cell(0, 12, fix_text(f"  {txt_top}"), 0, 1, 'L', True)
    
    pdf.ln(8)
    
    # --- 2. RANKING DETALHADO ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(139, 92, 246)
    pdf.cell(0, 10, fix_text('2. RANKING DE DEDICAÇÃO POR MATÉRIA'), 0, 1, 'L')
    pdf.ln(2)
    
    # Agrupamento para detalhamento
    df_agrup_ass = df.groupby(['materia', 'assunto']).agg({'tempo': 'sum'}).reset_index()
    
    # Iterar sobre matérias ordenadas por tempo (Maior -> Menor)
    ranking = 1
    for _, row_mat in df_agrup_mat.sort_values('tempo', ascending=False).iterrows():
        horas_mat = row_mat['tempo'] / 60
        pct_mat = (row_mat['tempo'] / minutos_totais * 100) if minutos_totais > 0 else 0
        
        # Cabeçalho da Matéria com Totalizador
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(240, 245, 255) # Azul bem claro para destaque
        pdf.set_text_color(30, 41, 59)
        
        # Formatar texto da linha da matéria
        texto_mat = f" #{ranking} {fix_text(row_mat['materia'].upper())}"
        info_mat = f"{horas_mat:.1f}h ({pct_mat:.1f}%) "
        
        pdf.cell(140, 8, texto_mat, 1, 0, 'L', True)
        pdf.cell(0, 8, info_mat, 1, 1, 'R', True)
        
        # Detalhamento de Assuntos (também ordenado por tempo)
        assuntos_da_materia = df_agrup_ass[df_agrup_ass['materia'] == row_mat['materia']].sort_values('tempo', ascending=False)
        
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(71, 85, 105) # Cinza escuro para itens
        
        for _, row_ass in assuntos_da_materia.iterrows():
            nome_ass = row_ass['assunto']
            horas_ass = row_ass['tempo'] / 60
            # Percentual relativo à matéria
            pct_ass_relativo = (row_ass['tempo'] / row_mat['tempo'] * 100) if row_mat['tempo'] > 0 else 0
            
            # Truncar nome longo
            if len(nome_ass) > 65: nome_ass = nome_ass[:62] + "..."
            
            pdf.cell(140, 6, fix_text(f"    • {nome_ass}"), 0, 0, 'L')
            pdf.cell(0, 6, f"{horas_ass:.1f}h  ({pct_ass_relativo:.0f}%)", 0, 1, 'R')
            
        pdf.ln(3) # Espaço entre matérias
        ranking += 1
        
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(0, 5, fix_text("Este relatório apresenta a distribuição do seu tempo de estudo ordenada pela maior dedicação. Use-o para verificar se o seu tempo está alinhado com a importância das disciplinas no edital."))

    return safe_pdf_output(pdf)

def gerar_pdf_simulados(df_simulados, missao):
    pdf = EstudoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho do Relatório
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(139, 92, 246)
    pdf.cell(0, 10, fix_text(f'RELATÓRIO DE SIMULADOS - {missao}'), 0, 1, 'L')
    
    if df_simulados.empty:
        pdf.set_font('Arial', '', 12)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 10, fix_text("Nenhum simulado registrado."), 0, 1)
        return safe_pdf_output(pdf)
        
    # Painel de Resumo
    media_geral = df_simulados['taxa'].mean()
    melhor_nota = df_simulados['taxa'].max()
    total_simulados = len(df_simulados)
    
    pdf.set_fill_color(248, 250, 252)
    pdf.cell(0, 15, "", 1, 1, 'L', True) # Fundo do painel
    pdf.set_y(pdf.get_y() - 15) # Voltar cursor
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(63, 15, f" Total: {total_simulados} provas", 0, 0, 'C')
    pdf.cell(63, 15, f" Média: {media_geral:.1f}%", 0, 0, 'C')
    pdf.cell(64, 15, f" Melhor: {melhor_nota:.1f}%", 0, 1, 'C')
    pdf.ln(15)
    pdf.ln(5)
    
    # Histórico Detalhado
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(139, 92, 246)
    pdf.cell(0, 10, fix_text('HISTÓRICO DETALHADO'), 0, 1, 'L')
    
    # Cabeçalho da Tabela
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(30, 8, " DATA", 1, 0, 'L', True)
    pdf.cell(90, 8, " PROVA / BANCA", 1, 0, 'L', True)
    pdf.cell(30, 8, " ACERTOS", 1, 0, 'C', True)
    pdf.cell(40, 8, " NOTA FINAL", 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(60, 60, 60)
    
    # Linhas da tabela
    for _, row in df_simulados.sort_values('data_estudo', ascending=False).iterrows():
        dt = pd.to_datetime(row['data_estudo']).strftime('%d/%m/%Y')
        nome = row['assunto']
        if len(nome) > 45: nome = nome[:42] + "..."
        acertos = f"{int(row['acertos'])}/{int(row['total'])}"
        nota = f"{row['taxa']:.1f}%"
        
        pdf.cell(30, 8, f" {dt}", 1, 0, 'L')
        pdf.cell(90, 8, fix_text(f" {nome}"), 1, 0, 'L')
        pdf.cell(30, 8, f" {acertos}", 1, 0, 'C')
        
        # Colorir notas altas/baixas
        if row['taxa'] >= 80:
            pdf.set_text_color(22, 163, 74) # Verde
            pdf.set_font('Arial', 'B', 9)
        elif row['taxa'] < 60:
            pdf.set_text_color(220, 38, 38) # Vermelho
        
        pdf.cell(40, 8, f" {nota}", 1, 1, 'C')
        
        # Resetar fonte
        pdf.set_text_color(60, 60, 60)
        pdf.set_font('Arial', '', 9)
        
    return safe_pdf_output(pdf)

def render_metric_card_modern(label, value, icon="📊", color=None, subtitle=None):
    """Renderiza cartões de métricas modernos com glassmorphism"""
    if color is None:
        color = COLORS["primary"]
    
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 24px 20px;
            background: {COLORS['bg_card']};
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid {COLORS['border']};
            border-radius: 16px;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        " onmouseover="this.style.borderColor='rgba(139, 92, 246, 0.5)'; this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 40px rgba(139, 92, 246, 0.15)';"
        onmouseout="this.style.borderColor='{COLORS['border']}'; this.style.transform='translateY(0)'; this.style.boxShadow='none';">
            <div style="
                font-size: 2rem;
                margin-bottom: 8px;
                filter: drop-shadow(0 0 10px {color}40);
            ">{icon}</div>
            <div style="
                color: {COLORS['text_secondary']};
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                margin-bottom: 8px;
                font-weight: 600;
            ">{label}</div>
            <div style="
                font-size: 2rem;
                font-weight: 800;
                background: linear-gradient(135deg, {color}, {COLORS['secondary']});
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1;
            ">{value}</div>
            {f'<div style="color: {COLORS["text_secondary"]}; font-size: 0.75rem; margin-top: 6px;">{subtitle}</div>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)

# --- FUNÇÃO LEGADO: mantida para compatibilidade ---
def render_metric_card_simple(label, value, help_text=None):
    """Renderiza cartões de métricas (agora usa o design moderno)"""
    render_metric_card_modern(label, value, icon="📊", subtitle=help_text)

def render_metric_card(label, value, icon="📊"):
    """Função legado - agora usa design moderno"""
    render_metric_card_modern(label, value, icon)

# --- FUNÇÃO: Barra de progresso moderna ---
def render_progress_bar(percentage, height=8, color_start=None, color_end=None):
    """Renderiza uma barra de progresso com gradiente moderno"""
    if color_start is None:
        color_start = COLORS["primary"]
    if color_end is None:
        color_end = COLORS["secondary"]
    
    st.markdown(f"""
        <div style="
            width: 100%;
            background-color: rgba(139, 92, 246, 0.1);
            border-radius: 10px;
            height: {height}px;
            margin: 8px 0;
            overflow: hidden;
        ">
            <div style="
                height: 100%;
                border-radius: 10px;
                background: linear-gradient(90deg, {color_start}, {color_end});
                width: {min(percentage, 100)}%;
                transition: width 0.5s ease;
                box-shadow: 0 0 10px {color_start}40;
            "></div>
        </div>
    """, unsafe_allow_html=True)


# --- FUNÇÃO: Barra de progresso moderna ---
def render_consistency_heatmap(df):
    """Renderiza um mapa de calor estilo GitHub para constância de estudos (Últimos 6 meses)"""
    if df.empty:
        st.info("📚 Estude seu primeiro tópico para começar a preencher seu mapa de constância!")
        return

    # Preparar dados: Soma de minutos por data
    df_day = df.groupby('data_estudo')['tempo'].sum().reset_index()
    df_day['data_estudo'] = pd.to_datetime(df_day['data_estudo']).dt.date
    
    # Criar dict para busca rápida
    data_map = dict(zip(df_day['data_estudo'], df_day['tempo']))
    
    # Gerar range de datas (últimos 180 dias)
    hoje = get_br_date()
    datas = [hoje - timedelta(days=x) for x in range(180, -1, -1)]
    
    # Organizar por semanas para o grid (transposto: colunas são semanas)
    # Precisamos de 7 linhas (seg a dom)
    rows = [[] for _ in range(7)]
    for d in datas:
        rows[d.weekday()].append(d)
        
    # Cores
    COLOR_EMPTY = "rgba(255, 255, 255, 0.05)"
    COLORS_INTENS = [
        "rgba(139, 92, 246, 0.2)", # Nível 1 (Pouco)
        "rgba(139, 92, 246, 0.5)", # Nível 2
        "rgba(139, 92, 246, 0.8)", # Nível 3
        "#8B5CF6"                  # Nível 4 (Muito)
    ]
    
    html = '<div style="display: flex; gap: 3px; overflow-x: auto; padding-bottom: 15px; mask-image: linear-gradient(to right, black 85%, transparent);">'
    
    # Renderizar colunas (Semanas)
    num_weeks = len(rows[0])
    for w in range(num_weeks):
        html += '<div style="display: flex; flex-direction: column; gap: 3px;">'
        for r in range(7):
            if w < len(rows[r]):
                d = rows[r][w]
                tempo = data_map.get(d, 0)
                
                # Definir cor baseada no tempo (minutos)
                if tempo == 0: color = COLOR_EMPTY
                elif tempo < 120: color = COLORS_INTENS[0]
                elif tempo < 240: color = COLORS_INTENS[1]
                elif tempo < 480: color = COLORS_INTENS[2]
                else: color = COLORS_INTENS[3]
                
                tip = f"{d.strftime('%d/%m')}: {tempo/60:.1f}h"
                html += f'<div title="{tip}" style="width: 12px; height: 12px; background-color: {color}; border-radius: 2px;"></div>'
        html += '</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# --- FUNÇÃO ADICIONADA: Fuso Horário Brasília ---
def get_br_date():
    """Retorna a data atual no fuso horário de Brasília (UTC-3)."""
    return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()

# --- FUNÇÃO ADICIONADA: Conversor de tempo ---
def formatar_tempo_para_bigint(tempo_str):
    """Converte string HHMM para minutos inteiros."""
    try:
        tempo_str = str(tempo_str).strip()
        if len(tempo_str) == 4:
            horas = int(tempo_str[:2])
            minutos = int(tempo_str[2:])
            return horas * 60 + minutos
        elif len(tempo_str) == 3:
            horas = int(tempo_str[0])
            minutos = int(tempo_str[1:])
            return horas * 60 + minutos
        else:
            return int(tempo_str)  # Já em minutos
    except (ValueError, TypeError, AttributeError):
        return 0

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="Monitor de Revisões Pro", layout="wide", initial_sidebar_state="expanded")

# --- INTEGRAÇÃO: SUPABASE ---
from supabase import create_client, Client

# Credenciais do Supabase (Hardcoded para arquivo único)
SUPABASE_URL = "https://dyxtalcvjcprmhuktyfd.supabase.co"
SUPABASE_KEY = "sb_secret_uEyhPGa8T-JUw0X1m5JyOA_PygMIKW3"

def init_supabase():
    url = SUPABASE_URL
    key = SUPABASE_KEY
    
    if not url or not key:
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar ao Supabase: {e}")
        return None

try:
    supabase: Client = init_supabase()
except Exception:
    supabase = None

# --- INTEGRAÇÃO: LÓGICA ---
def get_editais(supabase):
    if not supabase: return {}
    try:
        response = supabase.table("editais_materias").select("*").execute()
        data = response.data
        editais = {}
        if data:
            for item in data:
                concurso = item.get("concurso")
                if not concurso: continue
                if concurso not in editais:
                    editais[concurso] = {
                        "cargo": item.get("cargo", ""),
                        "data_prova": item.get("data_prova"),
                        "materias": {}
                    }
                materia = item.get("materia")
                topicos = item.get("topicos", [])
                if materia:
                    editais[concurso]["materias"][materia] = topicos
        return editais
    except Exception:
        return {}

def excluir_concurso_completo(supabase, missao):
    if not supabase or not missao: return False
    try:
        supabase.table("registros_estudos").delete().eq("concurso", missao).execute()
        supabase.table("editais_materias").delete().eq("concurso", missao).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir concurso: {e}")
        return False

# --- INTEGRAÇÃO: ESTILOS ---
def apply_styles():
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .badge-green { background-color: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-red { background-color: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-gray { background-color: rgba(148, 163, 184, 0.2); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); }
        .badge-yellow { background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.3); }
        .modern-progress-container { width: 100%; background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; height: 6px; overflow: hidden; }
        .modern-progress-fill { height: 100%; background: linear-gradient(90deg, #8B5CF6, #06B6D4); border-radius: 10px; transition: width 0.5s ease; }
        </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO OBRIGATÓRIA (ÚNICA) ---
if 'missao_ativa' not in st.session_state:
    # Padrão Automático: tenta carregar a primeira missão disponível
    try:
        ed = get_editais(supabase)
        if ed:
            st.session_state.missao_ativa = list(ed.keys())[0]
        else:
            st.session_state.missao_ativa = None
    except Exception:
        st.session_state.missao_ativa = None

if 'nota_corte_alvo' not in st.session_state:
    st.session_state.nota_corte_alvo = 80

# Helper function to load all data
def carregar_dados():
    if not supabase:
        return {}, pd.DataFrame()
    try:
        # Load editais
        editais_data = get_editais(supabase)
        
        # Load all study records for the active mission
        if st.session_state.missao_ativa:
            response = supabase.table("registros_estudos").select("*").eq("concurso", st.session_state.missao_ativa).order("data_estudo", desc=True).execute()
            df_raw = pd.DataFrame(response.data)
        else:
            df_raw = pd.DataFrame()
        
        return editais_data, df_raw
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar dados - {e}")
        return {}, pd.DataFrame()

# Carregar dados
dados, df_raw = carregar_dados()

# --- INTEGRAÇÃO: SEPARAÇÃO DE ESTUDOS vs SIMULADOS ---
if not df_raw.empty:
    # Garantir que a coluna 'materia' existe e tratar nulos
    if 'materia' in df_raw.columns:
        df_raw['materia'] = df_raw['materia'].fillna("Desconhecido")
        
        # Filtros Flexíveis para Simulados (Insensível a maiúsculas e variações)
        simulado_mask = df_raw['materia'].str.upper().str.contains('SIMULADO', na=False)
        df_simulados = df_raw[simulado_mask].copy()
        df_estudos = df_raw[~simulado_mask].copy()
    else:
        df_simulados = pd.DataFrame()
        df_estudos = df_raw.copy()
else:
    df_simulados = pd.DataFrame()
    df_estudos = pd.DataFrame()

# Alias para compatibilidade com código existente (que usa 'df')
# ONDE O CÓDIGO USA 'df', ELE DEVE USAR 'df_estudos' AGORA PARA MÉTRICAS DE ROTINA
df = df_estudos 

# Definir Missão Ativa
if not dados.get('missoes'):
    if 'missao_ativa' not in st.session_state:
        try:
            ed = get_editais(supabase)
            if ed:
                st.session_state.missao_ativa = list(ed.keys())[0]
            else:
                st.session_state.missao_ativa = None
        except Exception:
            st.session_state.missao_ativa = None

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

if 'edit_id_simulado' not in st.session_state:
    st.session_state.edit_id_simulado = None

# Inicializar estados das metas semanais
if 'meta_horas_semana' not in st.session_state:
    st.session_state.meta_horas_semana = 22

if 'meta_questoes_semana' not in st.session_state:
    st.session_state.meta_questoes_semana = 350

# Inicializar estados para controle de interface
if 'editando_metas' not in st.session_state:
    st.session_state.editando_metas = False

if 'checklist_status' not in st.session_state:
    st.session_state.checklist_status = {}

if 'missao_semanal_status' not in st.session_state:
    st.session_state.missao_semanal_status = "PLANEJAMENTO"

if 'renomear_materia' not in st.session_state:
    st.session_state.renomear_materia = {}

# Aplicar estilos base
apply_styles()

# CSS Customizado para Layout Moderno - TEMA ROXO/CIANO
st.markdown("""
    <style>
    /* Importar Fontes: Inter e Montserrat */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Montserrat:wght@400;500;600;700;800&display=swap');
    
    /* Variáveis de cores - TEMA FUTURISTA PREMIUM */
    :root {
        --primary: #8B5CF6;
        --secondary: #00FFFF; /* Ciano Neon */
        --accent: #EC4899;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --bg-dark: #0E1117; /* Cinza Oceano Profundo */
        --bg-card: rgba(15, 15, 35, 0.7);
        --text-primary: #FFFFFF;
        --text-secondary: #94A3B8;
        --border-glow: rgba(0, 255, 255, 0.1);
        --sidebar-bg: #0E1117; 
        --sidebar-border: 1px solid rgba(0, 255, 255, 0.1);
    }
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', 'Inter', sans-serif;
    }
    
    /* Fundo principal */
    .stApp {
        background: #0E1117;
    }
    
    /* CORREÇÃO DO LAYOUT EXPANSÍVEL */
    /* Quando a sidebar está EXPANDIDA */
    [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
        max-width: calc(100% - 300px) !important;
        margin-left: 300px !important;
        padding-left: 4rem !important;
        padding-right: 4rem !important;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    
    /* Quando a sidebar está RECOLHIDA (Minimizada) */
    [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
        max-width: 95% !important; 
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    
    /* Container principal padrão */
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        transition: all 0.3s ease;
    }

    /* Cards Glassmorphism Modernos */
    .modern-card {
        background: rgba(14, 17, 23, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(139, 92, 246, 0.1);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .modern-card:hover {
        border-color: rgba(0, 255, 255, 0.3);
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }

    /* Títulos Uppercase e Letter Spacing */
    .main-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 2.5rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2px;
        background: linear-gradient(135deg, #FFFFFF 0%, #00FFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
    }
    
    .section-subtitle {
        color: #94A3B8;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
        margin-bottom: 2rem;
    }

    /* Sidebar Futurista */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        background-image: none !important;
        border-right: var(--sidebar-border) !important;
        min-width: 300px !important;
        width: 300px !important;
    }
    
    /* Remover elementos padrão da sidebar */
    .stSidebarUserContent {
        padding-top: 2rem;
    }

    /* Estilização das TABS (Abas) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 15, 35, 0.5);
        padding: 8px;
        border-radius: 14px;
        border: 1px solid rgba(139, 92, 246, 0.1);
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 10px;
        color: #94A3B8;
        font-weight: 600;
        border: none !important;
        transition: all 0.3s ease;
        padding: 0 20px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #FFFFFF;
        background-color: rgba(139, 92, 246, 0.1);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #8B5CF6, #06B6D4) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
    }
    
    /* Botões Modernos */
    .stButton>button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2)) !important;
        color: #FFFFFF !important;
    }
    .stButton>button:hover {
        border-color: rgba(139, 92, 246, 0.6) !important;
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.3) !important;
        transform: translateY(-2px);
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #8B5CF6, #06B6D4) !important;
        border: none !important;
    }
    
    /* Inputs Modernos */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 12px !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        background: rgba(15, 15, 35, 0.8) !important;
        color: #FFFFFF !important;
    }
    
    /* Tabela de Disciplinas Moderna */
    .disciplina-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        background: rgba(15, 15, 35, 0.5);
        border-radius: 12px;
        overflow: hidden;
    }
    
    .disciplina-table thead {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.1));
    }
    
    .disciplina-table th {
        text-align: left;
        padding: 18px 15px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.15);
        background: linear-gradient(135deg, #8B5CF6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 1px;
    }
    
    .disciplina-table td {
        padding: 16px 15px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.08);
        color: #fff;
        font-size: 0.95rem;
    }
    
    .disciplina-table tr:hover {
        background-color: rgba(139, 92, 246, 0.08);
    }
    
    .disciplina-table tr:last-child td {
        border-bottom: none;
    }
    
    /* Metas Cards Modernos */
    .meta-card {
        background: rgba(15, 15, 35, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 16px;
        padding: 28px;
        text-align: center;
        height: 100%;
        position: relative;
        transition: all 0.3s ease;
    }
    .meta-card:hover {
        border-color: rgba(139, 92, 246, 0.4);
        box-shadow: 0 0 30px rgba(139, 92, 246, 0.15);
    }
    
    .meta-title {
        color: #94A3B8;
        font-size: 0.9rem;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
    
    .meta-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #8B5CF6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 15px 0;
    }
    
    .meta-progress {
        margin-top: 20px;
    }
    
    .meta-subtitle {
        color: #06B6D4;
        font-size: 0.9rem;
        margin-top: 10px;
        font-weight: 500;
    }
    
    /* Modal de Configuração */
    .meta-modal {
        background: rgba(15, 15, 35, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 16px;
        padding: 28px;
        margin-top: 20px;
    }
    
    /* Streak Card Moderno */
    .streak-card {
        background: rgba(15, 15, 35, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 16px;
        padding: 28px;
        margin: 20px 0;
    }
    
    .streak-title {
        color: #94A3B8;
        font-size: 1.2rem;
        margin-bottom: 15px;
        font-weight: 600;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .streak-value-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 20px 0;
        gap: 20px;
    }
    
    .streak-value-box {
        flex: 1;
        text-align: center;
        padding: 24px;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(6, 182, 212, 0.08));
        border-radius: 16px;
        border: 1px solid rgba(139, 92, 246, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    .streak-value-box:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.2);
    }
    
    .streak-value-label {
        color: #06B6D4;
        font-size: 0.9rem;
        margin-bottom: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .streak-value-number {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #8B5CF6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0;
    }
    
    .streak-period {
        color: #94A3B8;
        font-size: 0.9rem;
        margin-top: 15px;
        text-align: center;
        background: rgba(139, 92, 246, 0.1);
        padding: 10px 18px;
        border-radius: 10px;
        display: inline-block;
    }
    
    /* Filtros modernos */
    .stSegmentedControl {
        margin-bottom: 10px;
    }
    
    /* Seção de Constância Moderna */
    .constancia-section {
        margin-top: 30px;
        padding: 28px;
        background: linear-gradient(135deg, rgba(15, 15, 35, 0.9), rgba(15, 15, 35, 0.7));
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(139, 92, 246, 0.2);
        box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    }
    
    .constancia-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.15);
    }
    
    .constancia-title {
        color: #fff;
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #8B5CF6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .streak-value-container {
            flex-direction: column;
            gap: 15px;
        }
        
        .streak-value-box {
            width: 100%;
        }
    }
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(15, 15, 35, 0.5);
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #8B5CF6, #06B6D4);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #8B5CF6;
    }
    
    /* Expanders modernos */
    .streamlit-expanderHeader {
        background: rgba(139, 92, 246, 0.1) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(139, 92, 246, 0.15) !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: rgba(139, 92, 246, 0.3) !important;
    }
    
    /* Dividers */
    hr {
        border-color: rgba(139, 92, 246, 0.15) !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    </style>
""", unsafe_allow_html=True)

# --- NOVA FUNÇÃO: Processar assuntos em massa ---
def processar_assuntos_em_massa(texto, separador=";"):
    """
    Processa um texto com múltiplos assuntos separados por um separador.
    Retorna uma lista limpa de assuntos.
    """
    if not texto:
        return []
    
    # Remove espaços em branco no início e fim
    texto = texto.strip()
    
    # Processa baseado no separador
    if separador == ";":
        assuntos = texto.split(";")
    elif separador == ",":
        assuntos = texto.split(",")
    elif separador == "linha":
        # Divide por quebras de linha
        assuntos = texto.split("\n")
    elif separador == "ponto":
        # Divide por ponto
        assuntos = texto.split(".")
    else:
        assuntos = [texto]
    
    # Limpa cada assunto
    assuntos_limpos = []
    for assunto in assuntos:
        assunto = assunto.strip()
        # Remove caracteres especiais no início/fim
        assunto = re.sub(r'^[^a-zA-Z0-9]*|[^a-zA-Z0-9]*$', '', assunto)
        if assunto:  # Só adiciona se não estiver vazio
            assuntos_limpos.append(assunto)
    
    return assuntos_limpos

# --- 2. FUNÇÕES AUXILIARES ---
def calcular_countdown(data_str):
    if not data_str: return None, "#adb5bd"
    try:
        dias = (pd.to_datetime(data_str).date() - datetime.date.today()).days
        cor = "#FF4B4B" if dias <= 7 else "#FFD700" if dias <= 30 else "#00FF00"
        return dias, cor
    except (ValueError, TypeError, AttributeError):
        return None, "#adb5bd"

# Formata minutos em '2h 15m'
def formatar_minutos(minutos_totais):
    try:
        minutos = int(minutos_totais)
    except (ValueError, TypeError):
        return "0m"
    horas = minutos // 60
    minutos_rest = minutos % 60
    if horas > 0:
        return f"{horas}h{minutos_rest:02d}min"
    return f"{minutos_rest}min"

def formatar_horas_minutos(minutos_totais):
    """Formata minutos para 'Xh YYmin'"""
    try:
        minutos = int(minutos_totais)
    except (ValueError, TypeError):
        return "0h00min"
    horas = minutos // 60
    minutos_rest = minutos % 60
    return f"{horas}h{minutos_rest:02d}min"

def get_badge_cor(taxa):
    """Retorna classe CSS simples para badges baseado na taxa (0-100)."""
    try:
        t = float(taxa)
    except (ValueError, TypeError):
        return "badge-gray"
    if t >= 80:
        return "badge-green"
    if t >= 60:
        return "badge-gray"
    return "badge-red"

def calcular_streak(df):
    """Calcula dias consecutivos até hoje baseado na coluna 'data_estudo'."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
    except (ValueError, TypeError, KeyError):
        return 0
    dias = set(datas)
    streak = 0
    hoje = datetime.date.today()
    alvo = hoje
    while alvo in dias:
        streak += 1
        alvo = alvo - datetime.timedelta(days=1)
    return streak

def calcular_recorde_streak(df):
    """Calcula o maior streak (record) já alcançado."""
    if df is None or df.empty:
        return 0
    if 'data_estudo' not in df.columns:
        return 0
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().sort_values().unique()
    except (ValueError, TypeError, KeyError):
        return 0
    
    if len(datas) == 0:
        return 0
    
    recorde = 0
    streak_atual = 1
    
    for i in range(1, len(datas)):
        diferenca = (datas[i] - datas[i-1]).days
        if diferenca == 1:
            streak_atual += 1
        else:
            recorde = max(recorde, streak_atual)
            streak_atual = 1
    
    return max(recorde, streak_atual)

def calcular_datas_streak(df):
    """Calcula as datas de início e fim do streak atual."""
    if df is None or df.empty:
        return None, None
    if 'data_estudo' not in df.columns:
        return None, None
    
    try:
        datas = pd.to_datetime(df['data_estudo']).dt.date.dropna().unique()
        datas = sorted(datas, reverse=True)  # Mais recentes primeiro
    except (ValueError, TypeError, KeyError):
        return None, None
    
    if not datas:
        return None, None
    
    hoje = datetime.date.today()
    streak = calcular_streak(df)
    
    if streak == 0:
        return None, None
    
    fim_streak = hoje - datetime.timedelta(days=1)
    inicio_streak = fim_streak - datetime.timedelta(days=streak-1)
    
    return inicio_streak, fim_streak

def calcular_estudos_semana(df):
    """Calcula o total de horas e questões da semana atual."""
    if df is None or df.empty:
        return 0, 0
    
    hoje = datetime.date.today()
    inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())  # Segunda-feira
    fim_semana = inicio_semana + datetime.timedelta(days=6)  # Domingo
    
    try:
        df['data_estudo_date'] = pd.to_datetime(df['data_estudo']).dt.date
        df_semana = df[(df['data_estudo_date'] >= inicio_semana) & (df['data_estudo_date'] <= fim_semana)]
        
        horas_semana = df_semana['tempo'].sum() / 60
        questoes_semana = df_semana['total'].sum()
        
        return horas_semana, questoes_semana
    except (ValueError, TypeError, KeyError):
        return 0, 0

def calcular_projecao_conclusao(df, dados_edital):
    """
    Calcula o ritmo de estudo e projeta a data de conclusão do edital.
    """
    if not dados_edital or 'materias' not in dados_edital:
        return None
    
    # 1. Total de Tópicos no Edital
    total_topicos = 0
    for materia, topicos in dados_edital['materias'].items():
        total_topicos += len(topicos)
    
    if total_topicos == 0:
        return None
        
    # 2. Tópicos Estudados (Únicos)
    if df.empty:
        estudados = 0
    else:
        # Consideramos apenas tópicos que existem no edital atual
        todos_topicos_edital = []
        for materia, topicos in dados_edital['materias'].items():
            todos_topicos_edital.extend(topicos)
        
        # Filtra registros que batem com o edital e conta únicos
        estudados = df[df['assunto'].isin(todos_topicos_edital)]['assunto'].nunique()
    
    restantes = total_topicos - estudados
    progresso_pct = (estudados / total_topicos * 100) if total_topicos > 0 else 0
    
    # 3. Ritmo (Pace)
    if df.empty or estudados == 0:
        return {
            "total": total_topicos, "estudados": estudados, "restantes": restantes,
            "progresso": progresso_pct, "ritmo": 0, "dias_para_fim": None, "data_fim": None
        }
    
    # Ritmo nos últimos 30 dias (mais realista que o histórico total)
    hoje = get_br_date()
    inicio_janela = hoje - timedelta(days=30)
    df_recente = df[pd.to_datetime(df['data_estudo']).dt.date >= inicio_janela]
    
    if len(df_recente) < 5: # Se tiver pouco dado recente, usa histórico total
        data_inicio = pd.to_datetime(df['data_estudo']).min().date()
        dias_totais = max((hoje - data_inicio).days, 1)
        ritmo_diario = estudados / dias_totais
    else:
        topicos_30d = df_recente['assunto'].nunique()
        ritmo_diario = topicos_30d / 30
    
    # Garantir ritmo mínimo para não dividir por zero
    ritmo_diario = max(ritmo_diario, 0.01)
    
    dias_para_fim = int(restantes / ritmo_diario)
    data_fim = hoje + timedelta(days=dias_para_fim)
    
    return {
        "total": total_topicos,
        "estudados": estudados,
        "restantes": restantes,
        "progresso": progresso_pct,
        "ritmo": ritmo_diario * 7, # Tópicos por semana para exibição
        "dias_para_fim": dias_para_fim,
        "data_fim": data_fim
    }

# --- FUNÇÃO REMOVIDA: gerar_calendario_estudos (bolinhas) ---

# --- FUNÇÃO REMOVIDA: gerar_numeros_mes (1-31) ---
# A função gerar_numeros_mes foi REMOVIDA por solicitação

# --- NOVA FUNÇÃO: Cálculo dinâmico de intervalos ---
def calcular_proximo_intervalo(dificuldade, taxa_acerto):
    """
    Calcula o próximo intervalo de revisão baseado na dificuldade e desempenho.
    
    Fácil:   → 15 ou 20 dias (aproveita ciclos longos)
    Médio:   → 7 dias (padrão confiável)
    Difícil: → 3 dias se acerto < 70%, senão 5
    """
    if dificuldade == "🟢 Fácil":
        return 15 if taxa_acerto > 80 else 7
    elif dificuldade == "🟡 Médio":
        return 7
    else:  # 🔴 Difícil
        return 3 if taxa_acerto < 70 else 5

def tempo_recomendado_rev24h(dificuldade):
    """Retorna tempo sugerido para revisão de 24h (em minutos)."""
    tempos = {
        "🟢 Fácil": (2, "Apenas releitura rápida dos títulos"),
        "🟡 Médio": (8, "Revise seus grifos + 5 questões"),
        "🔴 Difícil": (18, "Active Recall completo + questões-chave")
    }
    return tempos.get(dificuldade, (5, "Padrão"))

# --- FUNÇÃO COM CACHE PARA PERFORMANCE ---
@st.cache_data(ttl=300)
def calcular_revisoes_pendentes(df_estudos, filtro_rev, filtro_dif):
    """Calcula revisões pendentes com cache para melhor performance."""
    hoje = get_br_date()
    pend = []
    
    if df_estudos.empty:
        return pend
        
    for _, row in df_estudos.iterrows():
        dt_est = pd.to_datetime(row['data_estudo']).date()
        dias = (hoje - dt_est).days
        tx = row.get('taxa', 0)
        dif = row.get('dificuldade', '🟡 Médio')
        
        # Lógica de Revisão 24h
        if not row.get('rev_24h', False):
            dt_prev = dt_est + timedelta(days=1)
            if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                atraso = (hoje - dt_prev).days
                pend.append({
                    "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                    "tipo": "Revisão 24h", "col": "rev_24h", "atraso": atraso, 
                    "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                    "dificuldade": dif, "taxa": tx, "relevancia": row.get('relevancia', 5)
                })
        
        # Lógica de Ciclos Longos (ADAPTATIVA) - CORRIGIDA: remove o elif problemático
        else:  # rev_24h = True
            intervalo = calcular_proximo_intervalo(dif, tx)
            
            # Determinar qual coluna atualizar
            if intervalo <= 7:
                col_alv, lbl = "rev_07d", f"Revisão {intervalo}d"
            else:  # 15+ dias
                col_alv, lbl = "rev_15d", f"Revisão {intervalo}d"
            
            if not row.get(col_alv, False):
                dt_prev = dt_est + timedelta(days=intervalo)
                if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                    atraso = (hoje - dt_prev).days
                    pend.append({
                        "id": row['id'], "materia": row['materia'], "assunto": row['assunto'], 
                        "tipo": lbl, "col": col_alv, "atraso": atraso, 
                        "data_prevista": dt_prev, "coment": row.get('comentarios', ''),
                        "dificuldade": dif, "taxa": tx, "relevancia": row.get('relevancia', 5)
                    })
    
    # Filtrar por dificuldade
    if filtro_dif != "Todas":
        pend = [p for p in pend if p['dificuldade'] == filtro_dif]
    
    return pend

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if st.session_state.missao_ativa is None:
    st.markdown('<h1 class="main-title">🎯 Central de Comando</h1>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Selecione sua missão ou inicie um novo ciclo</p>', unsafe_allow_html=True)
    
    ed = get_editais(supabase)
    tabs = st.tabs(["🚀 Missões Ativas", "➕ Novo Cadastro"])
    
    with tabs[0]:
        if not ed: 
            st.info("Nenhuma missão ativa no momento.")
        else:
            cols = st.columns(2)
            for i, (nome, d_concurso) in enumerate(ed.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div class="modern-card">
                            <h3 style="margin:0; background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{nome}</h3>
                            <p style="color:#94A3B8; font-size:0.9rem; margin-bottom:15px;">{d_concurso['cargo']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Acessar Missão", key=f"ac_{nome}", use_container_width=True, type="primary"):
                        st.session_state.missao_ativa = nome
                        st.rerun()
    
    with tabs[1]:
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("##### Cadastrar Novo Concurso/Edital")
        with st.form("form_novo_concurso", clear_on_submit=True):
            nome_concurso = st.text_input("Nome do Concurso", placeholder="Ex: Receita Federal, TJ-SP, etc.")
            cargo_concurso = st.text_input("Cargo", placeholder="Ex: Auditor Fiscal, Escrevente, etc.")
            informar_data_prova = st.checkbox("Informar data da prova (opcional)")
            if informar_data_prova:
                data_prova_input = st.date_input("Data da Prova")
            else:
                data_prova_input = None
            
            btn_cadastrar = st.form_submit_button("🚀 INICIAR MISSÃO", use_container_width=True, type="primary")
            
            if btn_cadastrar:
                if nome_concurso and cargo_concurso:
                    try:
                        payload = {
                            "concurso": nome_concurso,
                            "cargo": cargo_concurso,
                            "materia": "Geral",
                            "topicos": ["Introdução"]
                        }
                        if data_prova_input:
                            payload["data_prova"] = data_prova_input.strftime("%Y-%m-%d")
                        res_ins = supabase.table("editais_materias").insert(payload).execute()
                        # confirmar inserção
                        try:
                            check = supabase.table("editais_materias").select("data_prova").eq("concurso", nome_concurso).execute()
                            if check.data and len(check.data) > 0:
                                st.success(f"✅ Missão '{nome_concurso}' criada com sucesso!")
                                time.sleep(1)
                                st.session_state.missao_ativa = nome_concurso
                                st.rerun()
                            else:
                                st.warning("Missão criada, mas não foi possível confirmar 'data_prova' no banco. Verifique o supabase.")
                        except Exception:
                            st.success(f"✅ Missão '{nome_concurso}' criada (não foi possível confirmar via consulta).")
                            time.sleep(1)
                            st.session_state.missao_ativa = nome_concurso
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
                else:
                    st.warning("⚠️ Por favor, preencha o nome e o cargo.")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    missao = st.session_state.missao_ativa
    # The `df` variable is now `df_estudos` due to the alias
    # `dados` is already loaded by `carregar_dados()`
    
    # --- IMPORTANTE: BUSCA DIRETA DA DATA DA PROVA DO BANCO ---
    try:
        data_prova_direta = dados.get(missao, {}).get('data_prova')
    except Exception as e:
        # Log silencioso do erro, mas continua funcionando
        data_prova_direta = None
        
    # Garantir que 'dados' se refere à missão ativa
    dados_global = dados
    dados = dados_global.get(missao, {})

    with st.sidebar:
        # Logo Estilizado Moderno e Genérico
        st.markdown("""
            <div style='text-align: center; padding: 15px 0 30px 0;'>
                <div style='
                    background: rgba(255, 255, 255, 0.1); 
                    width: 60px; 
                    height: 60px; 
                    border-radius: 16px; 
                    margin: 0 auto 15px auto;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                '>
                    <span style='font-size: 30px;'>🎯</span>
                </div>
                <h1 style='color: white; font-family: "Inter", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0; letter-spacing: -0.5px; line-height: 1.2;'>
                    MONITOR<span style='color: #1a1a2e; background: #fff; padding: 0 6px; border-radius: 6px; margin-left: 4px; font-size: 1.4rem; vertical-align: middle;'>PRO</span>
                </h1>
                <p style='color: rgba(255,255,255,0.7); font-size: 0.75rem; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px; font-weight: 500;'>
                    Alta Performance
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Menu Premium com option_menu
        menu_selecionado = option_menu(
            menu_title=None,
            options=["HOME", "GUIA SEMANAL", "REVISÕES", "REGISTRAR", "DASHBOARD", "SIMULADOS", "HISTÓRICO", "RELATÓRIOS", "CONFIGURAR"],
            icons=["house", "calendar3", "arrow-repeat", "pencil-square", "graph-up-arrow", "trophy", "clock-history", "file-earmark-pdf", "gear"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#94A3B8", "font-size": "16px"}, 
                "nav-link": {
                    "font-family": "Montserrat, sans-serif",
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "6px 15px",
                    "padding": "12px 20px",
                    "border-radius": "30px",
                    "--hover-color": "rgba(255, 255, 255, 0.03)",
                    "font-weight": "500",
                    "color": "#94A3B8",
                    "transition": "all 0.3s ease"
                },
                "nav-link-selected": {
                    "background": "linear-gradient(90deg, #8B5CF6, #06B6D4)",
                    "color": "#fff",
                    "font-weight": "700",
                    "box-shadow": "0 4px 15px rgba(139, 92, 246, 0.3)",
                    "border": "none",
                },
            }
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # REMOVIDO: Navegação por páginas (1-6) - Conforme solicitado
        
        # Mapeamento do Menu (Opção UI -> Estado Interno)
        mapa_menu = {
            "HOME": "Home",
            "GUIA SEMANAL": "Guia Semanal",
            "REVISÕES": "Revisões",
            "REGISTRAR": "Registrar",
            "DASHBOARD": "Dashboard",
            "SIMULADOS": "Simulados",
            "HISTÓRICO": "Histórico",
            "RELATÓRIOS": "Relatórios",
            "CONFIGURAR": "Configurar"
        }
        
        menu = mapa_menu.get(menu_selecionado, "Home")

    # --- ABA: HOME (PAINEL GERAL) ---
    if menu == "Home":
        # Header compacto com título e botão de trocar missão
        col_titulo, col_btn = st.columns([5, 1])
        
        with col_titulo:
            st.markdown(f'<h1 style="background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size:2rem; margin-bottom:0;">{missao}</h1>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#94A3B8; font-size:1rem; margin-bottom:0;">{dados.get(missao, {}).get("cargo", "")}</p>', unsafe_allow_html=True)
        
        with col_btn:
            st.write("")  # Espaçamento vertical
            if st.button("🔄 Trocar", key="btn_trocar_missao", help="Voltar à Central de Comando para selecionar outra missão", use_container_width=True):
                st.session_state.missao_ativa = None
                st.rerun()
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
        
        if df_estudos.empty:
            st.info("Ainda não há registros. Faça seu primeiro estudo para preencher o painel.")
        else:
            # --- VISÃO DO MÊS ATUAL (como na imagem) ---
            st.markdown('<div class="visao-mes-title">VISÃO DO MÊS ATUAL</div>', unsafe_allow_html=True)
            
            # Calcular métricas
            t_q = df_estudos['total'].sum()
            a_q = df_estudos['acertos'].sum()
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df_estudos['tempo'].sum())
            
            # Formatar tempo como na imagem (3h45min)
            tempo_formatado = formatar_minutos(minutos_totais)
            
            # Dias para a prova
            dias_restantes = None
            if data_prova_direta:
                try:
                    dt_prova = pd.to_datetime(data_prova_direta).date()
                    dias_restantes = (dt_prova - get_br_date()).days
                except Exception:
                    dias_restantes = None
            
            # 4 cartões de métricas com ANÉIS CIRCULARES MODERNOS
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            
            # Calcular percentuais para os anéis
            horas_totais = minutos_totais / 60
            meta_horas_mes = 80  # Meta de horas por mês
            pct_tempo = min((horas_totais / meta_horas_mes) * 100, 100)
            pct_precisao = min(precisao, 100)
            meta_questoes_mes = 1000
            pct_questoes = min((t_q / meta_questoes_mes) * 100, 100)
            
            with c1:
                render_circular_progress(
                    percentage=pct_tempo,
                    label="TEMPO TOTAL",
                    value=tempo_formatado,
                    color_start=COLORS["primary"],
                    color_end=COLORS["secondary"],
                    icon="⏱️"
                )
            with c2:
                render_circular_progress(
                    percentage=pct_precisao,
                    label="PRECISÃO",
                    value=f"{precisao:.0f}%",
                    color_start=COLORS["success"] if precisao >= 70 else COLORS["warning"],
                    color_end=COLORS["secondary"],
                    icon="🎯"
                )
            with c3:
                render_circular_progress(
                    percentage=pct_questoes,
                    label="QUESTÕES",
                    value=f"{int(t_q)}",
                    color_start=COLORS["accent"],
                    color_end=COLORS["primary"],
                    icon="📝"
                )
            with c4:
                if dias_restantes is not None:
                    # Calcular percentual baseado em 90 dias
                    pct_dias = max(0, min(100, (1 - dias_restantes/90) * 100)) if dias_restantes > 0 else 100
                    cor = COLORS["danger"] if dias_restantes <= 30 else COLORS["warning"] if dias_restantes <= 60 else COLORS["success"]
                    render_circular_progress(
                        percentage=pct_dias,
                        label="DIAS PARA PROVA",
                        value=f"{dias_restantes}",
                        color_start=cor,
                        color_end=COLORS["secondary"],
                        icon="📅"
                    )
                else:
                    render_metric_card_modern("DIAS PARA PROVA", "—", icon="📅")
            
            st.divider()

            # --- SEÇÃO DE CONSTÂNCIA MELHORADA (SEM A SEÇÃO DE DIAS DO MÊS) ---
            st.markdown('<div class="constancia-section">', unsafe_allow_html=True)
            
            streak = calcular_streak(df_estudos)
            recorde = calcular_recorde_streak(df_estudos)
            inicio_streak, fim_streak = calcular_datas_streak(df_estudos)
            
            st.markdown('<div class="constancia-header">', unsafe_allow_html=True)
            st.markdown('<div class="constancia-title">📊 CONSTÂNCIA NOS ESTUDOS</div>', unsafe_allow_html=True)
            
            # Indicador de performance 
            performance = "🟢 Excelente" if streak >= 7 else "🟡 Bom" if streak >= 3 else "🔴 Precisa melhorar"
            st.markdown(f'<div style="color: #06B6D4; font-size: 0.9rem; font-weight: 600;">{performance}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Stats de constância em 3 colunas
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                st.markdown(f'''
                    <div style="text-align: center; padding: 24px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(139, 92, 246, 0.05)); border-radius: 16px; border: 1px solid rgba(139, 92, 246, 0.2); transition: all 0.3s ease;">
                        <div style="color: #8B5CF6; font-size: 0.85rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">STREAK ATUAL</div>
                        <div style="font-size: 3rem; font-weight: 800; background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 10px 0;">{streak}</div>
                        <div style="color: #94A3B8; font-size: 0.8rem;">dias consecutivos</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col_s2:
                st.markdown(f'''
                    <div style="text-align: center; padding: 24px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)); border-radius: 16px; border: 1px solid rgba(16, 185, 129, 0.2); transition: all 0.3s ease;">
                        <div style="color: #10B981; font-size: 0.85rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">SEU RECORDE</div>
                        <div style="font-size: 3rem; font-weight: 800; color: #10B981; margin: 10px 0;">{recorde}</div>
                        <div style="color: #94A3B8; font-size: 0.8rem;">dias seguidos</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            with col_s3:
                # Calcular dias estudados no mês
                hoje = get_br_date()
                dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
                dias_estudados_mes = len(set(pd.to_datetime(df_estudos['data_estudo']).dt.date.unique()))
                percentual_mes = (dias_estudados_mes / dias_no_mes) * 100
                
                st.markdown(f'''
                    <div style="text-align: center; padding: 24px; background: linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(6, 182, 212, 0.05)); border-radius: 16px; border: 1px solid rgba(6, 182, 212, 0.2); transition: all 0.3s ease;">
                        <div style="color: #06B6D4; font-size: 0.85rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">MÊS ATUAL</div>
                        <div style="font-size: 2.5rem; font-weight: 800; color: #06B6D4; margin: 10px 0;">{dias_estudados_mes}/{dias_no_mes}</div>
                        <div style="color: #94A3B8; font-size: 0.8rem;">dias estudados ({percentual_mes:.0f}%)</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            # Período do streak atual
            if inicio_streak and fim_streak:
                data_formatada = f"{inicio_streak.strftime('%d/%m')} a {fim_streak.strftime('%d/%m')}"
                st.markdown(f'<div style="text-align: center; margin-top: 15px; color: #94A3B8; font-size: 0.9rem; background: rgba(139, 92, 246, 0.1); padding: 12px; border-radius: 10px;">Período do streak atual: <span style="color: #8B5CF6; font-weight: 600;">{data_formatada}</span></div>', unsafe_allow_html=True)
            
            # --- NOVO: HEATMAP DE ATIVIDADE (ESTILO GITHUB) ---
            st.divider()
            st.markdown('<div style="text-align: center; color: #94A3B8; font-size: 0.85rem; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px;">🔥 MAPA DE CALOR (ÚLTIMAS 12 SEMANAS)</div>', unsafe_allow_html=True)
            
            if not df_estudos.empty:
                try:
                    # Preparar dados: Soma de tempo por dia
                    df_heat = df_estudos.copy()
                    df_heat['data'] = pd.to_datetime(df_heat['data_estudo']).dt.date
                    df_day = df_heat.groupby('data')['tempo'].sum().reset_index()
                    
                    # Criar range das últimas 12 semanas (84 dias)
                    fim = get_br_date()
                    inicio = fim - timedelta(days=83) # 12 semanas
                    all_days = pd.date_range(start=inicio, end=fim)
                    
                    # Merge para garantir todos os dias
                    df_all = pd.DataFrame({'data': all_days.date})
                    df_final = pd.merge(df_all, df_day, on='data', how='left').fillna(0)
                    
                    # Preparar matriz para o heatmap (7 linhas para dias da semana)
                    # 0=Monday, ..., 6=Sunday
                    df_final['weekday'] = pd.to_datetime(df_final['data']).dt.weekday
                    df_final['week'] = df_final['data'].apply(lambda x: (x - inicio).days // 7)
                    
                    # Matriz de dados
                    matrix = [[0 for _ in range(12)] for _ in range(7)]
                    for _, r in df_final.iterrows():
                        if r['week'] < 12:
                            matrix[int(r['weekday'])][int(r['week'])] = r['tempo'] / 60 # Horas
                    
                    weekdays_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                    
                    fig_heat = go.Figure(data=go.Heatmap(
                        z=matrix,
                        x=[f"Sem {i+1}" for i in range(12)],
                        y=weekdays_labels,
                        colorscale=[[0, 'rgba(139, 92, 246, 0.05)'], [0.1, '#1E1B4B'], [0.5, '#8B5CF6'], [1, '#00FFFF']],
                        showscale=False,
                        xgap=3, ygap=3,
                        hoverinfo='z',
                        hovertemplate='Horas estudadas: %{z:.1f}h<extra></extra>'
                    ))
                    
                    fig_heat.update_layout(
                        height=220,
                        margin=dict(t=0, b=10, l=0, r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        yaxis=dict(autorange='reversed', fixedrange=True),
                        xaxis=dict(fixedrange=True, side='top'),
                        font=dict(color="#94A3B8", size=10)
                    )
                    st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})
                except Exception as e:
                    st.error(f"Erro ao gerar heatmap: {e}")
            else:
                st.info("Inicie seus estudos para gerar seu mapa de calor!")

            st.markdown('</div>', unsafe_allow_html=True)  # Fecha constancia-section

            # --- SEÇÃO 3: PAINEL DE DISCIPLINAS ---
            st.markdown('<h3 style="margin-top:2rem; color:#fff;">📊 PAINEL DE DESEMPENHO</h3>', unsafe_allow_html=True)
            
            if not df_estudos.empty:
                # Calcular totais por disciplina
                df_disciplinas = df_estudos.groupby('materia').agg({
                    'tempo': 'sum',
                    'acertos': 'sum',
                    'total': 'sum'
                }).reset_index()
                
                # Recalcular taxa global por disciplina (média ponderada)
                df_disciplinas['taxa'] = (df_disciplinas['acertos'] / df_disciplinas['total'] * 100).fillna(0)
                
                df_disciplinas['erros'] = df_disciplinas['total'] - df_disciplinas['acertos']
                df_disciplinas['tempo_formatado'] = df_disciplinas['tempo'].apply(formatar_horas_minutos)
                df_disciplinas['taxa_formatada'] = df_disciplinas['taxa'].round(0).astype(int)
                df_disciplinas = df_disciplinas.sort_values('tempo', ascending=False)
                
                # Criar tabela HTML CORRIGIDA - SIMPLIFICADA
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                # Criar DataFrame para display
                display_df = pd.DataFrame({
                    'DISCIPLINAS': df_disciplinas['materia'],
                    'TEMPO': df_disciplinas['tempo_formatado'],
                    '✓': df_disciplinas['acertos'].astype(int),
                    '✗': df_disciplinas['erros'].astype(int),
                    '🎉': df_disciplinas['total'].astype(int),
                    '%': df_disciplinas['taxa_formatada']
                })
                
                # Exibir tabela usando st.dataframe com formatação condicional
                def color_taxa(val):
                    if val >= 80:
                        return 'color: #00FF00; font-weight: 700;'
                    elif val >= 70:
                        return 'color: #FFD700; font-weight: 700;'
                    else:
                        return 'color: #FF4B4B; font-weight: 700;'
                
                styled_df = display_df.style.map(color_taxa, subset=['%'])
                
                # Mostrar tabela
                st.dataframe(
                    styled_df,
                    column_config={
                        "DISCIPLINAS": st.column_config.Column(width="large"),
                        "TEMPO": st.column_config.Column(width="medium"),
                        "✓": st.column_config.Column(width="small"),
                        "✗": st.column_config.Column(width="small"),
                        "🎉": st.column_config.Column(width="small"),
                        "%": st.column_config.Column(width="small")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # --- SEÇÃO 4: METAS DE ESTUDO SEMANAL ---
            st.markdown('<h3 style="margin-top:2rem; color:#fff;">🎯 METAS DE ESTUDO SEMANAL</h3>', unsafe_allow_html=True)
            
            # Estado para controlar a edição das metas
            if 'editando_metas' not in st.session_state:
                st.session_state.editando_metas = False
            
            horas_semana, questoes_semana = calcular_estudos_semana(df_estudos)
            meta_horas = st.session_state.meta_horas_semana
            meta_questoes = st.session_state.meta_questoes_semana
            
            # Botão para editar metas
            col_btn1, col_btn2, col_btn3 = st.columns([4, 1, 1])
            with col_btn2:
                if st.button("⚙️ Configurar Metas", key="btn_config_metas", use_container_width=True):
                    st.session_state.editando_metas = not st.session_state.editando_metas
                    st.rerun()
            
            # Modal de edição de metas
            if st.session_state.editando_metas:
                with st.container():
                    st.markdown('<div class="meta-modal">', unsafe_allow_html=True)
                    st.markdown("##### 📝 Configurar Metas Semanais")
                    
                    with st.form("form_metas_semanais"):
                        col_meta1, col_meta2 = st.columns(2)
                        
                        with col_meta1:
                            nova_meta_horas = st.number_input(
                                "Horas de estudo semanais",
                                min_value=1,
                                max_value=100,
                                value=meta_horas,
                                step=1,
                                help="Meta de horas de estudo por semana"
                            )
                        
                        with col_meta2:
                            nova_meta_questoes = st.number_input(
                                "Questões semanais",
                                min_value=1,
                                max_value=1000,
                                value=meta_questoes,
                                step=10,
                                help="Meta de questões resolvidas por semana"
                            )
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
                        if col_btn1.form_submit_button("💾 Salvar Metas", use_container_width=True, type="primary"):
                            st.session_state.meta_horas_semana = nova_meta_horas
                            st.session_state.meta_questoes_semana = nova_meta_questoes
                            st.session_state.editando_metas = False
                            st.success("✅ Metas atualizadas com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        
                        if col_btn2.form_submit_button("❌ Cancelar", use_container_width=True, type="secondary"):
                            st.session_state.editando_metas = False
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Cartões de metas
            col_meta1, col_meta2 = st.columns(2)
            
            with col_meta1:
                progresso_horas = min((horas_semana / meta_horas) * 100, 100) if meta_horas > 0 else 0
                st.markdown(f'''
                <div class="meta-card">
                    <div class="meta-title">Horas de Estudo</div>
                    <div class="meta-value">{horas_semana:.1f}h/{meta_horas}h</div>
                    <div class="meta-progress">
                        <div class="modern-progress-container">
                            <div class="modern-progress-fill" style="width: {progresso_horas}%;"></div>
                        </div>
                    </div>
                    <div class="meta-subtitle">{progresso_horas:.0f}% da meta alcançada</div>
                </div>
                ''', unsafe_allow_html=True)
            
            with col_meta2:
                progresso_questoes = min((questoes_semana / meta_questoes) * 100, 100) if meta_questoes > 0 else 0
                st.markdown(f'''
                <div class="meta-card">
                    <div class="meta-title">Questões Resolvidas</div>
                    <div class="meta-value">{int(questoes_semana)}/{meta_questoes}</div>
                    <div class="meta-progress">
                        <div class="modern-progress-container">
                            <div class="modern-progress-fill" style="width: {progresso_questoes}%;"></div>
                        </div>
                    </div>
                    <div class="meta-subtitle">{progresso_questoes:.0f}% da meta alcançada</div>
                </div>
                ''', unsafe_allow_html=True)

    # --- ABA: GUIA SEMANAL (PLANNER INTELIGENTE) ---
    elif menu == "Guia Semanal":
        st.markdown('<h2 class="main-title">📅 Guia da Semana</h2>', unsafe_allow_html=True)
        st.markdown("<p style='color: #94A3B8; font-size: 1.1rem; margin-top: -1rem;'>Suas recomendações baseadas no radar de performance.</p>", unsafe_allow_html=True)
        
        if df_estudos.empty:
            st.info("Registre alguns estudos para que eu possa planejar sua semana estrategicamente.")
        else:
            # Lógica de Recomendação (Priority Engine)
            df_matriz = df_estudos.groupby('materia').agg({
                'acertos': 'sum',
                'total': 'sum',
                'relevancia': 'mean'
            }).reset_index()
            df_matriz['taxa'] = (df_matriz['acertos'] / df_matriz['total'] * 100).fillna(0)
            
            # Quadrante: Foco Crítico (Taxa < 75 e Relevância > 5)
            criticos = df_matriz[(df_matriz['taxa'] < 75) & (df_matriz['relevancia'] >= 5)].sort_values(['relevancia', 'taxa'], ascending=[False, True])
            
            col_rec1, col_rec2 = st.columns([2, 1])
            
            with col_rec1:
                st.markdown("#### 🎯 Alvos Prioritários")
                if criticos.empty:
                    st.success("✨ Sem gargalos críticos no momento! Recomendo avançar em novos tópicos do edital.")
                else:
                    for _, row in criticos.head(3).iterrows():
                        # Buscar o pior assunto desta materia
                        df_ass = df_estudos[df_estudos['materia'] == row['materia']].groupby('assunto').agg({'taxa': 'mean'}).reset_index()
                        pior_ass = df_ass.sort_values('taxa').iloc[0]['assunto']
                        
                        st.markdown(f"""
                        <div class="modern-card" style="border-left: 5px solid #EF4444;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="font-weight: 800; color: #E2E8F0; font-size: 1.1rem;">{row['materia'].upper()}</span>
                                <span style="background: rgba(239, 68, 68, 0.1); color: #EF4444; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">URGENTE</span>
                            </div>
                            <div style="margin-top: 10px; color: #94A3B8; font-size: 0.9rem;">
                                Sua precisão média é de <b>{row['taxa']:.0f}%</b>. O maior gargalo identificado é:
                            </div>
                            <div style="margin-top: 8px; color: #FFFFFF; font-weight: 600; font-size: 1rem;">
                                ⚠️ {pior_ass}
                            </div>
                            <div style="margin-top: 15px; font-size: 0.85rem; color: #8B5CF6;">
                                💡 Sugestão: Dedicar 2h de teoria + 30 questões comentadas nesta semana.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            
            with col_rec2:
                # 1. LÓGICA DE DADOS (Cálculos de Metas)
                hoje = get_br_date()
                in_sem = hoje - timedelta(days=hoje.weekday())
                
                df_s = df_raw[pd.to_datetime(df_raw['data_estudo']).dt.date >= in_sem] if not df_raw.empty else pd.DataFrame()
                df_e = df_estudos[pd.to_datetime(df_estudos['data_estudo']).dt.date >= in_sem] if not df_estudos.empty else pd.DataFrame()
                df_sim_s = df_simulados[pd.to_datetime(df_simulados['data_estudo']).dt.date >= in_sem] if not df_simulados.empty else pd.DataFrame()
                
                # Definir itens do checklist
                m_labels = []
                st_auto = {}
                
                if not criticos.empty:
                    pm = criticos.iloc[0]['materia']
                    lbl_c = f"Revisar {pm}"
                    m_labels.append(lbl_c)
                    st_auto[lbl_c] = not df_e[df_e['materia'] == pm].empty if not df_e.empty else False
                
                m_labels.extend(["Realizar 1 Simulado de Elite", "Manter meta de questões diária", "Zerar 2 novos tópicos do edital"])
                st_auto["Realizar 1 Simulado de Elite"] = not df_sim_s.empty
                st_auto["Manter meta de questões diária"] = df_s['total'].sum() >= st.session_state.get('meta_questoes_semana', 350) if not df_s.empty else False
                st_auto["Zerar 2 novos tópicos do edital"] = len(df_e['assunto'].unique()) >= 2 if not df_e.empty else False

                # Contagem de Progresso (Calculado ANTES de desenhar a UI)
                v_done = 0
                for i, m in enumerate(m_labels):
                    if st_auto.get(m, False) or st.session_state.checklist_status.get(f"check_{i}_{m[:10]}", False):
                        v_done += 1
                v_total = len(m_labels)

                # 2. RENDERIZAÇÃO DA UI
                st.markdown('<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">', unsafe_allow_html=True)
                st.markdown("#### ⚡ Checklist", unsafe_allow_html=True)
                
                m_status = st.session_state.missao_semanal_status
                m_color = "#94A3B8" if m_status == "PLANEJAMENTO" else "#8B5CF6"
                if v_done == v_total and v_total > 0:
                    m_status = "CONCLUÍDA"
                    m_color = "#10B981"
                st.markdown(f'<span class="badge" style="background: {m_color}22; color: {m_color}; border: 1px solid {m_color}44;">{m_status}</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                # Renderizar checkboxes
                for i, m in enumerate(m_labels):
                    is_a = st_auto.get(m, False)
                    is_m = st.session_state.checklist_status.get(f"check_{i}_{m[:10]}", False)
                    st.checkbox(f"{'✅ ' if is_a else ''}{m}", value=(is_a or is_m), key=f"guia_check_{i}")
                
                # Barra de Progresso Real
                p_pct = (v_done / v_total) if v_total > 0 else 0
                st.markdown(f"""
                    <div style='margin-top: 15px;'>
                        <div style='display: flex; justify-content: space-between; font-size: 0.75rem; color: #94A3B8; margin-bottom: 4px;'>
                            <span>Evolução</span><span>{v_done}/{v_total}</span>
                        </div>
                        <div class="modern-progress-container"><div class="modern-progress-fill" style="width: {p_pct*100}%;"></div></div>
                    </div>
                """, unsafe_allow_html=True)

                st.divider()
                if st.button("💾 Salvar Planejamento", use_container_width=True):
                    for i, m in enumerate(m_labels):
                        st.session_state.checklist_status[f"check_{i}_{m[:10]}"] = st.session_state[f"guia_check_{i}"]
                    st.session_state.missao_semanal_status = "EM EXECUÇÃO"
                    st.toast("Plano Ativado!", icon="🚀")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Gráfico de Alocação de Tempo Sugerida
            st.markdown("#### 📊 Alocação de Tempo Recomendada")
            if not criticos.empty:
                df_pie = criticos.head(5).copy()
                df_pie['sugestao'] = [40, 25, 15, 10, 10][:len(df_pie)] # Exemplo de pesos
                
                fig_planner = px.pie(
                    df_pie, values='sugestao', names='materia', 
                    hole=0.5, template="plotly_dark",
                    color_discrete_sequence=px.colors.sequential.Purp_r
                )
                fig_planner.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
                st.plotly_chart(fig_planner, use_container_width=True)
            else:
                st.info("Distribua seu tempo igualmente entre as matérias restantes do edital.")

    # --- ABA: REVISÕES (LISTA REDESENHADA) ---
    elif menu == "Revisões":
        st.markdown('<h2 class="main-title">🔄 Radar de Revisões</h2>', unsafe_allow_html=True)
        
        # Filtros
        c1, c2 = st.columns([2, 1])
        with c1:
            filtro_rev = st.segmented_control("Visualizar:", ["Pendentes/Hoje", "Todas"], default="Pendentes/Hoje", key="filtro_rev_list")
        with c2:
            filtro_dif = st.segmented_control("Dificuldade:", ["Todas", "🔴 Difícil", "🟡 Médio", "🟢 Fácil"], default="Todas", key="filtro_dif_list")
    
        # Calcular pendentes
        pend = calcular_revisoes_pendentes(df_estudos, filtro_rev, filtro_dif)
        
        if not pend: 
            st.success("✨ Tudo em dia! Nenhuma revisão pendente para os filtros selecionados.")
        else:
            # Ordenar por prioridade (Atraso > Data)
            pend = sorted(pend, key=lambda x: (x['atraso'] <= 0, x['data_prevista']))
            
            st.write(f"**{len(pend)} revisões encontradas**")
            st.markdown("---")
            
            # Lista de Cards Alinhados
            for p in pend:
                with st.container():
                    # Definir cor da borda baseada no status
                    border_color = "#EF4444" if p['atraso'] > 0 else "#10B981" if p['atraso'] == 0 else "#94A3B8"
                    status_badge = f"⚠️ {p['atraso']}d Atraso" if p['atraso'] > 0 else "🎯 É Hoje" if p['atraso'] == 0 else f"📅 {p['data_prevista'].strftime('%d/%m')}"
                    
                    # Card Container
                    st.markdown(f"""
                    <div style="
                        border-left: 4px solid {border_color};
                        background: rgba(30, 41, 59, 0.5);
                        padding: 15px 20px;
                        border-radius: 8px;
                        margin-bottom: 12px;
                        display: flex;
                        flex-direction: column;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <div>
                                <span style="background: {border_color}20; color: {border_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">{status_badge}</span>
                                <span style="color: #94A3B8; font-size: 0.75rem; margin-left: 8px;">{p['materia']}</span>
                            </div>
                             <div style="color: #64748B; font-size: 0.8rem;">
                                 ⭐ R{int(p.get('relevancia', 5))} | Rev de {p['tipo']}
                             </div>
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: white;">{p['assunto']}</div>
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">📝 {p['coment'] if p['coment'] else 'Sem anotações'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Área de Ação (Inputs, Tempo e Botão)
                    c_input, c_btn = st.columns([3, 1])
                    
                    with c_input:
                        ci1, ci2, ci3 = st.columns(3)
                        acertos = ci1.number_input("✅ Acertos", min_value=0, key=f"ac_{p['id']}_{p['col']}")
                        total = ci2.number_input("📝 Total", min_value=0, key=f"to_{p['id']}_{p['col']}")
                        tempo_rev = ci3.number_input("⏱️ Tempo (min)", min_value=0, step=5, key=f"tm_{p['id']}_{p['col']}")
                    
                    with c_btn:
                        if st.button("✅ Concluir", key=f"btn_{p['id']}_{p['col']}", use_container_width=True, type="primary"):
                            try:
                                res_db = supabase.table("registros_estudos").select("acertos, total, tempo").eq("id", p['id']).execute()
                                if res_db.data:
                                    n_ac = res_db.data[0]['acertos'] + acertos
                                    n_to = res_db.data[0]['total'] + total
                                    # Soma o tempo antigo com o novo tempo de revisão
                                    n_tempo = (res_db.data[0].get('tempo') or 0) + tempo_rev
                                    
                                    supabase.table("registros_estudos").update({
                                        p['col']: True, 
                                        "comentarios": f"{p['coment']} | Rev: {acertos}/{total} ({tempo_rev}min)", 
                                        "acertos": n_ac, 
                                        "total": n_to, 
                                        "tempo": n_tempo,
                                        "taxa": (n_ac/n_to*100 if n_to > 0 else 0)
                                    }).eq("id", p['id']).execute()
                                    
                                    st.toast(f"Revisão de {p['assunto']} concluída (+{tempo_rev}min)!")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                    
                    st.divider()

    # --- ABA: REGISTRAR ---
    elif menu == "Registrar":
        st.markdown('<h2 class="main-title">📝 Novo Registro de Estudo</h2>', unsafe_allow_html=True)
        mats = list(dados.get('materias', {}).keys())
        
        if not mats:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'Configurar' para adicionar disciplinas.")
        else:
            with st.container():
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                c1, c2 = st.columns([2, 1])
                dt_reg = c1.date_input("Data do Estudo", value=get_br_date(), format="DD/MM/YYYY")
                tm_reg = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30min")
                
                mat_reg = st.selectbox("Disciplina", mats)
                assuntos_disponiveis = dados.get('materias', {}).get(mat_reg, ["Geral"])
                ass_reg = st.selectbox("Assunto", assuntos_disponiveis, key=f"assunto_select_{mat_reg}")
                
                st.divider()
                
                with st.form("form_registro_final", clear_on_submit=True):
                    ca_reg, ct_reg = st.columns(2)
                    ac_reg = ca_reg.number_input("Questões Acertadas", 0)
                    to_reg = ct_reg.number_input("Total de Questões", 0)
                    
                    # NOVO: Classificação de Dificuldade
                    st.markdown("##### 🎯 Como foi esse assunto?")
                    dif_reg = st.segmented_control(
                        "Classificação:",
                        ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                        default="🟡 Médio"
                    )
                    
                    # NOVO: Relevância (Incidência)
                    rel_reg = st.selectbox(
                        "Relevância (Incidência em Prova):",
                        options=list(range(1, 11)),
                        index=4,  # Valor 5 (índice 4)
                        help="De 1 (baixa incidência) a 10 (matéria muito cobrada)"
                    )
                    
                    # Mostrar recomendação baseada na dificuldade
                    tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_reg)
                    st.info(f"💡 **{dif_reg}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                    
                    # NOVO: Checkbox para controlar se gera revisões
                    gerar_rev_reg = st.checkbox("🔄 Gerar ciclo de revisões para este registro?", value=True, help="Se desmarcado, este registro será salvo apenas para estatísticas e não aparecerá no radar de revisões.")
                    
                    st.divider()
                    
                    com_reg = st.text_area("Anotações / Comentários", placeholder="O que você aprendeu ou sentiu dificuldade?")
                    
                    btn_salvar = st.form_submit_button("💾 SALVAR REGISTRO", use_container_width=True, type="primary")
                    
                    if btn_salvar:
                        try:
                            t_b = formatar_tempo_para_bigint(tm_reg)
                            taxa = (ac_reg/to_reg*100 if to_reg > 0 else 0)
                            
                            payload = {
                                "concurso": missao, 
                                "materia": mat_reg, 
                                "assunto": ass_reg, 
                                "data_estudo": dt_reg.strftime('%Y-%m-%d'), 
                                "acertos": ac_reg, 
                                "total": to_reg, 
                                "taxa": taxa,
                                "dificuldade": dif_reg, 
                                "relevancia": rel_reg,  # Novo campo
                                "comentarios": com_reg, 
                                "tempo": t_b, 
                                "rev_24h": not gerar_rev_reg, 
                                "rev_07d": not gerar_rev_reg, 
                                "rev_15d": not gerar_rev_reg, 
                                "rev_30d": not gerar_rev_reg
                            }
                            supabase.table("registros_estudos").insert(payload).execute()
                            st.success("✅ Registro salvo com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: DASHBOARD ---
    elif menu == "Dashboard":
        st.markdown('<h2 class="main-title">📊 Dashboard de Performance</h2>', unsafe_allow_html=True)
        
        # --- NOVO: EDITAL VERTICALIZADO (COBERTURA) ---
        if dados.get('materias'):
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### 📜 Progresso do Edital (Syllabus)")
            st.markdown("<p style='font-size: 0.8rem; color: #94A3B8;'>Percentual de assuntos únicos estudados por matéria.</p>", unsafe_allow_html=True)
            
            # Calcular cobertura para cada materia cadastrada
            cols_edital = st.columns(3)
            col_idx = 0
            
            for materia, assuntos_previstos in dados.get('materias', {}).items():
                # Assuntos estudados nessa materia (filtrando do df_estudos)
                if not df_estudos.empty and 'materia' in df_estudos.columns and 'assunto' in df_estudos.columns:
                    assuntos_estudados = df_estudos[df_estudos['materia'] == materia]['assunto'].unique()
                    count_estudados = len(assuntos_estudados)
                else:
                    count_estudados = 0
                
                count_total = len(assuntos_previstos)
                porcentagem = (count_estudados / count_total * 100) if count_total > 0 else 0
                
                # Cor da barra
                bar_color = "#EF4444" if porcentagem < 30 else "#F59E0B" if porcentagem < 70 else "#10B981"
                
                with cols_edital[col_idx % 3]:
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; color: #E2E8F0; margin-bottom: 5px;">
                            <span>{materia}</span>
                            <span style="color: {bar_color};">{int(porcentagem)}%</span>
                        </div>
                        <div class="modern-progress-container">
                            <div class="modern-progress-fill" style="width: {porcentagem}%; background: {bar_color};"></div>
                        </div>
                        <div style="font-size: 0.7rem; color: #64748B; text-align: right; margin-top: 2px;">{count_estudados}/{count_total} tópicos</div>
                    </div>
                    """, unsafe_allow_html=True)
                col_idx += 1
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()

        # --- NOVO: MAPA DE CALOR DE CONSTÂNCIA ---
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        st.markdown("##### 🔥 Mapa de Calor: Sua Constância (6 meses)")
        render_consistency_heatmap(df_estudos)
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        # Métricas Gerais
        if df_estudos.empty:
            t_q, precisao, horas, ritmo = 0, 0, 0, 0
        else:
            t_q = df_estudos['total'].sum()
            a_q = df_estudos['acertos'].sum()
            precisao = (a_q/t_q*100 if t_q > 0 else 0)
            tempo_min = df_estudos['tempo'].sum()
            horas = tempo_min/60
            ritmo = (tempo_min / t_q) if t_q > 0 else 0
        
        # 1. MÉTRICAS PRINCIPAIS
        m1, m2, m3, m4 = st.columns(4)
        with m1: render_metric_card("Questões", int(t_q), "📝")
        with m2: render_metric_card("Precisão", f"{precisao:.1f}%", "🎯")
        with m3: render_metric_card("Horas", f"{horas:.1f}h", "⏱️")
        with m4: render_metric_card("Ritmo", f"{ritmo:.1f} min/q", "⚡")
        
        st.divider()
        
        # --- NOVO: DESEMPENHO POR RELEVÂNCIA ---
        if not df_estudos.empty and 'relevancia' in df_estudos.columns:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### ⭐ Desempenho por Nível de Relevância")
            st.markdown("<p style='font-size: 0.8rem; color: #94A3B8;'>Precisão média agrupada pela importância da matéria (1-10).</p>", unsafe_allow_html=True)
            
            # Agrupar por relevância
            df_rel_dash = df_estudos.groupby('relevancia').agg({
                'acertos': 'sum',
                'total': 'sum'
            }).reset_index()
            
            # Recalcular taxa por nível de relevância (média ponderada)
            df_rel_dash['taxa'] = (df_rel_dash['acertos'] / df_rel_dash['total'] * 100).fillna(0)
            df_rel_dash['relevancia'] = df_rel_dash['relevancia'].astype(int)
            df_rel_dash = df_rel_dash.sort_values('relevancia', ascending=False)
            
            # Usar colunas dinâmicas para os níveis de relevância
            n_cols = len(df_rel_dash)
            if n_cols > 0:
                c_rel = st.columns(n_cols)
                for idx, row in enumerate(df_rel_dash.iterrows()):
                    r_val = row[1]['relevancia']
                    r_taxa = row[1]['taxa']
                    r_total = row[1]['total']
                    
                    with c_rel[idx]:
                        color = "#10B981" if r_taxa >= 75 else "#F59E0B" if r_taxa >= 50 else "#EF4444"
                        st.markdown(f"""
                            <div style="text-align: center; border: 1px solid rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.02);">
                                <div style="font-size: 0.7rem; color: #94A3B8;">NÍVEL {r_val}</div>
                                <div style="font-size: 1.2rem; font-weight: 800; color: {color};">{r_taxa:.1f}%</div>
                                <div style="font-size: 0.65rem; color: #64748B;">{int(r_total)} questões</div>
                            </div>
                        """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()

        # 2. PONTOS FRACOS & EVOLUÇÃO
        if not df_estudos.empty:
            c_main1, c_main2 = st.columns([1, 1])
            
            with c_main1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### 📉 Pareto de Erros: Onde você mais perde pontos")
                st.markdown("<p style='font-size: 0.8rem; color: #94A3B8;'>Top 10 assuntos com maior volume absoluto de erros.</p>", unsafe_allow_html=True)
                
                # Calcular erros brutos por assunto
                df_errors = df_estudos.groupby(['materia', 'assunto']).agg({
                    'total': 'sum', 
                    'acertos': 'sum'
                }).reset_index()
                df_errors['erros'] = df_errors['total'] - df_errors['acertos']
                df_errors = df_errors.sort_values('erros', ascending=False).head(10)
                # Filtrar apenas assuntos com erros
                df_errors = df_errors[df_errors['erros'] > 0]
                
                if not df_errors.empty:
                    # Gráfico de barras horizontais (Pareto)
                    df_errors['label'] = df_errors['assunto'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x)
                    fig_pareto = px.bar(
                        df_errors, x='erros', y='label', orientation='h',
                        template="plotly_dark",
                        color='erros',
                        color_continuous_scale=["#F43F5E", "#E11D48"], # Tons de vermelho
                        text='erros'
                    )
                    fig_pareto.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(t=0, b=0, l=0, r=0),
                        xaxis_visible=False,
                        yaxis_title=None,
                        coloraxis_showscale=False,
                        height=280,
                        yaxis={'categoryorder':'total ascending'}
                    )
                    st.plotly_chart(fig_pareto, use_container_width=True)
                else:
                    st.success("🎉 Nenhum erro registrado! Continue com a precisão em 100%.")
                st.markdown('</div>', unsafe_allow_html=True)

            with c_main2:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                st.markdown("##### 📅 Produtividade Semanal")
                st.markdown("<p style='font-size: 0.8rem; color: #94A3B8;'>Horas de estudo por dia da semana.</p>", unsafe_allow_html=True)
                
                # Preparar dados por dia da semana
                df_estudos['weekday'] = pd.to_datetime(df_estudos['data_estudo']).dt.day_name()
                # Traduzir dias (opcional, ou usar ordem fixa)
                dias_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                dias_trad = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua", "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
                
                df_week = df_estudos.groupby('weekday')['tempo'].sum().reindex(dias_ordem).fillna(0).reset_index()
                df_week['horas'] = df_week['tempo'] / 60
                df_week['dia_pt'] = df_week['weekday'].map(dias_trad)
                
                fig_bar = px.bar(df_week, x='dia_pt', y='horas', 
                                template="plotly_dark",
                                color='horas',
                                color_continuous_scale=["#8B5CF6", "#06B6D4"])
                
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=10, b=0, l=0, r=0),
                    xaxis_title=None,
                    yaxis_title="Horas",
                    coloraxis_showscale=False,
                    height=250
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        # 3. GRÁFICO DE EVOLUÇÃO (Precisão com Média Móvel)
        if not df_estudos.empty:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### 📈 Evolução de Precisão & Tendência")
            st.markdown("<p style='font-size: 0.8rem; color: #94A3B8;'>Precisão diária (%) vs Média Móvel (tendência dos últimos 7 dias).</p>", unsafe_allow_html=True)
            
            # Preparar dados de evolução
            # Agrupar por data calculando somas para taxa ponderada
            df_ev = df_estudos.sort_values('data_estudo').groupby('data_estudo').agg({
                'acertos': 'sum',
                'total': 'sum'
            }).reset_index()
            
            # Calcular taxa diária
            df_ev['taxa'] = (df_ev['acertos'] / df_ev['total'] * 100).fillna(0)
            
            # Calcular Média Móvel (janela de 7 pontos para capturar ciclo semanal)
            df_ev['Média Móvel'] = df_ev['taxa'].rolling(window=min(7, len(df_ev)), min_periods=1).mean()
            
            # Criar gráfico Plotly unificado
            fig_evo = go.Figure()
            
            # Linha de Precisão Diária
            fig_evo.add_trace(go.Scatter(
                x=df_ev['data_estudo'], y=df_ev['taxa'],
                name='Precisão Diária',
                line=dict(color='#8B5CF6', width=2),
                mode='lines+markers',
                marker=dict(size=6)
            ))
            
            # Linha de Tendência (Média Móvel)
            fig_evo.add_trace(go.Scatter(
                x=df_ev['data_estudo'], y=df_ev['Média Móvel'],
                name='Tendência (Média Móvel)',
                line=dict(color='#06B6D4', width=4, dash='dash'),
                mode='lines'
            ))
            
            fig_evo.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=10, b=0, l=0, r=0),
                xaxis_title=None,
                yaxis_title="Taxa %",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                font=dict(color="#fff"),
                height=400,
                yaxis=dict(range=[0, 105], gridcolor='rgba(255,255,255,0.05)')
            )
            
            st.plotly_chart(fig_evo, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("📚 Registre seus primeiros estudos para ver o gráfico de evolução!")

        st.write("") # Espaçador

    # --- ABA: SIMULADOS (NOVA) ---
    elif menu == "Simulados":
        st.markdown('<h2 class="main-title">🏆 Área de Simulados</h2>', unsafe_allow_html=True)
        
        col_sim1, col_sim2 = st.columns([1, 2])
        
        with col_sim1:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown("##### 📝 Novo Simulado")
            
            with st.form("form_simulado"):
                nome_sim = st.text_input("Nome da Prova", placeholder="Ex: Simulado PF 01")
                banca_sim = st.text_input("Banca", placeholder="Ex: Cebraspe")
                col_sd1, col_sd2 = st.columns(2)
                data_sim = col_sd1.date_input("Data Realização")
                tempo_sim = col_sd2.text_input("Tempo (HHMM)", value="0400", help="Ex: 0400 para 4h00min")
                
                st.markdown("---")
                st.markdown("##### 📊 Desempenho por Disciplina")
                
                # Campos dinâmicos por matéria
                notas_por_materia = {}
                mats_edital = list(dados.get('materias', {}).keys())
                
                if not mats_edital:
                    st.warning("⚠️ Nenhuma matéria cadastrada no edital. Adicione matérias em 'Configurar' primeiro.")
                else:
                    for m_name in mats_edital:
                        c1, c2, c3 = st.columns([2, 1, 1])
                        c1.markdown(f"<div style='padding-top:25px; font-weight:600;'>{m_name}</div>", unsafe_allow_html=True)
                        ac = c2.number_input("Acertos", min_value=0, key=f"sim_ac_{m_name}")
                        to = c3.number_input("Total", min_value=0, key=f"sim_to_{m_name}")
                        notas_por_materia[m_name] = {"ac": ac, "to": to}

                if st.form_submit_button("💾 Salvar Simulado Completo", use_container_width=True, type="primary"):
                    if nome_sim and mats_edital:
                        # Calcular totais
                        total_acertos = sum(v['ac'] for v in notas_por_materia.values())
                        total_questoes = sum(v['to'] for v in notas_por_materia.values())
                        
                        if total_questoes == 0:
                            st.error("O total de questões não pode ser zero.")
                        else:
                            # Gerar string de detalhes
                            detalhes = " | ".join([f"{k}: {v['ac']}/{v['to']}" for k, v in notas_por_materia.items() if v['to'] > 0])
                            
                            t_b_sim = formatar_tempo_para_bigint(tempo_sim)
                            
                            simulado_data = {
                                "data_estudo": data_sim.strftime("%Y-%m-%d"),
                                "materia": "SIMULADO",
                                "assunto": f"{nome_sim} | {banca_sim}",
                                "tempo": t_b_sim,
                                "acertos": total_acertos,
                                "total": total_questoes,
                                "taxa": (total_acertos/total_questoes*100),
                                "concurso": st.session_state.missao_ativa,
                                "rev_24h": True, "rev_07d": True, "rev_15d": True, "rev_30d": True,
                                "dificuldade": "Simulado",
                                "comentarios": f"Banca: {banca_sim} | Detalhes: {detalhes}"
                            }
                            try:
                                supabase.table("registros_estudos").insert(simulado_data).execute()
                                st.success(f"🏆 Simulado registrado! Total: {total_acertos}/{total_questoes}")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                    elif not nome_sim:
                        st.warning("Preencha o nome do simulado.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_sim2:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            if not df_simulados.empty:
                # --- MÉTRICAS ACUMULATIVAS ---
                st.markdown("##### 🏛️ Desempenho Acumulado")
                c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
                tot_ac = df_simulados['acertos'].sum()
                tot_to = df_simulados['total'].sum()
                prec_global = (tot_ac / tot_to * 100) if tot_to > 0 else 0
                tempo_medio = df_simulados['tempo'].mean() if not df_simulados.empty else 0
                
                with c_ac1: render_metric_card("Total Acertos", int(tot_ac), "🎯")
                with c_ac2: render_metric_card("Total Questões", int(tot_to), "📝")
                with c_ac3: render_metric_card("Precisão Global", f"{prec_global:.1f}%", "🏆")
                with c_ac4: render_metric_card("Tempo Médio", formatar_minutos(tempo_medio), "⏱️")
                
                st.divider()
                
                # --- ANÁLISE VERTICAL ACUMULADA ---
                st.markdown("##### 📈 Análise Vertical Acumulada")
                st.markdown("<p style='font-size: 0.8rem; color: #94A3B8; margin-bottom: 15px;'>Desempenho consolidado de todas as disciplinas em todos os simulados.</p>", unsafe_allow_html=True)
                
                # Consolidar dados de todas as matérias de todos os simulados
                consolidado = {}
                for _, row in df_simulados.iterrows():
                    coments = row.get('comentarios', '')
                    if "Detalhes:" in coments:
                        try:
                            det_str = coments.split("Detalhes:")[1].strip()
                            items = [it.strip() for it in det_str.split("|")]
                            for item in items:
                                if ":" in item:
                                    mat, score = item.split(":", 1)
                                    if "/" in score:
                                        ac, to = score.split("/")
                                        m_name = mat.strip()
                                        if m_name not in consolidado:
                                            consolidado[m_name] = {"ac": 0, "to": 0}
                                        consolidado[m_name]["ac"] += int(ac)
                                        consolidado[m_name]["to"] += int(to)
                        except Exception:
                            continue
                
                if consolidado:
                    st.markdown("<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;'>", unsafe_allow_html=True)
                    # Ordenar por maior número de questões/importância
                    for m_name, vals in sorted(consolidado.items(), key=lambda x: x[1]['to'], reverse=True):
                        perc = (vals['ac'] / vals['to'] * 100) if vals['to'] > 0 else 0
                        bar_color = "#10B981" if perc >= 75 else "#F59E0B" if perc >= 50 else "#EF4444"
                        
                        st.markdown(f"""
                        <div style="background: rgba(139, 92, 246, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.1);">
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 8px;">
                                <span style="font-weight: 600;">{m_name}</span>
                                <span style="font-weight: 800; color: {bar_color};">{vals['ac']}/{vals['to']} ({int(perc)}%)</span>
                            </div>
                            <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                                <div style="width: {perc}%; height: 100%; background: {bar_color}; box-shadow: 0 0 10px {bar_color}40;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("Cadastre simulados com detalhamento por matéria para habilitar a análise vertical.")

                st.divider()
                
                # --- HISTÓRICO VERTICAL (CARDS) COM SCROLL ---
                st.markdown("##### 📜 Histórico de Provas")
                
                df_sim_hist = df_simulados.sort_values('data_estudo', ascending=False)
                
                # --- MODAL DE EDIÇÃO DE SIMULADO ---
                if st.session_state.edit_id_simulado is not None:
                    registro_sim_edit = df_simulados[df_simulados['id'] == st.session_state.edit_id_simulado].iloc[0]
                    
                    st.markdown('<div class="modern-card" style="border: 2px solid rgba(0, 255, 255, 0.3); background: rgba(0, 255, 255, 0.05);">', unsafe_allow_html=True)
                    st.markdown("### ✏️ Editar Simulado")
                    
                    with st.form("form_edit_simulado"):
                        nome_sim_ed = st.text_input("Nome da Prova", value=registro_sim_edit['assunto'].split(' | ')[0])
                        banca_sim_ed = st.text_input("Banca", value=registro_sim_edit['assunto'].split(' | ')[1] if ' | ' in registro_sim_edit['assunto'] else "")
                        
                        col_ed_sim1, col_ed_sim2 = st.columns(2)
                        data_sim_ed = col_ed_sim1.date_input("Data Realização", value=pd.to_datetime(registro_sim_edit['data_estudo']).date())
                        tempo_sim_ed = col_ed_sim2.text_input("Tempo (HHMM)", value=f"{int(registro_sim_edit['tempo']//60):02d}{int(registro_sim_edit['tempo']%60):02d}")
                        
                        st.divider()
                        st.markdown("##### 📊 Desempenho por Disciplina")
                        
                        # Extrair notas atuais dos comentários
                        coments = registro_sim_edit.get('comentarios', '')
                        notas_atuais = {}
                        if "Detalhes:" in coments:
                            det_str = coments.split("Detalhes:")[1].strip()
                            for item in det_str.split("|"):
                                if ":" in item:
                                    m, s = item.split(":", 1)
                                    if "/" in s:
                                        notas_atuais[m.strip()] = s.strip().split("/")
                        
                        novas_notas = {}
                        for m_name in mats_edital:
                            c1, c2, c3 = st.columns([2, 1, 1])
                            c1.markdown(f"<div style='padding-top:25px; font-weight:600;'>{m_name}</div>", unsafe_allow_html=True)
                            val_ac = int(notas_atuais.get(m_name, [0, 0])[0])
                            val_to = int(notas_atuais.get(m_name, [0, 0])[1])
                            ac = c2.number_input("Acertos", min_value=0, value=val_ac, key=f"edit_sim_ac_{m_name}")
                            to = c3.number_input("Total", min_value=0, value=val_to, key=f"edit_sim_to_{m_name}")
                            novas_notas[m_name] = {"ac": ac, "to": to}
                        
                        col_edit_btn1, col_edit_btn2 = st.columns(2)
                        if col_edit_btn1.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True, type="primary"):
                            tot_ac = sum(v['ac'] for v in novas_notas.values())
                            tot_to = sum(v['to'] for v in novas_notas.values())
                            
                            if tot_to > 0:
                                det_novos = " | ".join([f"{k}: {v['ac']}/{v['to']}" for k, v in novas_notas.items() if v['to'] > 0])
                                t_b_ed = formatar_tempo_para_bigint(tempo_sim_ed)
                                
                                supabase.table("registros_estudos").update({
                                    "data_estudo": data_sim_ed.strftime("%Y-%m-%d"),
                                    "assunto": f"{nome_sim_ed} | {banca_sim_ed}",
                                    "tempo": t_b_ed,
                                    "acertos": tot_ac,
                                    "total": tot_to,
                                    "taxa": (tot_ac/tot_to*100),
                                    "comentarios": f"Banca: {banca_sim_ed} | Detalhes: {det_novos}"
                                }).eq("id", st.session_state.edit_id_simulado).execute()
                                
                                st.success("✅ Simulado atualizado!")
                                time.sleep(1)
                                st.session_state.edit_id_simulado = None
                                st.rerun()
                        
                        if col_edit_btn2.form_submit_button("❌ CANCELAR", use_container_width=True):
                            st.session_state.edit_id_simulado = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with st.container(height=600): # Container scrollável
                    for _, row in df_sim_hist.iterrows():
                        st.markdown(f"""
                        <div style="
                            background: rgba(30, 41, 59, 0.4);
                            border-left: 5px solid #8B5CF6;
                            padding: 20px;
                            border-radius: 12px;
                            margin-bottom: 20px;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div>
                                    <div style="font-size: 0.8rem; color: #94A3B8;">
                                        {pd.to_datetime(row['data_estudo']).strftime('%d/%m/%Y')} 
                                        <span style="margin-left: 10px; color: #00FFFF;">⏱️ {int(row['tempo']//60)}h{int(row['tempo']%60):02d}min</span>
                                    </div>
                                    <div style="font-size: 1.2rem; font-weight: 700; color: white;">{row['assunto']}</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 1.8rem; font-weight: 900; color: #00FFFF;">{row['taxa']:.1f}%</div>
                                    <div style="font-size: 0.8rem; color: #94A3B8;">{int(row['acertos'])}/{int(row['total'])} acertos</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Extrair detalhamento do comentário
                        # Formato: "Banca: X | Detalhes: Materia: A/B | Materia2: C/D"
                        comentario = row.get('comentarios', '')
                        if "Detalhes:" in comentario:
                            try:
                                detalhes_str = comentario.split("Detalhes:")[1].strip()
                                items = [it.strip() for it in detalhes_str.split("|")]
                                
                                st.markdown("<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>", unsafe_allow_html=True)
                                for item in items:
                                    if ":" in item:
                                        mat, score = item.split(":", 1)
                                        if "/" in score:
                                            ac, to = score.split("/")
                                            perc = (int(ac)/int(to)*100) if int(to) > 0 else 0
                                            bar_color = "#10B981" if perc >= 75 else "#F59E0B" if perc >= 50 else "#EF4444"
                                            
                                            st.markdown(f"""
                                            <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                                                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #E2E8F0; margin-bottom: 4px;">
                                                    <span>{mat}</span>
                                                    <span style="font-weight: 700;">{score.strip()} ({int(perc)}%)</span>
                                                </div>
                                                <div style="height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                                                    <div style="width: {perc}%; height: 100%; background: {bar_color};"></div>
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                st.markdown("</div>", unsafe_allow_html=True)
                            except Exception:
                                st.write(f"Ref: {comentario}")
                        else:
                            st.write(f"Notas: {comentario}")
                            
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Adicionar botões de ação para Simulado
                        col_act1, col_act2, col_act3 = st.columns([1, 1, 4])
                        if col_act1.button("✏️", key=f"edit_sim_{row['id']}", help="Editar simulado", use_container_width=True):
                            st.session_state.edit_id_simulado = row['id']
                            st.rerun()
                        
                        if col_act2.button("🗑️", key=f"del_sim_{row['id']}", help="Excluir simulado", use_container_width=True):
                            if st.session_state.get(f"confirm_del_sim_{row['id']}", False):
                                try:
                                    supabase.table("registros_estudos").delete().eq("id", row['id']).execute()
                                    st.toast("✅ Simulado excluído!")
                                    st.session_state[f"confirm_del_sim_{row['id']}"] = False
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {e}")
                            else:
                                st.session_state[f"confirm_del_sim_{row['id']}"] = True
                                st.rerun()
                        
                        if st.session_state.get(f"confirm_del_sim_{row['id']}", False):
                            st.warning("⚠️ Clique em 🗑️ novamente para confirmar")

                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Nenhum simulado registrado ainda.")
            st.markdown('</div>', unsafe_allow_html=True)

# --- ABA: HISTÓRICO ---
    elif menu == "Histórico":
            st.markdown('<h2 class="main-title">📜 Histórico de Estudos</h2>', unsafe_allow_html=True)
        
            if not df.empty:
                df_h = df.copy()
                df_h['data_estudo_display'] = pd.to_datetime(df_h['data_estudo']).dt.strftime('%d/%m/%Y')
            
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            
                # Filtros
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    mat_filter = st.selectbox("Filtrar por Matéria:", ["Todas"] + list(df_h['materia'].unique()), key="mat_hist_filter")
                with col_f2:
                    rel_options = ["Todas"] + list(range(1, 11))
                    rel_filter = st.selectbox("Filtrar por Relevância:", rel_options, index=0, key="rel_hist_filter")
                with col_f3:
                    ordem = st.selectbox("Ordenar por:", ["Mais Recente", "Mais Antigo", "Maior Taxa", "Menor Taxa", "Maior Relevância"], key="ord_hist")
                with col_f4:
                    st.write("")  # Espaçamento
            
                # Aplicar filtros
                df_filtered = df_h.copy()
                if mat_filter != "Todas":
                    df_filtered = df_filtered[df_filtered['materia'] == mat_filter]
                
                # Filtrar por relevância (considerando 5 como padrão se nulo ou coluna ausente)
                df_filtered['rel_val'] = df_filtered['relevancia'].fillna(5).astype(int) if 'relevancia' in df_filtered.columns else 5
                
                if rel_filter != "Todas":
                    df_filtered = df_filtered[df_filtered['rel_val'] == int(rel_filter)]
            
                # Aplicar ordenação
                if ordem == "Mais Recente":
                    df_filtered = df_filtered.sort_values('data_estudo', ascending=False)
                elif ordem == "Mais Antigo":
                    df_filtered = df_filtered.sort_values('data_estudo', ascending=True)
                elif ordem == "Maior Taxa":
                    df_filtered = df_filtered.sort_values('taxa', ascending=False)
                elif ordem == "Menor Taxa":
                    df_filtered = df_filtered.sort_values('taxa', ascending=True)
                elif ordem == "Maior Relevância":
                    df_filtered = df_filtered.sort_values('rel_val', ascending=False)
            
                st.divider()
            
                # Resumo
                total_registros = len(df_filtered)
                total_acertos_hist = df_filtered['acertos'].sum()
                total_questoes_hist = df_filtered['total'].sum()
                taxa_media = (total_acertos_hist / total_questoes_hist * 100) if total_questoes_hist > 0 else 0
                tempo_total = df_filtered['tempo'].sum() / 60
            
                col_info1, col_info2, col_info3 = st.columns(3)
                col_info1.metric("📝 Registros", total_registros)
                col_info2.metric("🎯 Taxa Média", f"{taxa_media:.1f}%")
                col_info3.metric("⏱️ Tempo Total", f"{tempo_total:.1f}h")
            
                st.divider()
            
                # --- MODAL DE EDIÇÃO ---
                if st.session_state.edit_id is not None:
                    registro_edit = df[df['id'] == st.session_state.edit_id].iloc[0]
                
                    st.markdown('<div class="modern-card" style="border: 2px solid rgba(255, 75, 75, 0.3); background: rgba(255, 75, 75, 0.05);">', unsafe_allow_html=True)
                    st.markdown("### ✏️ Editar Registro")
                
                    with st.form("form_edit_registro", clear_on_submit=False):
                        col_e1, col_e2 = st.columns([2, 1])
                        dt_edit = col_e1.date_input(
                            "Data do Estudo", 
                            value=pd.to_datetime(registro_edit['data_estudo']).date(), 
                            format="DD/MM/YYYY", 
                            key="dt_edit"
                        )
                        tm_edit = col_e2.text_input(
                            "Tempo (HHMM)", 
                            value=f"{int(registro_edit['tempo']//60):02d}{int(registro_edit['tempo']%60):02d}", 
                            key="tm_edit"
                        )
                    
                        mat_edit = st.selectbox(
                            "Disciplina", 
                            list(dados.get('materias', {}).keys()), 
                            index=list(dados.get('materias', {}).keys()).index(registro_edit['materia']), 
                            key="mat_edit"
                        )
                        assuntos_edit = dados['materias'].get(mat_edit, ["Geral"])
                        ass_edit = st.selectbox(
                            "Assunto", 
                            assuntos_edit, 
                            index=assuntos_edit.index(registro_edit['assunto']) if registro_edit['assunto'] in assuntos_edit else 0, 
                            key="ass_edit"
                        )
                    
                        st.divider()
                    
                        ca_edit, ct_edit = st.columns(2)
                        ac_edit = ca_edit.number_input("Questões Acertadas", value=int(registro_edit['acertos']), min_value=0, key="ac_edit")
                        to_edit = ct_edit.number_input("Total de Questões", value=int(registro_edit['total']), min_value=0, key="to_edit")
                    
                        # Dificuldade
                        st.markdown("##### 🎯 Classificação de Dificuldade")
                        dif_edit = st.segmented_control(
                            "Classificação:",
                            ["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                            default=registro_edit.get('dificuldade', '🟡 Médio'),
                            key="dif_edit"
                        )

                        # NOVO: Relevância na edição
                        rel_edit = st.selectbox(
                            "Relevância (Incidência em Prova):",
                            options=list(range(1, 11)),
                            index=int(registro_edit.get('relevancia', 5)) - 1,
                            key="rel_edit"
                        )
                    
                        tempo_rec, desc_rec = tempo_recomendado_rev24h(dif_edit)
                        st.info(f"💡 **{dif_edit}** → Revisar em 24h: ~{tempo_rec}min ({desc_rec})")
                    
                        st.divider()
                        com_edit = st.text_area(
                            "Anotações / Comentários", 
                            value=registro_edit.get('comentarios', ''), 
                            key="com_edit",
                            height=100
                        )
                    
                        # NOVO: Controle de ciclo de revisões na edição
                        st.markdown("##### 🔄 Ciclo de Revisões")
                        foi_concluido = all([registro_edit.get('rev_24h'), registro_edit.get('rev_07d'), registro_edit.get('rev_15d')])
                        gerar_rev_edit = st.checkbox(
                            "Manter ciclo de revisões ativo?", 
                            value=not foi_concluido,
                            help="Se desmarcado, as revisões deste registro serão marcadas como concluídas.",
                            key="gerar_rev_edit"
                        )
                    
                        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
                    
                        if col_btn1.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True, type="primary"):
                            try:
                                t_b = formatar_tempo_para_bigint(tm_edit)
                                taxa = (ac_edit/to_edit*100 if to_edit > 0 else 0)
                            
                                supabase.table("registros_estudos").update({
                                    "data_estudo": dt_edit.strftime('%Y-%m-%d'),
                                    "materia": mat_edit,
                                    "assunto": ass_edit,
                                    "acertos": ac_edit,
                                    "total": to_edit,
                                    "taxa": taxa,
                                    "dificuldade": dif_edit,
                                    "relevancia": rel_edit, # Novo campo
                                    "comentarios": com_edit,
                                    "tempo": t_b,
                                    "rev_24h": bool(not gerar_rev_edit if not gerar_rev_edit else (False if foi_concluido else registro_edit['rev_24h'])),
                                    "rev_07d": bool(not gerar_rev_edit if not gerar_rev_edit else (False if foi_concluido else registro_edit['rev_07d'])),
                                    "rev_15d": bool(not gerar_rev_edit if not gerar_rev_edit else (False if foi_concluido else registro_edit['rev_15d'])),
                                    "rev_30d": bool(not gerar_rev_edit if not gerar_rev_edit else (False if foi_concluido else registro_edit['rev_30d']))
                                }).eq("id", st.session_state.edit_id).execute()
                            
                                st.success("✅ Registro atualizado com sucesso!")
                                time.sleep(1)
                                st.session_state.edit_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao atualizar: {e}")
                    
                        if col_btn2.form_submit_button("❌ CANCELAR", use_container_width=True, type="secondary"):
                            st.session_state.edit_id = None
                            st.rerun()
                
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.divider()
            
                # --- LISTA DE REGISTROS ---
                st.markdown("##### 📝 Gerenciar Registros")
            
                if len(df_filtered) == 0:
                    st.info("Nenhum registro encontrado com os filtros selecionados.")
                else:
                    for index, row in df_filtered.iterrows():
                        with st.container():
                            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                        
                            # Layout principal
                            info_col, metrics_col, action_col = st.columns([3, 1.5, 1.2])
                        
                            with info_col:
                                # Informações do Registro
                                taxa_color = "#00FF00" if row['taxa'] >= 80 else "#FFD700" if row['taxa'] >= 60 else "#FF4B4B"
                            
                                st.markdown(f"""
                                    <div style="margin-bottom: 8px;">
                                        <span style="color: #adb5bd; font-size: 0.85rem; font-weight: 600;">📅 {row['data_estudo_display']}</span>
                                        <span style="color: {taxa_color}; font-size: 0.85rem; font-weight: 700; margin-left: 15px;">
                                            {row['taxa']:.1f}%
                                        </span>
                                        <span style="color: #adb5bd; font-size: 0.85rem; margin-left: 15px;">
                                            {row.get('dificuldade', '🟡 Médio')}
                                        </span>
                                        <span style="color: #F59E0B; font-size: 0.85rem; font-weight: 700; margin-left: 15px;">
                                            ⭐ R{int(row.get('relevancia', 5))}
                                        </span>
                                    </div>
                                    <h4 style="margin: 0; color: #fff; font-size: 1.1rem;">{row['materia']}</h4>
                                    <p style="color: #adb5bd; font-size: 0.9rem; margin: 5px 0 0 0;">{row['assunto']}</p>
                                """, unsafe_allow_html=True)
                            
                                # Anotações
                                if row.get('comentarios'):
                                    with st.expander("📝 Ver Anotações", expanded=False):
                                        st.markdown(f"<p style='color: #adb5bd; font-size: 0.9rem;'>{row['comentarios']}</p>", unsafe_allow_html=True)
                        
                            with metrics_col:
                                # Métricas - CORREÇÃO: string formatada corretamente
                                html_metricas = f"""
                                    <div style="text-align: right;">
                                        <div style="font-size: 0.8rem; color: #adb5bd; margin-bottom: 5px;">Desempenho</div>
                                        <div style="font-size: 1.3rem; font-weight: 700; color: #fff;">
                                            {int(row['acertos'])}/{int(row['total'])}
                                        </div>
                                        <div style="font-size: 0.75rem; color: #adb5bd;">
                                            ⏱️ {int(row['tempo']//60)}h{int(row['tempo']%60):02d}m
                                        </div>
                                    </div>
                                """
                                st.markdown(html_metricas, unsafe_allow_html=True)
                        
                            with action_col:
                                col_a1, col_a2 = st.columns(2, gap="small")
                            
                                # Botão Editar
                                if col_a1.button("✏️", key=f"edit_{row['id']}", help="Editar registro", use_container_width=True):
                                    st.session_state.edit_id = row['id']
                                    st.rerun()
                            
                                # Botão Excluir com confirmação
                                if col_a2.button("🗑️", key=f"del_{row['id']}", help="Excluir registro", use_container_width=True):
                                    try:
                                        # Confirmação via dialog
                                        if st.session_state.get(f"confirm_delete_{row['id']}", False):
                                            supabase.table("registros_estudos").delete().eq("id", row['id']).execute()
                                            st.toast("✅ Registro excluído com sucesso!", icon="✅")
                                            time.sleep(0.5)
                                            st.session_state[f"confirm_delete_{row['id']}"] = False
                                            st.rerun()
                                        else:
                                            st.session_state[f"confirm_delete_{row['id']}"] = True
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao excluir: {e}")
                            
                                # Confirmação visual
                                if st.session_state.get(f"confirm_delete_{row['id']}", False):
                                    st.warning(f"⚠️ Clique em 🗑️ novamente para confirmar exclusão", icon="⚠️")
                        
                            st.markdown('</div>', unsafe_allow_html=True)
            
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("📚 Nenhum registro de estudo encontrado ainda. Comece a estudar!")

    # --- ABA: RELATÓRIOS ---
    elif menu == "Relatórios":
        st.markdown(f'<h1 style="background: linear-gradient(135deg, #8B5CF6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size:2.5rem; margin-bottom:1rem;">📑 Central de Relatórios</h1>', unsafe_allow_html=True)
        st.markdown("<p style='color: #94A3B8; font-size: 1.1rem;'>Gere documentos consolidados e análises estratégicas para o seu estudo.</p>", unsafe_allow_html=True)
        
        st.divider()
        
        # Calcular Projeção
        proj = calcular_projecao_conclusao(df_estudos, dados)
        
        # VISUALIZAÇÃO DE PROJEÇÃO (FULL WIDTH)
        if proj:
            st.markdown(f"""
                <div style="background: {COLORS['bg_card']}; padding: 25px; border-radius: 20px; border: 1px solid {COLORS['border']}; margin-bottom: 30px;">
                    <h3 style="color: #fff; margin-bottom: 15px;">📅 Previsão do Edital</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: center;">
                        <div style="flex: 1; min-width: 200px;">
                            <div style="color: #94A3B8; font-size: 0.7rem; text-transform: uppercase;">Progresso Único</div>
                            <div style="font-size: 2rem; font-weight: 800; color: #06B6D4;">{proj['progresso']:.1f}%</div>
                        </div>
                        <div style="flex: 1; min-width: 200px;">
                            <div style="color: #94A3B8; font-size: 0.7rem;">DATA ESTIMADA</div>
                            <div style="color: #fff; font-size: 1.2rem; font-weight: 700;">{proj['data_fim'].strftime('%d/%m/%Y')}</div>
                        </div>
                        <div style="flex: 1; min-width: 200px;">
                            <div style="color: #94A3B8; font-size: 0.7rem;">DIAS RESTANTES</div>
                            <div style="color: #fff; font-size: 1.2rem; font-weight: 700;">{proj['dias_para_fim']} dias</div>
                        </div>
                        <div style="flex: 1; min-width: 200px;">
                            <div style="color: #94A3B8; font-size: 0.7rem;">RITMO (Tópicos/sem)</div>
                            <div style="color: #10B981; font-size: 1.2rem; font-weight: 700;">{proj['ritmo']:.1f}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Cadastre o edital para ver a previsão.")

        col_rel1, col_rel2, col_rel3 = st.columns(3)
        
        with col_rel1:
            st.markdown(f"""
                <div style="background: {COLORS['bg_card']}; padding: 25px; border-radius: 20px; border: 1px solid {COLORS['border']}; height: 350px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <h3 style="color: #fff; margin-bottom: 10px;">🏆 Relatório Estratégico</h3>
                        <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 20px;">
                            Análise de priorização (Esforço x Resultado), 
                            detalhamento por matéria e gargalos de assuntos.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Botão fora do HTML para funcionar o Streamlit
            if st.button("🚀 Gerar PDF Estratégico", use_container_width=True, key="btn_gerar_pdf"):
                try:
                    pdf_bytes = gerar_pdf_estratégico(df_estudos, missao, df_raw, proj)
                    st.success("✅ Relatório gerado!")
                    st.download_button(
                        label="📥 Baixar (PDF)",
                        data=pdf_bytes,
                        file_name=f"Relatorio_{missao}_{get_br_date().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro: {e}")

        with col_rel2:
            st.markdown(f"""
                <div style="background: {COLORS['bg_card']}; padding: 25px; border-radius: 20px; border: 1px solid {COLORS['border']}; height: 350px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <h3 style="color: #fff; margin-bottom: 10px;">🕒 Diário de Horas</h3>
                        <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 20px;">
                            Ranking de dedicação por matéria (do maior para o menor), com destaque para seu foco principal e detalhamento de tópicos.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📊 Gerar Diário de Horas", use_container_width=True, key="btn_gerar_pdf_horas"):
                try:
                    pdf_bytes_h = gerar_pdf_carga_horaria(df_estudos, missao)
                    st.success("✅ Log gerado!")
                    st.download_button(
                        label="📥 Baixar Diário (PDF)",
                        data=pdf_bytes_h,
                        file_name=f"Carga_Horaria_{missao}_{get_br_date().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro: {e}")

        with col_rel3:
            st.markdown(f"""
                <div style="background: {COLORS['bg_card']}; padding: 25px; border-radius: 20px; border: 1px solid {COLORS['border']}; height: 350px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <h3 style="color: #fff; margin-bottom: 10px;">📝 Relatório de Simulados</h3>
                        <p style="color: #94A3B8; font-size: 0.9rem; margin-bottom: 20px;">
                            Histórico consolidado de todas as suas provas, com evolução de notas, média geral e recordes.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📜 Gerar Histórico Simulados", use_container_width=True, key="btn_gerar_pdf_sim"):
                try:
                    # Garantir que df_simulados esteja disponível
                    pdf_bytes_s = gerar_pdf_simulados(df_simulados, missao)
                    st.success("✅ Histórico gerado!")
                    st.download_button(
                        label="📥 Baixar Simulados (PDF)",
                        data=pdf_bytes_s,
                        file_name=f"Simulados_{missao}_{get_br_date().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.divider()

        # --- SEÇÃO: BENCHMARK DE SIMULADOS ---
        st.markdown('<h3 style="color: #fff; margin-bottom: 20px;">📈 Benchmark de Simulados</h3>', unsafe_allow_html=True)
        
        # Usar df_simulados carregado no início da aplicação
        df_sim_bench = df_simulados.sort_values('data_estudo')
        
        if df_sim_bench.empty:
            st.info("Registre pelo menos um Simulado para habilitar o Benchmark.")
        else:
            col_b1, col_b2 = st.columns([1, 2])
            
            with col_b1:
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                # Configurar Nota de Corte
                st.session_state.nota_corte_alvo = st.slider(
                    "Sua Nota de Corte Alvo (%)", 
                    min_value=50, max_value=100, 
                    value=st.session_state.nota_corte_alvo,
                    step=1
                )
                
                # Métricas de Evolução
                ult_nota = df_sim_bench['taxa'].iloc[-1]
                med_nota = df_sim_bench['taxa'].mean()
                diff_corte = ult_nota - st.session_state.nota_corte_alvo
                
                st.markdown("---")
                st.markdown(f"**Última Nota:** {ult_nota:.1f}%")
                if diff_corte >= 0:
                    st.success(f"🔥 +{diff_corte:.1f}% ACIMA da meta!")
                else:
                    st.warning(f"⚠️ {abs(diff_corte):.1f}% ABAIXO da meta.")
                
                st.markdown(f"**Média Geral:** {med_nota:.1f}%")
                
                # Tendência
                if len(df_sim_bench) >= 2:
                    tendencia = "Subindo 📈" if df_sim_bench['taxa'].iloc[-1] > df_sim_bench['taxa'].iloc[-2] else "Caindo 📉" if df_sim_bench['taxa'].iloc[-1] < df_sim_bench['taxa'].iloc[-2] else "Estável ➖"
                else:
                    tendencia = "Mantenha o Ritmo!"
                
                st.markdown(f"**Tendência:** {tendencia}")
                st.markdown('</div>', unsafe_allow_html=True)

            with col_b2:
                # Gráfico de Evolução de simulados
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                df_plt = df_sim_bench.copy()
                df_plt['data_estudo'] = pd.to_datetime(df_plt['data_estudo'])
                
                fig_bench = go.Figure()
                
                # Linha de Corte
                fig_bench.add_hline(
                    y=st.session_state.nota_corte_alvo, 
                    line_dash="dash", 
                    line_color="#EF4444", 
                    annotation_text="Nota de Corte", 
                    annotation_position="top left"
                )
                
                # Linha de Performance
                fig_bench.add_trace(go.Scatter(
                    x=df_plt['data_estudo'], 
                    y=df_plt['taxa'],
                    name='Seu Desempenho',
                    line=dict(color='#06B6D4', width=3),
                    mode='lines+markers',
                    marker=dict(size=8, symbol='diamond')
                ))
                
                fig_bench.update_layout(
                    title="Evolução de Notas vs Meta",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#fff"),
                    height=300,
                    margin=dict(t=30, b=10, l=10, r=10),
                    yaxis=dict(range=[max(0, df_plt['taxa'].min()-10), 105], gridcolor='rgba(255,255,255,0.05)')
                )
                
                st.plotly_chart(fig_bench, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA: CONFIGURAR ---
    elif menu == "Configurar":
        st.markdown('<h2 class="main-title">⚙️ Configurações</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-subtitle">Gerenciar missões e preferências globais</p>', unsafe_allow_html=True)

        # SEÇÃO: TROCAR MISSÃO (Conforme Plano de Profissionalização)
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('### 📌 Seleção de Missão Foco', unsafe_allow_html=True)
        
            ed = get_editais(supabase)
            if ed:
                nomes_missoes = list(ed.keys())
                try:
                    indice_atual = nomes_missoes.index(missao) if missao in nomes_missoes else 0
                except (ValueError, IndexError):
                    indice_atual = 0
            
                nova_missao = st.selectbox(
                    "Selecione o concurso que deseja focar agora:",
                    options=nomes_missoes,
                    index=indice_atual,
                    help="Isso alterará os dados exibidos em todo o aplicativo de acordo com a missão escolhida."
                )
            
                if nova_missao != missao:
                    st.session_state.missao_ativa = nova_missao
                    st.success(f"✅ Missão alterada para: {nova_missao}")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Nenhuma missão cadastrada encontrada.")
                if st.button("➕ Cadastrar Nova Missão"):
                    st.session_state.missao_ativa = None
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # Mostrar data atual se existir
        try:
            data_prova_atual = pd.to_datetime(data_prova_direta).date() if data_prova_direta else None
        except Exception:
            data_prova_atual = None

        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('### Dados do Edital', unsafe_allow_html=True)
            st.write(f"**Concurso:** {missao}")
            st.write(f"**Cargo:** {dados.get('cargo', '—')}")
            st.write(f"**Data da Prova (atual):** {data_prova_atual.strftime('%d/%m/%Y') if data_prova_atual else '—'}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Formulário para editar data da prova
        with st.form("form_editar_edital"):
            st.markdown("### 📅 Ajustar Data da Prova")
        
            nova_data_escolhida = st.date_input(
                "Selecione a data da prova", 
                value=(data_prova_atual or datetime.date.today())
            )
        
            remover = st.checkbox("Remover data da prova (deixar em branco)")

            submitted = st.form_submit_button("Salvar alterações", use_container_width=True, type="primary")
        
            if submitted:
                try:
                    valor_final = None if remover else nova_data_escolhida.strftime("%Y-%m-%d")
                
                    # 1. SALVA NO BANCO - Atualiza a tabela CORRETA: editais_materias
                    res = supabase.table("editais_materias").update({"data_prova": valor_final}).eq("concurso", missao).execute()
                
                    if res.data:
                        # 2. LIMPA A MEMÓRIA DO APP
                        st.cache_data.clear() 
                    
                        # 3. ATUALIZA O ESTADO PARA FORÇAR RECARREGAMENTO
                        st.session_state.missao_ativa = missao
                    
                        st.success(f"✅ Data atualizada no banco! Recarregando...")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {e}")

        # Seção para adicionar/gerenciar matérias
        st.divider()
        st.markdown("### 📚 Gerenciar Matérias e Assuntos")
    
        with st.container():
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        
            # Buscar matérias do banco de dados
            try:
                res_materias = supabase.table("editais_materias").select("id, materia, topicos").eq("concurso", missao).execute()
                registros_materias = res_materias.data
            except Exception as e:
                st.error(f"Erro ao buscar matérias: {e}")
                registros_materias = []
        
            # --- NOVA SEÇÃO: EXCLUSÃO EM MASSA ---
            if registros_materias:
                st.markdown("#### 🗑️ Exclusão em Massa de Matérias")
                st.warning("⚠️ Atenção: Esta ação excluirá permanentemente as matérias selecionadas e TODOS os registros de estudo relacionados!", icon="⚠️")
            
                # Criar lista de matérias com checkboxes
                materias_selecionadas = []
            
                for reg in registros_materias:
                    col_check, col_info = st.columns([0.1, 0.9])
                    with col_check:
                        selecionada = st.checkbox("", key=f"sel_{reg['id']}", help=f"Selecionar {reg['materia']} para exclusão")
                    with col_info:
                        st.write(f"**{reg['materia']}** - {len(reg['topicos'] if reg['topicos'] else [])} assuntos")
                
                    if selecionada:
                        materias_selecionadas.append(reg)
            
                # Botão para excluir matérias selecionadas
                if materias_selecionadas:
                    st.error(f"⚠️ **{len(materias_selecionadas)} matéria(s) selecionada(s) para exclusão:**")
                    for mat in materias_selecionadas:
                        st.write(f"• {mat['materia']}")
                
                    # Confirmação adicional
                    confirmacao = st.checkbox("✅ Confirmo que compreendo que esta ação é irreversível e excluirá todos os registros relacionados", 
                                            key="confirm_exclusao_massa")
                
                    if confirmacao:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🚨 EXCLUIR MATÉRIAS SELECIONADAS", type="primary", use_container_width=True):
                                try:
                                    contador_exclusoes = 0
                                    contador_registros = 0
                                
                                    for mat in materias_selecionadas:
                                        # Primeiro, contar registros de estudos associados a esta matéria
                                        try:
                                            res_contagem = supabase.table("registros_estudos")\
                                                .select("id", count="exact")\
                                                .eq("concurso", missao)\
                                                .eq("materia", mat['materia'])\
                                                .execute()
                                        
                                            # CORREÇÃO: Verificar se count existe e não é None
                                            if hasattr(res_contagem, 'count') and res_contagem.count is not None:
                                                contador_registros += res_contagem.count
                                        except Exception:
                                            # Se não conseguir contar, continuar mesmo assim
                                            pass
                                    
                                        # Excluir registros de estudos dessa matéria
                                        try:
                                            supabase.table("registros_estudos").delete()\
                                                .eq("concurso", missao)\
                                                .eq("materia", mat['materia'])\
                                                .execute()
                                        except Exception as e:
                                            st.warning(f"Aviso: Não foi possível excluir todos os registros de '{mat['materia']}': {e}")
                                    
                                        # Excluir a matéria da tabela editais_materias
                                        try:
                                            supabase.table("editais_materias").delete().eq("id", mat['id']).execute()
                                            contador_exclusoes += 1
                                        except Exception as e:
                                            st.error(f"Erro ao excluir matéria '{mat['materia']}': {e}")
                                
                                    st.success(f"✅ **{contador_exclusoes} matéria(s) excluída(s) com sucesso!**")
                                    if contador_registros > 0:
                                        st.info(f"🗑️ **{contador_registros} registro(s) de estudo relacionados foram removidos.**")
                                
                                    # Limpar cache e recarregar
                                    st.cache_data.clear()
                                    time.sleep(2)
                                    st.rerun()
                                
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir matérias: {e}")
                    
                        with col_btn2:
                            if st.button("❌ Cancelar Exclusão", type="secondary", use_container_width=True):
                                st.rerun()
            
                st.divider()
        
            # Mostrar matérias atuais
            if registros_materias:
                st.markdown("#### ✏️ Editar Matérias Individuais")
            
                # Para cada matéria, criar um expander com opções de edição
                for reg in registros_materias:
                    materia = reg['materia']
                    topicos = reg['topicos'] if reg['topicos'] else []
                    id_registro = reg['id']
                
                    with st.expander(f"📖 {materia} ({len(topicos)} assuntos)"):
                        # Mostrar assuntos atuais
                        st.markdown("**Assuntos atuais:**")
                        if topicos:
                            for i, topico in enumerate(topicos):
                                col1, col2 = st.columns([5, 1])
                                col1.write(f"• {topico}")
                                # Botão para remover assunto
                                if col2.button("🗑️", key=f"del_{id_registro}_{i}", help="Remover assunto", use_container_width=True):
                                    try:
                                        # Remover o tópico da lista
                                        novos_topicos = [t for t in topicos if t != topico]
                                        # Atualizar no banco
                                        supabase.table("editais_materias").update({"topicos": novos_topicos}).eq("id", id_registro).execute()
                                        st.success(f"✅ Assunto '{topico}' removido!")
                                        time.sleep(1)
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao remover assunto: {e}")
                        else:
                            st.info("Nenhum assunto cadastrado.")
                    
                        st.divider()
                    
                        # Formulário para adicionar novos assuntos
                        with st.form(f"form_novo_assunto_{id_registro}"):
                            st.markdown("**Adicionar novos assuntos (em massa)**")
                        
                            # Opções de entrada
                            metodo_entrada = st.selectbox(
                                "Como deseja adicionar os assuntos?",
                                ["Um por um", "Vários com separador", "Vários por linhas"],
                                key=f"metodo_{id_registro}"
                            )
                        
                            # Inicializar variável para evitar NameError
                            assuntos_para_adicionar = []
                        
                            if metodo_entrada == "Um por um":
                                # Modo tradicional
                                novo_assunto = st.text_input("Nome do assunto", placeholder="Ex: Princípios fundamentais", key=f"novo_assunto_single_{id_registro}")
                                assuntos_para_adicionar = [novo_assunto] if novo_assunto else []
                            
                            elif metodo_entrada == "Vários com separador":
                                # Modo com separador
                                col_sep1, col_sep2 = st.columns([2, 1])
                                with col_sep1:
                                    texto_assuntos = st.text_area(
                                        "Digite os assuntos separados por:",
                                        placeholder="Ex: Princípios fundamentais; Organização do Estado; Direitos e garantias fundamentais",
                                        key=f"texto_assuntos_{id_registro}",
                                        height=100
                                    )
                                with col_sep2:
                                    separador = st.selectbox(
                                        "Separador",
                                        ["; (ponto e vírgula)", ", (vírgula)", ". (ponto)", "- (hífen)", "| (pipe)"],
                                        key=f"separador_{id_registro}"
                                    )
                                    # Mapear separador
                                    separador_map = {
                                        "; (ponto e vírgula)": ";",
                                        ", (vírgula)": ",",
                                        ". (ponto)": ".",
                                        "- (hífen)": "-",
                                        "| (pipe)": "|"
                                    }
                                    separador_char = separador_map[separador]
                            
                                if texto_assuntos:
                                    # Processar os assuntos
                                    assuntos_brutos = texto_assuntos.split(separador_char)
                                    assuntos_para_adicionar = [a.strip() for a in assuntos_brutos if a.strip()]
                                else:
                                    assuntos_para_adicionar = []
                                
                                    # Mostrar prévia
                                    if assuntos_para_adicionar:
                                        st.info(f"**Prévia:** Serão adicionados {len(assuntos_para_adicionar)} assuntos")
                                        with st.expander("Ver assuntos"):
                                            for a in assuntos_para_adicionar:
                                                st.write(f"• {a}")
                            else:  # "Vários por linhas"
                                # Modo com múltiplas linhas
                                texto_assuntos = st.text_area(
                                    "Digite um assunto por linha:",
                                    placeholder="Princípios fundamentais\nOrganização do Estado\nDireitos e garantias fundamentais\n...",
                                    key=f"texto_assuntos_linhas_{id_registro}",
                                    height=120
                                )
                            
                                if texto_assuntos:
                                    # Processar os assuntos (uma por linha)
                                    assuntos_brutos = texto_assuntos.split("\n")
                                    assuntos_para_adicionar = [a.strip() for a in assuntos_brutos if a.strip()]
                                else:
                                    assuntos_para_adicionar = []
                                
                                    # Mostrar prévia
                                    if assuntos_para_adicionar:
                                        st.info(f"**Prévia:** Serão adicionados {len(assuntos_para_adicionar)} assuntos")
                                        with st.expander("Ver assuntos"):
                                            for a in assuntos_para_adicionar:
                                                st.write(f"• {a}")
                        
                            col_btn1, col_btn2 = st.columns(2)
                            if col_btn1.form_submit_button("➕ Adicionar Assuntos", use_container_width=True):
                                if assuntos_para_adicionar:
                                    try:
                                        # Buscar tópicos atuais
                                        if not topicos:
                                            topicos = []
                                        # Adicionar novos tópicos à lista (evitar duplicados)
                                        for assunto in assuntos_para_adicionar:
                                            if assunto not in topicos:
                                                topicos.append(assunto)
                                            else:
                                                st.warning(f"Assunto '{assunto}' já existe e foi ignorado.")
                                    
                                        # Atualizar no banco
                                        supabase.table("editais_materias").update({"topicos": topicos}).eq("id", id_registro).execute()
                                        st.success(f"✅ {len(assuntos_para_adicionar)} assunto(s) adicionado(s) com sucesso!")
                                        time.sleep(1)
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao adicionar assuntos: {e}")
                                else:
                                    st.warning("⚠️ Nenhum assunto válido para adicionar.")
                        
                            if col_btn2.form_submit_button("✏️ Renomear Matéria", use_container_width=True, type="secondary"):
                                # Abrir modal para renomear matéria
                                st.session_state[f"renomear_{id_registro}"] = True
                                st.rerun()
                    
                        # Modal para renomear matéria
                        if st.session_state.get(f"renomear_{id_registro}", False):
                            st.markdown('<div style="background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 8px; margin-top: 10px;">', unsafe_allow_html=True)
                            novo_nome = st.text_input("Novo nome da matéria", value=materia, key=f"novo_nome_{id_registro}")
                        
                            col_r1, col_r2 = st.columns(2)
                            if col_r1.button("💾 Salvar", key=f"salvar_nome_{id_registro}", use_container_width=True):
                                if novo_nome and novo_nome != materia:
                                    try:
                                        # Atualizar o nome da matéria
                                        supabase.table("editais_materias").update({"materia": novo_nome}).eq("id", id_registro).execute()
                                    
                                        # Atualizar também nos registros de estudo
                                        supabase.table("registros_estudos").update({"materia": novo_nome}).eq("concurso", missao).eq("materia", materia).execute()
                                    
                                        st.success(f"✅ Matéria renomeada para '{novo_nome}'!")
                                        time.sleep(1)
                                        st.session_state[f"renomear_{id_registro}"] = False
                                        st.cache_data.clear()  # Limpar cache para atualizar a interface
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao renomear matéria: {e}")
                        
                            if col_r2.button("❌ Cancelar", key=f"cancelar_nome_{id_registro}", use_container_width=True):
                                st.session_state[f"renomear_{id_registro}"] = False
                                st.rerun()
                        
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Nenhuma matéria cadastrada ainda.")
        
            # Formulário para adicionar nova matéria
            st.divider()
            st.markdown("#### ➕ Adicionar Nova Matéria")
        
            with st.form("form_nova_materia"):
                col1, col2 = st.columns([3, 1])
            
                with col1:
                    nova_materia = st.text_input("Nome da Matéria", placeholder="Ex: Direito Constitucional")
            
                with col2:
                    st.write("")  # Espaçamento
                    st.write("")  # Espaçamento
            
                # Seção para assuntos iniciais
                st.markdown("**Assuntos iniciais (opcional):**")
            
                metodo_assuntos = st.selectbox(
                    "Como deseja adicionar os assuntos iniciais?",
                    ["Sem assuntos iniciais", "Um por um", "Vários com separador", "Vários por linhas"],
                    key="metodo_assuntos_nova"
                )
            
                assuntos_iniciais = []
            
                if metodo_assuntos == "Um por um":
                    assunto_inicial = st.text_input("Assunto inicial", placeholder="Ex: Princípios fundamentais", key="assunto_inicial_single")
                    if assunto_inicial:
                        assuntos_iniciais = [assunto_inicial]
                    
                elif metodo_assuntos == "Vários com separador":
                    col_sep1, col_sep2 = st.columns([2, 1])
                    with col_sep1:
                        texto_assuntos = st.text_area(
                            "Digite os assuntos separados por:",
                            placeholder="Ex: Princípios fundamentais; Organização do Estado; Direitos e garantias fundamentais",
                            key="texto_assuntos_nova",
                            height=100
                        )
                    with col_sep2:
                        separador = st.selectbox(
                            "Separador",
                            ["; (ponto e vírgula)", ", (vírgula)", ". (ponto)", "- (hífen)", "| (pipe)"],
                            key="separador_nova"
                        )
                        # Mapear separador
                        separador_map = {
                            "; (ponto e vírgula)": ";",
                            ", (vírgula)": ",",
                            ". (ponto)": ".",
                            "- (hífen)": "-",
                            "| (pipe)": "|"
                        }
                        separador_char = separador_map[separador]
                
                    if texto_assuntos:
                        # Processar os assuntos
                        assuntos_brutos = texto_assuntos.split(separador_char)
                        assuntos_iniciais = [a.strip() for a in assuntos_brutos if a.strip()]
                    
                elif metodo_assuntos == "Vários por linhas":
                    texto_assuntos = st.text_area(
                        "Digite um assunto por linha:",
                        placeholder="Princípios fundamentais\nOrganização do Estado\nDireitos e garantias fundamentais\n...",
                        key="texto_assuntos_linhas_nova",
                        height=120
                    )
                
                    if texto_assuntos:
                        # Processar os assuntos (uma por linha)
                        assuntos_brutos = texto_assuntos.split("\n")
                        assuntos_iniciais = [a.strip() for a in assuntos_brutos if a.strip()]
            
                # Mostrar prévia se houver assuntos
                if assuntos_iniciais and metodo_assuntos != "Sem assuntos iniciais":
                    st.info(f"**Prévia:** {len(assuntos_iniciais)} assunto(s) inicial(is)")
                    with st.expander("Ver assuntos"):
                        for a in assuntos_iniciais:
                            st.write(f"• {a}")
            
                # Botão de envio
                if st.form_submit_button("Adicionar Matéria", use_container_width=True):
                    if nova_materia:
                        try:
                            # Verificar se já existe
                            res_existente = supabase.table("editais_materias").select("*").eq("concurso", missao).eq("materia", nova_materia).execute()
                            if res_existente.data:
                                st.error(f"❌ A matéria '{nova_materia}' já existe!")
                            else:
                                # Buscar cargo atual
                                cargo_atual = dados.get('cargo', '')
                                # Se não houver assuntos definidos, usar "Geral" como padrão
                                if not assuntos_iniciais:
                                    assuntos_iniciais = ["Geral"]
                            
                                # Adicionar nova matéria
                                payload = {
                                    "concurso": missao,
                                    "cargo": cargo_atual,
                                    "materia": nova_materia,
                                    "topicos": assuntos_iniciais
                                }
                                # Se houver data_prova, incluir
                                if data_prova_direta:
                                    payload["data_prova"] = data_prova_direta
                            
                                supabase.table("editais_materias").insert(payload).execute()
                                st.success(f"✅ Matéria '{nova_materia}' adicionada com {len(assuntos_iniciais)} assunto(s) inicial(is)!")
                                time.sleep(1)
                                st.cache_data.clear()  # Limpar cache para atualizar a interface
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao adicionar matéria: {e}")
                    else:
                        st.warning("⚠️ Por favor, informe o nome da matéria.")
        
            st.markdown('</div>', unsafe_allow_html=True)

        # Botão para excluir o concurso
        st.divider()
        st.markdown("### ⚠️ Zona de Perigo")
    
        with st.container():
            st.markdown('<div class="modern-card" style="border: 2px solid rgba(255, 75, 75, 0.3); background: rgba(255, 75, 75, 0.05);">', unsafe_allow_html=True)
        
            st.warning("Esta ação é irreversível!")
        
            # Checkbox de confirmação ANTES do botão (para funcionar corretamente com Streamlit)
            confirmacao_exclusao = st.checkbox(
                "✅ Confirmo que quero excluir TODOS os dados desta missão", 
                key="confirm_delete_mission"
            )
        
            # Botão só aparece habilitado se checkbox estiver marcado
            if confirmacao_exclusao:
                st.error("⚠️ ATENÇÃO: Ao clicar no botão abaixo, todos os dados serão perdidos!")
                if st.button("🗑️ EXCLUIR MISSÃO PERMANENTEMENTE", type="primary", use_container_width=True):
                    if excluir_concurso_completo(supabase, missao):  # Função do logic.py
                        st.success("Missão excluída! Redirecionando...")
                        st.session_state.missao_ativa = None
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao excluir missão. Tente novamente.")
            else:
                st.info("👆 Marque a caixa acima para habilitar o botão de exclusão.")
        
            st.markdown('</div>', unsafe_allow_html=True)
