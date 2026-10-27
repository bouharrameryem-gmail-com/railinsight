"""Home page: project overview, network KPIs, navigation cards to each question.

This file is run as a script by Streamlit (via st.Page in app.py).
It imports the provider from providers.py and calls render().
"""

from __future__ import annotations

import logging

import streamlit as st

from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.providers import get_provider
from railinsight.ui.theme.tokens import QUESTION_COLORS
from railinsight.utils.formatting import fmt_pct

logger = logging.getLogger(__name__)


def render(provider: DataProvider) -> None:
    """Render the RailInsight home page.

    Args:
        provider: Data provider used to load network KPIs.
    """
    st.title("RailInsight")
    st.subheader("La fiabilité du réseau TGV en chiffres")
    st.caption("Source : SNCF Open Data — Régularité mensuelle TGV (AQST)")
    st.divider()

    _render_network_kpis(provider)
    st.divider()
    _render_question_cards()
    st.divider()
    _render_about(provider)


def _render_network_kpis(provider: DataProvider) -> None:
    """Render 3 network-level KPI cards (last 12 months)."""
    st.markdown("#### Réseau TGV — chiffres clés (12 derniers mois)")
    try:
        network = provider.load_network_monthly()
        monthly = provider.load_clean_monthly()
        recent = network.tail(12)
        n_routes = monthly["route"].nunique()
        avg_late15 = recent["late15_rate"].mean()
        avg_cancel = recent["cancellation_rate"].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Liaisons analysées", str(n_routes))
        c2.metric(
            "Retards > 15 min",
            fmt_pct(avg_late15),
            help="Moyenne pondérée sur les 12 derniers mois.",
        )
        c3.metric(
            "Annulations",
            fmt_pct(avg_cancel),
            help="Moyenne pondérée sur les 12 derniers mois.",
        )
    except Exception:
        logger.exception("Could not load network KPIs for home page")
        st.info("Indicateurs réseau temporairement indisponibles.")


def _render_question_cards() -> None:
    """Render the four question navigation cards."""
    st.markdown("#### Les quatre questions de l'équipe")

    questions = [
        (
            1,
            "Liaisons les moins fiables",
            "Quelles liaisons sont chroniquement en retard, et ça s'aggrave ?",
            "Michelle",
        ),
        (
            2,
            "Gares responsables vs victimes",
            "Quelles gares concentrent les retards vs. gares victimes de cascade ?",
            "Éric",
        ),
        (
            3,
            "Profils de ponctualité",
            "Peut-on regrouper les liaisons par profil de régularité (clustering) ?",
            "Bachelard",
        ),
        (
            4,
            "Score de fiabilité",
            "Score par liaison (annulations + retards) représenté sur la carte réseau.",
            "Meryem",
        ),
    ]

    left_col, right_col = st.columns(2)
    columns = [left_col, right_col]

    for i, (num, title, description, author) in enumerate(questions):
        color = QUESTION_COLORS[num]
        # All values are hardcoded — no user input injected here.
        with columns[i % 2]:
            st.markdown(
                f'<div style="border-left:4px solid {color};padding:12px 16px;'
                f'margin-bottom:12px;background:#F5F7FA;border-radius:4px;">'
                f'<strong style="color:{color};">Q{num} — {title}</strong><br>'
                f'<span style="font-size:0.9em;">{description}</span><br>'
                f'<em style="font-size:0.8em;color:#9BA3AE;">Auteur·e : {author}</em>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_about(provider: DataProvider) -> None:
    """Render the data quality and methodology expander."""
    with st.expander("Qualité des données et méthodologie", expanded=False):
        st.markdown(
            "Les données proviennent du jeu open data SNCF "
            "*Régularité mensuelle TGV (AQST)*, mis à jour mensuellement. "
            "Pour les détails sur les anomalies détectées et les corrections "
            "appliquées, consultez le rapport qualité ci-dessous."
        )
        try:
            report = provider.load_quality_report()
            st.json(report)
        except Exception:
            logger.exception("Could not load quality report for home page")
            st.caption("Rapport qualité non disponible.")


# Script entry point — executed by Streamlit when this file is a st.Page target.
render(get_provider())
