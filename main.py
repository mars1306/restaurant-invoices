"""
Entry point for the Restaurant Invoices Streamlit application.
Run with: streamlit run main.py
"""
import os
import sys

# Ensure the project root is on sys.path so `app.*` imports work
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from app.ui.login import render_login_page, logout
from app.ui.style import inject

# ---- Page config (must be first Streamlit call) ----
st.set_page_config(
    page_title="Factures — Brasserie",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()

# Initialize session state for user
if "user" not in st.session_state:
    st.session_state.user = None

# Show login page if not authenticated
if st.session_state.user is None:
    render_login_page()
    st.stop()

from app.database.models import init_db
from app.utils.logger import get_logger

logger = get_logger("main")

# Initialize DB on startup (idempotent)
init_db()

# ---- Sidebar navigation ----
PAGES = {
    "Upload": "upload",
    "Tableau de bord": "dashboard",
    "Factures": "invoices",
    "Comparaisons": "comparisons",
    "Analyse Produits": "products",
    "Paramètres": "settings",
}

with st.sidebar:
    st.title("Factures Fournisseurs")
    
    # Display current date context
    from datetime import date
    st.info(f"📅 Aujourd'hui : {date.today().strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    selected_page = st.radio(
        "Navigation",
        list(PAGES.keys()),
        key="nav_page",
    )
    
    st.markdown("---")
    # Mobile optimization toggle
    use_mobile = st.checkbox("Optimisation Mobile 📱", value=False)
    if use_mobile:
        st.session_state.mobile_mode = True
    else:
        st.session_state.mobile_mode = False
        
    st.markdown("---")
    if st.session_state.user:
        st.write(f"Connecté : {st.session_state.user.email}")
    if st.button("Se déconnecter"):
        logout()
    st.caption("Powered by Claude Vision")

# ---- Page routing ----
page_key = PAGES[selected_page]

if page_key == "upload":
    from app.ui.upload import render
    render()

elif page_key == "dashboard":
    from app.ui.dashboard import render
    render()

elif page_key == "invoices":
    from app.ui.invoices import render
    render()

elif page_key == "comparisons":
    from app.ui.comparisons import render
    render()

elif page_key == "products":
    from app.ui.products import render
    render()

elif page_key == "settings":
    from app.ui.settings import render
    render()
