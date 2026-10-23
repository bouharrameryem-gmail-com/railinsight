"""Methodology and limits expander.

Usage:
    method_box(
        content=\"\"\"
        **Méthode :** ratio de sommes sur les mois valides (WIKI §5.2).
        **Limites :** hors liaisons < 24 mois de données.
        \"\"\",
    )
"""

from __future__ import annotations

import streamlit as st


def method_box(
    content: str,
    title: str = "Méthode et limites",
    expanded: bool = False,
) -> None:
    """Render a collapsible methodology and limits box.

    Always place this at the bottom of an analysis section, before the sources
    footer. Write in plain French accessible to a non-expert reader.

    Args:
        content: Markdown-formatted text. Use **Méthode :** and **Limites :**
            as sub-headings. Keep it under 10 lines.
        title: Expander title. Defaults to "Méthode et limites".
        expanded: Whether the expander starts open. Defaults to False.
    """
    with st.expander(title, expanded=expanded):
        st.markdown(content)
