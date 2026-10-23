"""RailInsight — Streamlit entry point.

Responsibilities (and only these):
  1. st.set_page_config — must be the very first Streamlit call.
  2. Initialise logging and the Plotly template (both idempotent).
  3. Build the page registry and hand off to st.navigation.

Business logic and data loading belong in src/railinsight/, not here.
"""

import streamlit as st

from railinsight.logging_config import setup_logging
from railinsight.ui.theme.plotly_template import register_template

st.set_page_config(
    page_title="RailInsight",
    page_icon="",
    layout="wide",
    menu_items={
        "About": (
            "RailInsight — Analyse de la fiabilité des TGV SNCF. Projet Télécom Paris."
        ),
    },
)

setup_logging()
register_template()

# --- Page registry (ordered by question number) ----------------------------
# Add a new st.Page here when a team member delivers their page.
# The path is relative to the project root. The title is what appears in the
# sidebar. icon= accepts any :material/icon_name: from Material Symbols.

pages = [
    st.Page(
        "src/railinsight/ui/pages/home.py",
        title="Accueil",
        icon=":material/home:",
        default=True,
    ),
    st.Page(
        "src/railinsight/ui/pages/template_page.py",
        title="Page modèle",
        icon=":material/draft:",
    ),
    # Q1 — Michelle
    # st.Page(
    #     "src/railinsight/ui/pages/q1_unreliable_routes.py",
    #     title="Q1 — Liaisons peu fiables",
    #     icon=":material/trending_down:",
    # ),
    # Q2 — Éric
    # st.Page(
    #     "src/railinsight/ui/pages/q2_departure_stations.py",
    #     title="Q2 — Gares responsables",
    #     icon=":material/alt_route:",
    # ),
    # Q3 — Bachelard (décommenter quand prêt)
    # st.Page(
    #     "src/railinsight/ui/pages/q3_narrative.py",
    #     title="Q3 — Profils de ponctualité",
    #     icon=":material/scatter_plot:",
    # ),
    # st.Page(
    #     "src/railinsight/ui/pages/q3_lab.py",
    #     title="Q3 — Laboratoire",
    #     icon=":material/science:",
    # ),
    # Q4 — Meryem
    # st.Page(
    #     "src/railinsight/ui/pages/q4_reliability_map.py",
    #     title="Q4 — Carte de fiabilité",
    #     icon=":material/map:",
    # ),
]

pg = st.navigation(pages)
pg.run()
