"""Home page: hero banner, network KPIs and question navigation cards.

This file is run as a script by Streamlit (via st.Page in app.py).
"""

from __future__ import annotations

import logging

import streamlit as st

from railinsight.interfaces.data_protocols import DataProvider
from railinsight.ui.components.kpi_card import kpi_row
from railinsight.ui.providers import get_provider
from railinsight.ui.theme.css import inject_global_css
from railinsight.ui.theme.tokens import QUESTION_COLORS
from railinsight.utils.formatting import fmt_pct

logger = logging.getLogger(__name__)

# Questions catalogue — all values hardcoded, no user input injected here.
# page_path: relative path as declared in app.py st.Page(), or None if not yet built.
_QUESTIONS = [
    (
        1,
        "Liaisons les moins fiables",
        "Quelles liaisons sont chroniquement en retard, et ça s'aggrave-t-il ?",
        "Michelle",
        None,
    ),
    (
        2,
        "Gares responsables vs victimes",
        "Quelles gares concentrent les retards ? Qui subit les cascades ?",
        "Éric",
        None,
    ),
    (
        3,
        "Profils de ponctualité",
        "Peut-on regrouper les liaisons par profil de régularité via clustering ?",
        "Bachelard",
        "src/railinsight/ui/pages/q3_narrative.py",
    ),
    (
        4,
        "Score de fiabilité",
        "Score par liaison (annulations + retards) représenté sur la carte réseau.",
        "Meryem",
        None,
    ),
]


def render(provider: DataProvider) -> None:
    """Render the RailInsight home page.

    Args:
        provider: Data provider used to load network KPIs.
    """
    inject_global_css()
    _render_hero()
    _render_network_kpis(provider)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_question_cards()
    _render_about(provider)


def _render_hero() -> None:
    """Render the SNCF-branded hero banner."""
    st.markdown(
        '<div style="'
        "background:linear-gradient(135deg,#1A1A2E 0%,#16213E 45%,#E8003D 100%);"
        "color:white;"
        "padding:48px 40px 44px;"
        "border-radius:16px;"
        "margin-bottom:32px;"
        '">'
        '<div style="font-size:0.72rem;font-weight:700;opacity:0.6;'
        "letter-spacing:0.12em;text-transform:uppercase;"
        'margin-bottom:14px;">Télécom Paris · SNCF Open Data</div>'
        '<h1 style="margin:0;font-size:2.6rem;font-weight:800;'
        'letter-spacing:-0.03em;line-height:1.1;">🚄 RailInsight</h1>'
        '<p style="margin:14px 0 0;font-size:1.05rem;opacity:0.85;'
        "max-width:580px;line-height:1.6;"
        '">'
        "Exploration interactive de la régularité du réseau TGV français. "
        "Analyses statistiques, visualisations et insights chiffrés "
        "sur les données ouvertes de la SNCF."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_network_kpis(provider: DataProvider) -> None:
    """Render 3 network-level KPI cards (last 12 months)."""
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;color:#9BA3AE;'
        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px;">'
        "Réseau TGV — 12 derniers mois</p>",
        unsafe_allow_html=True,
    )
    try:
        network = provider.load_network_monthly()
        monthly = provider.load_clean_monthly()
        recent = network.tail(12)
        n_routes = monthly["route"].nunique()
        avg_late15 = recent["late15_rate"].mean()
        avg_cancel = recent["cancellation_rate"].mean()
        kpi_row(
            [
                {"label": "Liaisons analysées", "value": str(n_routes)},
                {
                    "label": "Retards > 15 min",
                    "value": fmt_pct(avg_late15),
                    "help": "Moyenne sur les 12 derniers mois.",
                },
                {
                    "label": "Annulations",
                    "value": fmt_pct(avg_cancel),
                    "help": "Moyenne sur les 12 derniers mois.",
                },
            ]
        )
    except Exception:
        logger.exception("Could not load network KPIs for home page")
        st.info("Indicateurs réseau temporairement indisponibles.")


def _render_question_cards() -> None:
    """Render the four question navigation cards with optional page links."""
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;color:#9BA3AE;'
        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:16px;">'
        "Les quatre questions de l'équipe</p>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns(2, gap="medium")
    columns = [left_col, right_col]

    for i, (num, title, description, author, page_path) in enumerate(_QUESTIONS):
        color = QUESTION_COLORS[num]
        with columns[i % 2]:
            st.markdown(
                f'<div style="'
                f"background:white;"
                f"border-radius:12px;"
                f"padding:20px;"
                f"box-shadow:0 2px 8px rgba(0,0,0,0.07);"
                f"margin-bottom:4px;"
                f'border-top:4px solid {color};">'
                f'<div style="font-size:0.68rem;font-weight:700;'
                f"color:{color};text-transform:uppercase;"
                f'letter-spacing:0.1em;margin-bottom:6px;">Q{num}</div>'
                f'<div style="font-size:1rem;font-weight:700;'
                f'color:#1A1A2E;margin-bottom:6px;">{title}</div>'
                f'<div style="font-size:0.85rem;color:#4A5568;'
                f'line-height:1.55;margin-bottom:10px;">{description}</div>'
                f'<div style="font-size:0.72rem;color:#9BA3AE;'
                f'font-weight:500;">Auteur·e : {author}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            if page_path:
                st.page_link(
                    page_path,
                    label="Voir l'analyse →",
                    icon=":material/arrow_forward:",
                )
            else:
                st.caption("En cours de développement")


def _render_about(provider: DataProvider) -> None:
    """Render the data quality and methodology expander."""
    st.markdown("<br>", unsafe_allow_html=True)
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
    st.markdown(
        '<div style="text-align:center;margin-top:40px;">'
        '<span style="font-size:0.7rem;color:#CBD5E0;">'
        "Source : SNCF Open Data — Régularité mensuelle TGV (AQST)"
        "</span></div>",
        unsafe_allow_html=True,
    )


# Script entry point — executed by Streamlit when this file is a st.Page target.
render(get_provider())
