import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0A0A0B; color: #E2E8F0; }
        .rev-card { background: #17171B; border: 1px solid #2D2D35; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #333; }
        .perf-bad { border-left-color: #EF4444; }
        .perf-med { border-left-color: #F59E0B; }
        .perf-good { border-left-color: #10B981; }
        .score-badge { background: #2D2D35; color: #FFF; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
        .stButton button { background: #1E1E24; border: 1px solid #3F3F46; border-radius: 6px; font-weight: 600; width: 100%; transition: 0.3s; }
        .stButton button:hover { background: #DC2626; border-color: #DC2626; color: white; }
    </style>
    """, unsafe_allow_html=True)
