"""Standardized chart wrapper: title, Plotly figure, reading guide, caption.

Usage:
    import plotly.express as px
    fig = px.scatter(df, x="x", y="y")
    chart_container(fig, "Mon graphique", how_to_read="Chaque point est une liaison.")
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


def chart_container(
    fig: go.Figure,
    title: str,
    how_to_read: str | None = None,
    caption: str | None = None,
    use_container_width: bool = True,
) -> None:
    """Render a Plotly figure with a standard header and optional reading guide.

    Every chart in the app should go through this wrapper so that:
    - Titles follow the same typographic hierarchy.
    - "Comment lire ce graphique" is always available when provided.
    - Source captions are consistent.

    Args:
        fig: A Plotly figure object (go.Figure or any px.* output).
        title: Short chart title phrased as a finding, not a description.
            Good: "Les liaisons longues sont plus souvent en retard".
            Avoid: "Graphique de corrélation durée / retard".
        how_to_read: Optional plain-French explanation of how to read the chart.
            Shown in a collapsed expander below the figure.
        caption: Optional footnote (e.g., "Hors mois exceptionnels.").
        use_container_width: Whether to stretch the chart to full width.
    """
    st.markdown(f"**{title}**")
    st.plotly_chart(fig, use_container_width=use_container_width)

    if how_to_read:
        with st.expander("Comment lire ce graphique ?", expanded=False):
            st.markdown(how_to_read)

    if caption:
        st.caption(caption)
