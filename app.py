# app.py (com correção para KeyError em PDF e ordenação de simulados)

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
# 🎨 CONFIGURAÇÃO DE LAYOUT RESPONSIVO
# ============================================================================

def configurar_layout_responsivo():
    """Configura o layout para evitar problemas de espaço horizontal"""
    st.markdown("""
        <style>
        /* Garantir largura mínima para inputs */
        .stNumberInput > div > div > input {
            min-width: 80px !important;
        }
        
        .stTextInput > div > div > input {
            min-width: 100px !important;
        }
        
        .stSelectbox > div > div > div {
            min-width: 120px !important;
        }
        
        /* Melhorar responsividade em mobile */
        @media (max-width: 768px) {
            .stColumns {
                flex-direction: column !important;
            }
            
            .stColumn {
                width: 100% !important;
                margin-bottom: 1rem;
            }
        }
        
        /* Evitar overflow em containers */
        .element-container {
            overflow-x: auto;
        }
        
        /* Garantir que cards tenham largura mínima */
        .modern-card {
            min-width: 200px;
        }
        </style>
    """, unsafe_allow_html=True)

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

class EstudoPDF(FPDF):
    def header(self):
        # Título principal
        self.set_font('Arial', 'B', 16)
        self.set_text_color(139, 92, 246) # Roxo do tema
        self.cell(0, 10, 'RELATÓRIO ESTRATÉGICO DE DESEMPENHO', 0, 1, 'C')
        
        # Horário de Brasília
        agora_br = (datetime.datetime.utcnow() - datetime.timedelta(hours=3))
        self.set_font('Arial', '', 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f'Gerado em: {agora_br.strftime("%d/%m/%Y %H:%M")} (Horário de Brasília)', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_estratégico(df_estudos, missao, df_bruto, proj=None):
    pdf = EstudoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Calcular métricas principais
    t_q = df_estudos['total'].sum() if 'total' in df_estudos.columns else 0
    a_q = df_estudos['acertos'].sum() if 'acertos' in df_estudos.columns else 0
    precisao = (a_q / t_q * 100) if t_q > 0 else 0
    tempo_total = df_estudos['tempo'].sum() / 60 if 'tempo' in df_estudos.columns else 0
    
    # 1. RESUMO GERAL (Layout em Grid/Tabela)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '1. RESUMO GERAL', 0, 1, 'L')
    
    # Grid de métricas
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(248, 248, 255)
    pdf.set_text_color(100, 100, 100)
    
    # Linha 1
    pdf.cell(95, 8, ' MISSAO ATIVA', 1, 0, 'L', True)
    pdf.cell(95, 8, ' TEMPO TOTAL', 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    # Truncar nome da missão se muito longo
    missao_truncada = missao if len(missao) <= 30 else missao[:27] + "..."
    pdf.cell(95, 10, f' {missao_truncada}', 1, 0, 'L')
    pdf.cell(95, 10, f' {tempo_total:.1f} horas', 1, 1, 'L')
    
    # Linha 2
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(95, 8, ' TOTAL DE QUESTOES', 1, 0, 'L', True)
    pdf.cell(95, 8, ' PRECISAO MEDIA', 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 10, f' {int(t_q)}', 1, 0, 'L')
    pdf.cell(95, 10, f' {precisao:.1f}%', 1, 1, 'L')
    
    pdf.ln(10)
    
    # 2. MATRIZ DE PRIORIZAÇÃO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '2. MATRIZ DE PRIORIZAÇÃO (AÇÕES RECOMENDADAS)', 0, 1, 'L')
    
    # Lógica de Dados
    if 'materia' in df_estudos.columns:
        df_matriz = df_estudos.groupby('materia').agg({
            'acertos': 'sum',
            'total': 'sum',
            'tempo': 'sum'
        }).reset_index()
        df_matriz['taxa'] = (df_matriz['acertos'] / df_matriz['total'] * 100).fillna(0)
        
        df_assuntos = df_estudos.groupby(['materia', 'assunto']).agg({
            'acertos': 'sum',
            'total': 'sum'
        }).reset_index()
        df_assuntos['taxa'] = (df_assuntos['acertos'] / df_assuntos['total'] * 100).fillna(0)
        
        media_taxa = df_matriz['taxa'].mean() if not df_matriz.empty else 0
        media_volume = df_matriz['total'].mean() if not df_matriz.empty else 0
        
        focar = []
        manter = []
        revisar_base = []
        otimizar = []
        
        for _, row in df_matriz.iterrows():
            if row['taxa'] < 75 and row['total'] >= media_volume:
                focar.append(f"{row['materia']} ({row['taxa']:.0f}%)")
            elif row['taxa'] >= 75 and row['total'] >= media_volume:
                manter.append(f"{row['materia']} ({row['taxa']:.0f}%)")
            elif row['taxa'] < 75 and row['total'] < media_volume:
                revisar_base.append(f"{row['materia']} ({row['taxa']:.0f}%)")
            else:
                otimizar.append(f"{row['materia']} ({row['taxa']:.0f}%)")
    else:
        focar, manter, revisar_base, otimizar = [], [], [], []
            
    # Escrever no PDF com design melhorado
    def write_block(title, items, border_color, bg_color):
        pdf.set_fill_color(*bg_color)
        pdf.set_draw_color(*border_color)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(*border_color)
        
        # Cabeçalho do Bloco
        pdf.cell(0, 8, f"  {title}", 1, 1, 'L', True)
        
        # Conteúdo do Bloco
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(255, 255, 255)
        
        content = ", ".join(items) if items else "Nenhuma disciplina nesta categoria."
        pdf.multi_cell(0, 6, f"  {content}\n ", 1, 'L')
        pdf.ln(5)

    write_block("FOCO CRÍTICO: Baixo acerto + Alto volume", focar, (239, 68, 68), (254, 242, 242))
    write_block("MANUTENÇÃO: Bom acerto + Alto volume", manter, (16, 185, 129), (240, 253, 244))
    write_block("REVISAR BASE: Baixo acerto + Poucas questões", revisar_base, (245, 158, 11), (255, 251, 235))
    write_block("OTIMIZAR: Excelente acerto + Poucas questões", otimizar, (6, 182, 212), (236, 254, 255))
    
    pdf.ln(5)
    
    # 3. DETALHAMENTO POR MATÉRIA E ASSUNTO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '3. DESEMPENHO DETALHADO (POR MATÉRIA E ASSUNTO)', 0, 1, 'L')
    pdf.ln(2)
    
    if 'materia' in df_estudos.columns and not df_matriz.empty:
        for _, row_mat in df_matriz.sort_values('taxa').iterrows():
            # Bloco de Título da Matéria
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(139, 92, 246)
            pdf.cell(0, 8, f" {row_mat['materia'].upper()}", 1, 1, 'L', True)
            
            # Sub-cabeçalho das métricas da matéria
            pdf.set_font('Arial', 'I', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"  Média Geral: {row_mat['taxa']:.1f}% | Total de Questões: {int(row_mat['total'])}", 0, 1, 'L')
            
            # Listagem de Assuntos
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(60, 60, 60)
            if 'assunto' in df_assuntos.columns:
                topicos_da_materia = df_assuntos[df_assuntos['materia'] == row_mat['materia']].sort_values('taxa')
                
                for _, row_ass in topicos_da_materia.iterrows():
                    # Formatar linha do assunto: Assunto ............. % (Questoes)
                    nome_ass = row_ass['assunto']
                    if len(nome_ass) > 45: nome_ass = nome_ass[:42] + "..."  # Reduzido para evitar overflow
                    
                    # Usamos uma lógica de preenchimento de pontos para ficar elegante
                    texto_esq = f"      - {nome_ass}"
                    texto_dir = f"{row_ass['taxa']:.0f}% ({int(row_ass['total'])} q)"
                    
                    pdf.cell(120, 6, texto_esq, 0, 0, 'L')  # Largura reduzida de 150 para 120
                    pdf.cell(0, 6, texto_dir, 0, 1, 'R')
                    
            pdf.ln(4)
        
    # 4. PROJEÇÃO DE CONCLUSÃO
    if proj:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 10, '4. PROJEÇÃO DE CONCLUSÃO DO EDITAL', 0, 1, 'L')
        
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, f"Com base no seu ritmo de estudo dos últimos 30 dias (ou histórico total), aqui está a estimativa para conclusão do seu edital:")
        pdf.ln(5)
        
        # Grid de Projeção
        pdf.set_fill_color(240, 253, 244) # Verde bem claro
        pdf.set_draw_color(16, 185, 129)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 10, ' PROGRESSO DO EDITAL', 1, 0, 'L', True)
        pdf.cell(95, 10, ' RITMO (PACE) ATUAL', 1, 1, 'L', True)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(95, 12, f" {proj['estudados']} de {proj['total']} tópicos ({proj['progresso']:.1f}%)", 1, 0, 'L')
        pdf.cell(95, 12, f" {proj['ritmo']:.1f} tópicos por semana", 1, 1, 'L')
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 10, ' DIAS RESTANTES ESTIMADOS', 1, 0, 'L', True)
        pdf.cell(95, 10, ' DATA PREVISTA PARA TERMINAR', 1, 1, 'L', True)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(95, 12, f" {proj['dias_para_fim']} dias", 1, 0, 'L')
        pdf.cell(95, 12, f" {proj['data_fim'].strftime('%d/%m/%Y') if proj['data_fim'] else '—'}", 1, 1, 'L')
        
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(100, 100, 100)
        if proj['progresso'] > 80:
            msg = "Você está na reta final! Mantenha a constância para garantir a memorização dos últimos detalhes."
        elif proj['ritmo'] < 1:
            msg = "Atenção: Seu ritmo atual está baixo. Tente zerar ao menos 2-3 novos tópicos por semana para acelerar a conclusão."
        else:
            msg = "Continue assim! O segredo da aprovação é a regularidade. Cada tópico zerado é um passo rumo à vaga."
        pdf.multi_cell(0, 7, f"Insight: {msg}")

    # 5. ASSUNTOS QUE EXIGEM ATENÇÃO (GARGALOS)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '5. ASSUNTOS QUE EXIGEM ATENCÃO (GARGALOS)', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, "Abaixo estão listados os tópicos específicos onde sua precisão está abaixo de 70%. Estes são os seus maiores gargalos e merecem uma revisão teórica antes de novos exercícios.")
    pdf.ln(5)
    
    # Filtrar assuntos críticos (taxa < 70% e total > 0)
    if 'materia' in df_estudos.columns and 'assunto' in df_estudos.columns:
        df_criticos = df_assuntos[(df_assuntos['taxa'] < 70) & (df_assuntos['total'] > 0)].sort_values('taxa')
        
        if not df_criticos.empty:
            materias_criticas = df_criticos['materia'].unique()
            for mat in materias_criticas:
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(139, 92, 246)
                pdf.cell(0, 8, f"  > {mat}", 0, 1)
                
                topicos_da_materia = df_criticos[df_criticos['materia'] == mat]
                pdf.set_font('Arial', '', 9)
                pdf.set_text_color(60, 60, 60)
                for _, row in topicos_da_materia.iterrows():
                    bullet = f"      - {row['assunto']}: {row['taxa']:.0f}% de acerto ({int(row['total'])} questões)"
                    pdf.multi_cell(0, 5, bullet)
                pdf.ln(2)
        else:
            pdf.set_font('Arial', 'I', 10)
            pdf.set_text_color(16, 185, 129)
            pdf.cell(0, 10, "Parabéns! Nenhum tópico específico está com desempenho abaixo de 70%.", 0, 1, 'L')
    else:
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(0, 10, "Dados insuficientes para análise de gargalos.", 0, 1, 'L')

    # 6. BENCHMARK DE SIMULADOS
    # Usar filtro flexível no dataframe bruto para capturar variações (Simulado, SIMULADOS, etc)
    if not df_bruto.empty and 'materia' in df_bruto.columns and 'data_estudo' in df_bruto.columns:
        mask = df_bruto['materia'].str.upper().str.contains('SIMULADO', na=False)
        df_sim = df_bruto[mask].copy()
        
        if not df_sim.empty and 'data_estudo' in df_sim.columns:
            try:
                df_sim = df_sim.sort_values('data_estudo')
            except Exception:
                df_sim = df_sim.copy()
            
            pdf.add_page()
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(0, 10, '6. BENCHMARK DE SIMULADOS (EVOLUÇÃO)', 0, 1, 'L')
            
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, "Acompanhamento cronológico do seu desempenho em provas completas (Simulados).")
            pdf.ln(5)
            
            # Cabeçalho da Tabela
            pdf.set_font('Arial', 'B', 9)
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(139, 92, 246)
            pdf.cell(40, 7, ' Data', 1, 0, 'C', True)
            pdf.cell(100, 7, ' Simulado', 1, 0, 'C', True)
            pdf.cell(40, 7, ' Pontuação (%)', 1, 1, 'C', True)
            
            pdf.set_font('Arial', '', 8)
            pdf.set_text_color(60, 60, 60)
            for _, row in df_sim.iterrows():
                try:
                    data_formatada = pd.to_datetime(row['data_estudo']).strftime('%d/%m/%Y')
                except:
                    data_formatada = str(row['data_estudo'])
                
                pdf.cell(40, 6, data_formatada, 1, 0, 'C')
                assunto = str(row.get('assunto', ''))[:55]
                pdf.cell(100, 6, f" {assunto}", 1, 0, 'L')
                
                taxa = row.get('taxa', 0)
                pdf.cell(40, 6, f"{taxa:.1f}%", 1, 1, 'C')
                
            # Insights de Tendência no PDF
            pdf.ln(5)
            if not df_sim.empty and 'taxa' in df_sim.columns:
                ult_nota = df_sim['taxa'].iloc[-1]
                med_nota = df_sim['taxa'].mean()
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 8, f"Resumo: Última Nota: {ult_nota:.1f}% | Precisão Média: {med_nota:.1f}%", 0, 1)
                
                pdf.set_font('Arial', 'I', 9)
                pdf.set_text_color(100, 100, 100)
                if len(df_sim) >= 2:
                    gap = df_sim['taxa'].iloc[-1] - df_sim['taxa'].iloc[-2]
                    tendencia = "em ascensão" if gap > 0 else "em queda" if gap < 0 else "estabilizado"
                    msg_sim = f"Seu desempenho está {tendencia} em relação ao último simulado ({'+' if gap>0 else ''}{gap:.1f}%)."
                else:
                    msg_sim = "Continue realizando simulados regularmente para consolidar sua curva de aprendizado."
                pdf.multi_cell(0, 6, f"Análise: {msg_sim}")

    return bytes(pdf.output())

def gerar_pdf_carga_horaria(df, missao):
    pdf = EstudoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 1. RESUMO DE CARGA HORÁRIA
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '1. RESUMO DE CARGA HORÁRIA', 0, 1, 'L')
    
    minutos_totais = df['tempo'].sum() if 'tempo' in df.columns else 0
    horas_totais = minutos_totais / 60
    if 'data_estudo' in df.columns and 'tempo' in df.columns:
        dias_estudados = df[df['tempo'] > 0]['data_estudo'].nunique()
    else:
        dias_estudados = 0
    media_diaria = horas_totais / dias_estudados if dias_estudados > 0 else 0
    
    # Grid de métricas
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(248, 248, 255)
    pdf.set_text_color(100, 100, 100)
    
    pdf.cell(63, 8, ' TOTAL DE HORAS', 1, 0, 'L', True)
    pdf.cell(63, 8, ' DIAS ESTUDADOS', 1, 0, 'L', True)
    pdf.cell(64, 8, ' MEDIA DIARIA', 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(63, 10, f' {horas_totais:.1f}h', 1, 0, 'L')
    pdf.cell(63, 10, f' {int(dias_estudados)}', 1, 0, 'L')
    pdf.cell(64, 10, f' {media_diaria:.1f}h/dia', 1, 1, 'L')
    
    pdf.ln(10)
    
    # 2. LOG DE HORAS POR MATÉRIA E ASSUNTO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, '2. DETALHAMENTO DE TEMPO INVESTIDO', 0, 1, 'L')
    pdf.ln(2)
    
    # Lógica de Agrupamento
    if 'materia' in df.columns and 'tempo' in df.columns:
        df_agrup_mat = df.groupby('materia').agg({'tempo': 'sum'}).reset_index()
        df_agrup_ass = df.groupby(['materia', 'assunto']).agg({'tempo': 'sum'}).reset_index()
        
        for _, row_mat in df_agrup_mat.sort_values('tempo', ascending=False).iterrows():
            # Bloco de Título da Matéria
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(139, 92, 246)
            pdf.cell(0, 8, f" {row_mat['materia'].upper()}", 1, 1, 'L', True)
            
            # Total da matéria
            pdf.set_font('Arial', 'I', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"  Carga Horária Total: {row_mat['tempo']/60:.1f}h", 0, 1, 'L')
            
            # Listagem de Assuntos
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(60, 60, 60)
            assuntos_da_materia = df_agrup_ass[df_agrup_ass['materia'] == row_mat['materia']].sort_values('tempo', ascending=False)
            
            for _, row_ass in assuntos_da_materia.iterrows():
                nome_ass = row_ass['assunto']
                if len(nome_ass) > 45: nome_ass = nome_ass[:42] + "..."  # Reduzido para evitar overflow
                
                texto_esq = f"      - {nome_ass}"
                texto_dir = f"{row_ass['tempo']/60:.1f}h"
                
                pdf.cell(160, 6, texto_esq, 0, 0, 'L')
                pdf.cell(0, 6, texto_dir, 0, 1, 'R')
                
            pdf.ln(4)
        
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "Este relatório apresenta a distribuição do seu tempo de estudo por disciplina e tópico. Use-o para avaliar se você está dedicando o tempo adequado às matérias de maior peso ou dificuldade.")

    return bytes(pdf.output())

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
    if 'data_estudo' in df.columns and 'tempo' in df.columns:
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
    else:
        st.info("Dados insuficientes para gerar mapa de calor.")

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
        
        horas_semana = df_semana['tempo'].sum() / 60 if 'tempo' in df_semana.columns else 0
        questoes_semana = df_semana['total'].sum() if 'total' in df_semana.columns else 0
        
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
        estudados = df[df['assunto'].isin(todos_topicos_edital)]['assunto'].nunique() if 'assunto' in df.columns else 0
    
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
    
    # Verificar se a coluna data_estudo existe
    if 'data_estudo' not in df.columns:
        data_inicio = hoje
        dias_totais = 1
    else:
        df['data_estudo_date'] = pd.to_datetime(df['data_estudo']).dt.date
        df_recente = df[df['data_estudo_date'] >= inicio_janela]
        
        if len(df_recente) < 5: # Se tiver pouco dado recente, usa histórico total
            data_inicio = pd.to_datetime(df['data_estudo']).min().date()
            dias_totais = max((hoje - data_inicio).days, 1)
            ritmo_diario = estudados / dias_totais
        else:
            topicos_30d = df_recente['assunto'].nunique() if 'assunto' in df_recente.columns else 0
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
    
    if df_estudos.empty or 'data_estudo' not in df_estudos.columns:
        return pend
        
    for _, row in df_estudos.iterrows():
        try:
            dt_est = pd.to_datetime(row['data_estudo']).date()
        except:
            continue
            
        dias = (hoje - dt_est).days
        tx = row.get('taxa', 0)
        dif = row.get('dificuldade', '🟡 Médio')
        
        # Lógica de Revisão 24h
        if not row.get('rev_24h', False):
            dt_prev = dt_est + timedelta(days=1)
            if dt_prev <= hoje or filtro_rev == "Todas (incluindo futuras)":
                atraso = (hoje - dt_prev).days
                pend.append({
                    "id": row['id'], "materia": row.get('materia', ''), "assunto": row.get('assunto', ''), 
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
                        "id": row['id'], "materia": row.get('materia', ''), "assunto": row.get('assunto', ''), 
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
        data_prova_direta = dados.get('data_prova') if isinstance(dados, dict) else None
    except Exception:
        data_prova_direta = None
        
    # Garantir que 'dados' se refere à missão ativa
    dados_global = dados
    dados = dados_global.get(missao, {}) if isinstance(dados_global, dict) else {}

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
            if isinstance(dados, dict):
                st.markdown(f'<p style="color:#94A3B8; font-size:1rem; margin-bottom:0;">{dados.get("cargo", "")}</p>', unsafe_allow_html=True)
        
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
            
            # Calcular métricas com verificação de colunas
            t_q = df_estudos['total'].sum() if 'total' in df_estudos.columns else 0
            a_q = df_estudos['acertos'].sum() if 'acertos' in df_estudos.columns else 0
            precisao = (a_q / t_q * 100) if t_q > 0 else 0
            minutos_totais = int(df_estudos['tempo'].sum() if 'tempo' in df_estudos.columns else 0)
            
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
            
            # Métricas com ANÉIS CIRCULARES - Layout responsivo (2x2)
            
            # Calcular percentuais para os anéis
            horas_totais = minutos_totais / 60
            meta_horas_mes = 80  # Meta de horas por mês
            pct_tempo = min((horas_totais / meta_horas_mes) * 100, 100)
            pct_precisao = min(precisao, 100)
            meta_questoes_mes = 1000
            pct_questoes = min((t_q / meta_questoes_mes) * 100, 100)
            
            # Linha 1: Tempo e Precisão
            row1_col1, row1_col2 = st.columns(2)
            
            with row1_col1:
                render_circular_progress(
                    percentage=pct_tempo,
                    label="TEMPO TOTAL",
                    value=tempo_formatado,
                    color_start=COLORS["primary"],
                    color_end=COLORS["secondary"],
                    icon="⏱️"
                )
            
            with row1_col2:
                render_circular_progress(
                    percentage=pct_precisao,
                    label="PRECISÃO",
                    value=f"{precisao:.0f}%",
                    color_start=COLORS["success"] if precisao >= 70 else COLORS["warning"],
                    color_end=COLORS["secondary"],
                    icon="🎯"
                )
            
            # Linha 2: Questões e Média
            row2_col1, row2_col2 = st.columns(2)
            
            with row2_col1:
                render_circular_progress(
                    percentage=pct_questoes,
                    label="QUESTÕES",
                    value=f"{int(t_q)}",
                    color_start=COLORS["accent"],
                    color_end=COLORS["primary"],
                    icon="📝"
                )
            
            with row2_col2:
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
                if 'data_estudo' in df_estudos.columns:
                    dias_estudados_mes = len(set(pd.to_datetime(df_estudos['data_estudo']).dt.date.unique()))
                else:
                    dias_estudados_mes = 0
                percentual_mes = (dias_estudados_mes / dias_no_mes) * 100 if dias_no_mes > 0 else 0
                
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
            
            if not df_estudos.empty and 'data_estudo' in df_estudos.columns and 'tempo' in df_estudos.columns:
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
            
            if not df_estudos.empty and 'materia' in df_estudos.columns:
                # Calcular totais por disciplina
                df_disciplinas = df_estudos.groupby('materia').agg({
                    'tempo': 'sum' if 'tempo' in df_estudos.columns else 'materia',
                    'acertos': 'sum' if 'acertos' in df_estudos.columns else 'materia',
                    'total': 'sum' if 'total' in df_estudos.columns else 'materia'
                }).reset_index()
                
                # Recalcular taxa global por disciplina (média ponderada)
                if 'acertos' in df_disciplinas.columns and 'total' in df_disciplinas.columns:
                    df_disciplinas['taxa'] = (df_disciplinas['acertos'] / df_disciplinas['total'] * 100).fillna(0)
                
                df_disciplinas['erros'] = df_disciplinas['total'] - df_disciplinas['acertos'] if 'total' in df_disciplinas.columns and 'acertos' in df_disciplinas.columns else 0
                df_disciplinas['tempo_formatado'] = df_disciplinas['tempo'].apply(formatar_horas_minutos) if 'tempo' in df_disciplinas.columns else "0h00min"
                df_disciplinas['taxa_formatada'] = df_disciplinas['taxa'].round(0).astype(int) if 'taxa' in df_disciplinas.columns else 0
                df_disciplinas = df_disciplinas.sort_values('tempo', ascending=False) if 'tempo' in df_disciplinas.columns else df_disciplinas
                
                # Criar tabela HTML CORRIGIDA - SIMPLIFICADA
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                # Criar DataFrame para display
                display_df = pd.DataFrame({
                    'DISCIPLINAS': df_disciplinas['materia'],
                    'TEMPO': df_disciplinas['tempo_formatado'],
                    '✓': df_disciplinas['acertos'].astype(int) if 'acertos' in df_disciplinas.columns else 0,
                    '✗': df_disciplinas['erros'].astype(int) if 'erros' in df_disciplinas.columns else 0,
                    '🎉': df_disciplinas['total'].astype(int) if 'total' in df_disciplinas.columns else 0,
                    '%': df_disciplinas['taxa_formatada'] if 'taxa_formatada' in df_disciplinas.columns else 0
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
            if 'materia' in df_estudos.columns:
                df_matriz = df_estudos.groupby('materia').agg({
                    'acertos': 'sum' if 'acertos' in df_estudos.columns else 'materia',
                    'total': 'sum' if 'total' in df_estudos.columns else 'materia',
                    'relevancia': 'mean' if 'relevancia' in df_estudos.columns else 'materia'
                }).reset_index()
                
                if 'acertos' in df_matriz.columns and 'total' in df_matriz.columns:
                    df_matriz['taxa'] = (df_matriz['acertos'] / df_matriz['total'] * 100).fillna(0)
                
                # Quadrante: Foco Crítico (Taxa < 75 e Relevância > 5)
                if 'taxa' in df_matriz.columns and 'relevancia' in df_matriz.columns:
                    criticos = df_matriz[(df_matriz['taxa'] < 75) & (df_matriz['relevancia'] >= 5)].sort_values(['relevancia', 'taxa'], ascending=[False, True])
                else:
                    criticos = pd.DataFrame()
            else:
                criticos = pd.DataFrame()
            
            col_rec1, col_rec2 = st.columns([2, 1])
            
            with col_rec1:
                st.markdown("#### 🎯 Alvos Prioritários")
                if criticos.empty:
                    st.success("✨ Sem gargalos críticos no momento! Recomendo avançar em novos tópicos do edital.")
                else:
                    for _, row in criticos.head(3).iterrows():
                        # Buscar o pior assunto desta materia
                        if 'materia' in df_estudos.columns and 'assunto' in df_estudos.columns and 'taxa' in df_estudos.columns:
                            df_ass = df_estudos[df_estudos['materia'] == row['materia']].groupby('assunto').agg({'taxa': 'mean'}).reset_index()
                            pior_ass = df_ass.sort_values('taxa').iloc[0]['assunto'] if not df_ass.empty else "Nenhum assunto específico"
                        else:
                            pior_ass = "Nenhum assunto específico"
                        
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
                
                if not df_raw.empty and 'data_estudo' in df_raw.columns:
                    df_s = df_raw[pd.to_datetime(df_raw['data_estudo']).dt.date >= in_sem] 
                else:
                    df_s = pd.DataFrame()
                    
                if not df_estudos.empty and 'data_estudo' in df_estudos.columns:
                    df_e = df_estudos[pd.to_datetime(df_estudos['data_estudo']).dt.date >= in_sem]
                else:
                    df_e = pd.DataFrame()
                    
                if not df_simulados.empty and 'data_estudo' in df_simulados.columns:
                    df_sim_s = df_simulados[pd.to_datetime(df_simulados['data_estudo']).dt.date >= in_sem]
                else:
                    df_sim_s = pd.DataFrame()
                
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
                st_auto["Manter meta de questões diária"] = df_s['total'].sum() >= st.session_state.get('meta_questoes_semana', 350) if not df_s.empty and 'total' in df_s.columns else False
                st_auto["Zerar 2 novos tópicos do edital"] = len(df_e['assunto'].unique()) >= 2 if not df_e.empty and 'assunto' in df_e.columns else False

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
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                    with col1:
                        acertos = st.number_input("✅ Acertos", min_value=0, key=f"ac_{p['id']}_{p['col']}")

                    with col2:
                        total = st.number_input("📝 Total", min_value=0, key=f"to_{p['id']}_{p['col']}")

                    with col3:
                        tempo_rev = st.number_input("⏱️ Tempo (min)", min_value=0, step=5, key=f"tm_{p['id']}_{p['col']}")

                    with col4:
                        st.write("")  # Espaçamento
                        st.write("")  # Mais espaçamento
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
        
        # Obter matérias do edital
        if isinstance(dados, dict) and 'materias' in dados:
            mats = list(dados['materias'].keys())
        else:
            mats = []
        
        if not mats:
            st.warning("⚠️ Nenhuma matéria cadastrada. Vá em 'Configurar' para adicionar disciplinas.")
        else:
            with st.container():
                st.markdown('<div class="modern-card">', unsafe_allow_html=True)
                
                c1, c2 = st.columns([2, 1])
                dt_reg = c1.date_input("Data do Estudo", value=get_br_date(), format="DD/MM/YYYY")
                tm_reg = c2.text_input("Tempo (HHMM)", value="0100", help="Ex: 0130 para 1h30min")
                
                mat_reg = st.selectbox("Disciplina", mats)
                
                # Obter assuntos da matéria selecionada
                if isinstance(dados, dict) and 'materias' in dados and mat_reg in dados['materias']:
                    assuntos_disponiveis = dados['materias'][mat_reg]
                else:
                    assuntos_disponiveis = ["Geral"]
                    
                ass_reg = st.selectbox("Assunto", assuntos_disponiveis, key=f"assunto_select_{mat_reg}")
                
                st.div
