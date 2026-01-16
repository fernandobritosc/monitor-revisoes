# No topo do arquivo
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ... dentro do código
conn = st.connection("gsheets", type=GSheetsConnection)
