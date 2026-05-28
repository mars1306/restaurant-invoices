"""
Brasserie Moderne — global CSS injection.
Call inject() once at app startup, right after st.set_page_config().
"""
import streamlit as st


def inject() -> None:
    st.markdown(
        """
        <style>
        /* ── Google Fonts ─────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:wght@400;500&display=swap');

        /* ── Base body ────────────────────────────────────────── */
        .stApp, .stApp * {
            font-family: 'DM Sans', sans-serif;
        }

        /* ── Headings ─────────────────────────────────────────── */
        h1, h2, h3 {
            font-family: 'Cormorant Garamond', serif !important;
            letter-spacing: 0.05em;
        }

        h1 {
            font-size: 2rem !important;
            color: #c9a84c !important;
            border-bottom: 1px solid #2a2722;
            padding-bottom: 0.5rem;
        }

        h2 {
            font-size: 1.3rem !important;
            color: #f0ede6 !important;
        }

        /* ── Metrics ──────────────────────────────────────────── */
        div[data-testid="stMetric"] {
            background: #1a1916;
            border: 1px solid #2a2722;
            border-left: 3px solid #c9a84c;
            border-radius: 8px;
            padding: 1rem;
        }

        div[data-testid="stMetricLabel"] {
            color: #6b6560 !important;
            font-size: 0.75rem !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        div[data-testid="stMetricValue"] {
            color: #f0ede6 !important;
            font-size: 1.6rem !important;
            font-family: 'Cormorant Garamond', serif !important;
        }

        /* ── Buttons — primary ────────────────────────────────── */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
            background: #c9a84c !important;
            color: #0e0e0e !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 4px !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {
            background: #b8943d !important;
        }

        /* ── Buttons — secondary ──────────────────────────────── */
        .stButton > button[kind="secondary"],
        .stButton > button[data-testid="baseButton-secondary"] {
            background: transparent !important;
            color: #c9a84c !important;
            border: 1px solid #c9a84c !important;
        }

        /* ── Expander ─────────────────────────────────────────── */
        .stExpander {
            border: 1px solid #2a2722 !important;
            border-radius: 6px !important;
            background: #1a1916 !important;
        }

        /* ── DataFrame ────────────────────────────────────────── */
        .stDataFrame {
            border: 1px solid #2a2722 !important;
        }

        /* ── Alerts ───────────────────────────────────────────── */
        div[data-testid="stAlert"][data-alert-type="info"],
        .stAlert[kind="info"] {
            border-left: 3px solid #c9a84c !important;
            background: #1a1916 !important;
        }

        div[data-testid="stAlert"][data-alert-type="success"],
        .stAlert[kind="success"] {
            border-left: 3px solid #4caf50 !important;
            background: #111f13 !important;
        }

        div[data-testid="stAlert"][data-alert-type="warning"],
        .stAlert[kind="warning"] {
            border-left: 3px solid #e8a338 !important;
            background: #1f1a10 !important;
        }

        div[data-testid="stAlert"][data-alert-type="error"],
        .stAlert[kind="error"] {
            border-left: 3px solid #e05252 !important;
            background: #1f1010 !important;
        }

        /* ── Sidebar ──────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: #0a0a08 !important;
            border-right: 1px solid #2a2722 !important;
        }

        [data-testid="stSidebar"] .stRadio label:hover,
        [data-testid="stSidebar"] a:hover {
            color: #c9a84c !important;
        }

        /* ── Dividers / HR ────────────────────────────────────── */
        hr, .stDivider {
            border-color: #2a2722 !important;
        }

        /* ── File uploader ────────────────────────────────────── */
        [data-testid="stFileUploader"] {
            border: 2px dashed #2a2722 !important;
            background: #1a1916 !important;
            border-radius: 8px !important;
        }

        [data-testid="stFileUploader"]:hover {
            border-color: #c9a84c !important;
        }

        /* ── Inputs — selectbox / text / number ───────────────── */
        .stSelectbox > div > div,
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            background: #1a1916 !important;
            border: 1px solid #2a2722 !important;
            color: #f0ede6 !important;
            border-radius: 4px !important;
        }

        .stSelectbox > div > div:focus-within,
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus {
            border-color: #c9a84c !important;
            outline: none !important;
            box-shadow: none !important;
        }

        /* ── Top header bar ───────────────────────────────────── */
        header[data-testid="stHeader"] {
            background: #0a0a08 !important;
            border-bottom: 1px solid #2a2722 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
