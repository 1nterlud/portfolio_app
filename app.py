"""
Portfolio Pro — entry point.
Routes between Portfolio Dashboard, Stock Research, Compare and Watchlist.
All business logic lives in analytics/, data/, utils/.
All rendering lives in ui/.
"""
import os
import streamlit as st
from config import APP_NAME, __version__

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — robust to working dir (Streamlit Cloud, local, etc.)
_CSS_PATHS = [
    "assets/style.css",
    os.path.join(os.path.dirname(__file__), "assets", "style.css"),
]
for _p in _CSS_PATHS:
    try:
        with open(_p) as fh:
            st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)
        break
    except FileNotFoundError:
        continue

from ui.sidebar import render_sidebar
from ui.portfolio_dashboard import render_portfolio_dashboard
from ui.stock_research import render_stock_research
from ui.compare import render_compare
from ui.watchlist import render_watchlist
from ui.macro_page import render_macro

# ── Navigation ────────────────────────────────────────────────────────────────
inputs = render_sidebar()
page   = inputs.get("page", "portfolio")

if page == "stock":
    render_stock_research(
        ticker=inputs.get("ticker", "AAPL"),
        analyze=inputs.get("analyze_btn", False),
    )
elif page == "compare":
    render_compare(inputs)
elif page == "watchlist":
    render_watchlist(inputs)
elif page == "macro":
    render_macro(inputs)
else:
    render_portfolio_dashboard(inputs)
