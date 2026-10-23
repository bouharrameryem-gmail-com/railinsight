"""Highlighted "À retenir" takeaway box.

Usage:
    insight_box("Les 5 liaisons les moins fiables concentrent 40 % des retards.")
"""

from __future__ import annotations

import streamlit as st


def insight_box(text: str, title: str = "À retenir") -> None:
    """Render a visually distinct takeaway box with a key finding.

    Use this for the 1–2 sentence summary at the top of a section.
    The text should express a result, not a method ("X % des liaisons…"
    not "Nous avons calculé…").

    Args:
        text: The key finding in plain French, 1–2 sentences max.
        title: Box heading. Defaults to "À retenir".
    """
    st.info(f"**{title}** — {text}")
