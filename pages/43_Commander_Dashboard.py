from __future__ import annotations

import streamlit as st

from src.commander.console_page import render_console


st.set_page_config(page_title="AIOS Commander", page_icon="Commander", layout="wide")
render_console()
