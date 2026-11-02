"""Affichage commun des graphiques Plotly avec titre et aide à la lecture."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


def chart_container(
    fig: go.Figure,
    title: str,
    how_to_read: str | None = None,
    caption: str | None = None,
    use_container_width: bool = True,
    key: str | None = None,
) -> None:
    """Affiche le graphique, une aide repliable et une légende facultatives.

    `key` distingue deux graphiques identiques ; `use_container_width` étire
    le graphique sur toute la largeur disponible.
    """
    st.markdown(f"**{title}**")
    st.plotly_chart(fig, width="stretch" if use_container_width else "content", key=key)

    if how_to_read:
        with st.expander("Comment lire ce graphique ?", expanded=False):
            st.markdown(how_to_read)

    if caption:
        st.caption(caption)
