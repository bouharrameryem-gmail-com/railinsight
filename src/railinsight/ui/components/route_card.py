"""Route info card: displays a summary profile for a single TGV route.

Usage:
    route_card(
        route="PARIS GARE DE LYON → MARSEILLE ST CHARLES",
        indicators={
            "Retards > 15 min": "27,3 %",
            "Sévérité": "Élevée",
            "Durée": "3 h 20",
        },
        cluster_name="Liaisons longues chroniques",
        color="#6A0572",
    )
"""

from __future__ import annotations

import streamlit as st

from railinsight.ui.theme.tokens import SNCF_RED


def route_card(
    route: str,
    indicators: dict[str, str],
    cluster_name: str | None = None,
    color: str = SNCF_RED,
) -> None:
    """Render a profile card for a single route.

    Args:
        route: Route label (e.g., "PARIS LYON → MARSEILLE ST CHARLES").
        indicators: Ordered dict of label → formatted value pairs to display.
            Use fmt_pct / fmt_number for consistent formatting.
        cluster_name: Optional cluster or profile name this route belongs to.
        color: Accent color for the left border. Defaults to SNCF red.
            Use QUESTION_COLORS[3] for Q3, or CLUSTER_COLORS[i] for clusters.
    """
    departure, _, arrival = route.partition(" → ")

    # All values are developer-supplied (not user input) — safe to inject.
    header_html = (
        f'<div style="border-left:4px solid {color};padding:10px 14px;'
        f"background:#F5F7FA;border-radius:4px;margin-bottom:8px;"
        f'">'
        f'<strong style="color:{color};">{departure}</strong>'
        f'<span style="color:#9BA3AE;"> → </span>'
        f'<strong style="color:{color};">{arrival}</strong>'
    )
    if cluster_name:
        header_html += (
            f'<br><em style="font-size:0.85em;color:#4A5568;">{cluster_name}</em>'
        )
    header_html += "</div>"

    st.markdown(header_html, unsafe_allow_html=True)

    if indicators:
        cols = st.columns(len(indicators))
        for col, (label, value) in zip(cols, indicators.items(), strict=False):
            col.metric(label, value)
