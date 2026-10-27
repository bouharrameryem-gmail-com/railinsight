"""Highlighted "À retenir" takeaway box.

Usage:
    insight_box("Les 5 liaisons les moins fiables concentrent 40 % des retards.")
"""

from __future__ import annotations

import streamlit as st


def insight_box(text: str, title: str = "À retenir") -> None:
    """Render a visually distinct SNCF-branded takeaway box with a key finding.

    Use this for the 1–2 sentence summary at the top of a section.
    The text should express a result, not a method ("X % des liaisons…"
    not "Nous avons calculé…").

    Args:
        text: The key finding in plain French, 1–2 sentences max.
            Markdown bold (**...**) is supported.
        title: Box heading. Defaults to "À retenir".
    """
    st.markdown(
        f'<div style="'
        f"background:#FFF5F7;"
        f"border-left:5px solid #E8003D;"
        f"border-radius:0 10px 10px 0;"
        f"padding:16px 20px;"
        f'margin:12px 0 20px;">'
        f'<div style="font-size:0.7rem;font-weight:700;color:#E8003D;'
        f"text-transform:uppercase;letter-spacing:0.09em;"
        f'margin-bottom:7px;">● {title}</div>'
        f'<div style="color:#1A1A2E;line-height:1.65;font-size:0.92rem;">'
        f"{text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
