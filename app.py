"""
Portfolio Pro — entry point.
Routes between Portfolio Dashboard and Stock Research based on sidebar selection.
All business logic lives in analytics/, data/, utils/.
All rendering lives in ui/.
"""
import streamlit as st

st.set_page_config(
    page_title="Portfolio Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
try:
    with open("assets/style.css") as fh:
        st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

from ui.sidebar import render_sidebar
from ui.portfolio_dashboard import render_portfolio_dashboard
from ui.stock_research import render_stock_research

# ── Navigation ────────────────────────────────────────────────────────────────
inputs = render_sidebar()

if inputs["page"] == "stock":
    render_stock_research(
        ticker=inputs.get("ticker", "AAPL"),
        analyze=inputs.get("analyze_btn", False),
    )
else:
    render_portfolio_dashboard(inputs)
