from __future__ import annotations

import streamlit as st
from src.ui import apply_design_system, business_home_link

from src.commander.console_page import render_console
from src.ui.revenue1_readiness import render_commander_readiness
from src.ui.revenue2_first_customer import render_commander as render_revenue2_commander
from src.ui.revenue3_customer_package import render_commander_package
from src.ui.revenue4_onboarding import render_commander as render_revenue4_commander
from src.ui.revenue5_owner_approval import render_commander as render_revenue5_commander
from src.ui.revenue6_controlled_intake import render_commander as render_revenue6_commander
from src.ui.revenue7_operation_simulation import render_commander as render_revenue7_commander
from src.ui.revenue8_first_offer import render_commander as render_revenue8_commander
from src.ui.revenue9_owner_decision import render_commander as render_revenue9_commander


st.set_page_config(page_title="AIOS Commander Console", page_icon="Commander", layout="wide")
apply_design_system()
business_home_link()
render_console()
with st.expander("事業・収益ステータス詳細", expanded=False):
    render_commander_readiness()
    render_revenue2_commander()
    render_commander_package()
    render_revenue4_commander()
    render_revenue5_commander()
    render_revenue6_commander()
    render_revenue7_commander()
    render_revenue8_commander()
    render_revenue9_commander()
