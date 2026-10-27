"""SNCF-branded global CSS injection for the RailInsight Streamlit app.

Call inject_global_css() once per page render (in app.py, before pg.run()).
Call sidebar_brand() in app.py to add the branded header to the sidebar.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# CSS design system
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* === 1. Typography — Inter via Google Fonts === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'Segoe UI', sans-serif !important;
}

/* === 2. Sidebar — dark SNCF navy === */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1A2E 0%, #0D1421 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
}
/* Sidebar text */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] label {
    color: #CBD5E0 !important;
}
/* Nav links */
[data-testid="stSidebarNav"] ul { padding: 4px 8px; }
[data-testid="stSidebarNav"] a {
    color: #A0AEC0 !important;
    border-radius: 6px !important;
    padding: 9px 14px !important;
    margin: 2px 0 !important;
    display: flex !important;
    align-items: center !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255,255,255,0.07) !important;
    color: white !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(232,0,61,0.18) !important;
    color: white !important;
    border-left: 3px solid #E8003D !important;
    border-radius: 0 6px 6px 0 !important;
    font-weight: 600 !important;
    padding-left: 11px !important;
}

/* === 3. Hide Streamlit chrome === */
#MainMenu          { visibility: hidden !important; height: 0 !important; }
footer             { visibility: hidden !important; height: 0 !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"]     { background: transparent !important; }
[data-testid="stToolbar"]    { visibility: hidden !important; }

/* === 4. Main content container === */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1200px !important;
}

/* === 5. Primary buttons — SNCF red === */
.stButton > button[kind="primary"] {
    background: #E8003D !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.01em !important;
    padding: 10px 24px !important;
    transition: all 0.18s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: #C4002E !important;
    box-shadow: 0 4px 16px rgba(232,0,61,0.35) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}
/* Secondary / tertiary buttons */
.stButton > button:not([kind="primary"]) {
    border-radius: 6px !important;
    border: 1.5px solid #E8ECEF !important;
    background: white !important;
    font-size: 0.88rem !important;
    transition: border-color 0.15s ease, color 0.15s ease !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #E8003D !important;
    color: #E8003D !important;
}

/* === 6. Form — card-like container === */
[data-testid="stForm"] {
    border: 1px solid #E8ECEF !important;
    border-radius: 12px !important;
    padding: 24px !important;
    background: #FAFBFC !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
}

/* === 7. Expanders === */
[data-testid="stExpander"] {
    border: 1px solid #E8ECEF !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    margin-bottom: 4px !important;
}
[data-testid="stExpander"] summary {
    padding: 12px 16px !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}
[data-testid="stExpander"] summary:hover {
    background: #F5F7FA !important;
}

/* === 8. Tabs === */
[data-testid="stTabs"] [role="tab"] {
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    transition: color 0.15s ease !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #E8003D !important;
    border-bottom-color: #E8003D !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid #E8ECEF !important;
}

/* === 9. Dividers === */
hr {
    border: none !important;
    border-top: 1px solid #E8ECEF !important;
    margin: 24px 0 !important;
}

/* === 10. Selectbox / inputs === */
[data-baseweb="select"] > div:first-child {
    border-radius: 6px !important;
    border-color: #E8ECEF !important;
    font-size: 0.9rem !important;
}
[data-baseweb="select"] > div:first-child:focus-within {
    border-color: #E8003D !important;
    box-shadow: 0 0 0 2px rgba(232,0,61,0.15) !important;
}
[data-baseweb="input"] input {
    border-radius: 6px !important;
    border-color: #E8ECEF !important;
    font-size: 0.9rem !important;
}

/* === 11. DataFrame === */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid #E8ECEF !important;
}

/* === 12. Notification boxes === */
[data-testid="stNotification"] {
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}

/* === 13. Scrollbar (Webkit) === */
::-webkit-scrollbar          { width: 6px; height: 6px; }
::-webkit-scrollbar-track    { background: #F5F7FA; }
::-webkit-scrollbar-thumb    { background: #CBD5E0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9BA3AE; }

/* === 14. KPI cards (custom HTML component) === */
.ri-kpi-card {
    background: white;
    border-radius: 10px;
    padding: 20px 16px 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    text-align: center;
    height: 100%;
    min-height: 96px;
    transition: box-shadow 0.2s ease;
}
.ri-kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.11); }
.ri-kpi-label {
    font-size: 0.7rem;
    color: #4A5568;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
}
.ri-kpi-value {
    font-size: 1.95rem;
    font-weight: 800;
    color: #1A1A2E;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.ri-kpi-delta {
    font-size: 0.78rem;
    font-weight: 600;
    margin-top: 6px;
}

/* === 15. Question cards (home page) === */
.ri-question-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 16px;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    cursor: default;
}
.ri-question-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.10);
}
.ri-question-number {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}
.ri-question-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1A1A2E;
    margin-bottom: 6px;
}
.ri-question-desc {
    font-size: 0.85rem;
    color: #4A5568;
    line-height: 1.55;
    margin-bottom: 10px;
}
.ri-question-author {
    font-size: 0.72rem;
    color: #9BA3AE;
    font-weight: 500;
}
</style>
"""

_SIDEBAR_BRAND_HTML = """
<div style="
    padding: 24px 16px 20px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 8px;
">
    <div style="font-size:1.6rem;margin-bottom:6px;">🚄</div>
    <div style="
        font-size: 1.1rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.02em;
    ">RailInsight</div>
    <div style="
        font-size: 0.68rem;
        color: #718096;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    ">Télécom Paris · SNCF Open Data</div>
</div>
"""


def inject_global_css() -> None:
    """Inject the RailInsight SNCF-branded CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    """Render the RailInsight brand header at the top of the sidebar."""
    st.sidebar.markdown(_SIDEBAR_BRAND_HTML, unsafe_allow_html=True)
