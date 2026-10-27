"""KPI metric cards — custom styled HTML cards with SNCF branding.

Usage:
    kpi_card("Retards > 15 min", "27,3 %", delta="-1,2 pt", color=SNCF_RED)
    kpi_row([{"label": "...", "value": "..."}, ...])
"""

from __future__ import annotations

import streamlit as st

from railinsight.ui.theme.tokens import SNCF_RED


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    help: str | None = None,
    color: str = SNCF_RED,
) -> None:
    """Render a single KPI card as a styled HTML block.

    The card has a colored top border, a large value, and an optional
    directional delta (green if starts with "+", red if starts with "-").

    Args:
        label: Short description of the indicator (e.g., "Retards > 15 min").
        value: Formatted value string (e.g., "27,3 %").
        delta: Optional change indicator (e.g., "+1,2 pt", "-3 %").
        help: Optional explanation shown as a small caption below the card.
        color: Accent color for the top border. Defaults to SNCF red.
    """
    delta_html = ""
    if delta:
        is_positive = delta.strip().startswith("+")
        delta_color = "#2E7D32" if is_positive else "#C62828"
        arrow = "▲" if is_positive else "▼"
        delta_html = (
            f'<div class="ri-kpi-delta" style="color:{delta_color};">'
            f"{arrow} {delta}</div>"
        )

    st.markdown(
        f'<div class="ri-kpi-card" style="border-top:4px solid {color};">'
        f'<div class="ri-kpi-label">{label}</div>'
        f'<div class="ri-kpi-value">{value}</div>'
        f"{delta_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if help:
        st.caption(f"ℹ️ {help}")


def kpi_row(
    cards: list[dict],
    n_columns: int | None = None,
) -> None:
    """Render multiple KPI cards side by side in a row.

    Args:
        cards: List of dicts with keys "label", "value" (required),
            "delta", "help", "color" (optional).
        n_columns: Number of columns. Defaults to len(cards).

    Example:
        kpi_row([
            {"label": "Liaisons", "value": "20"},
            {"label": "Retards > 15 min", "value": "27,3 %", "delta": "-1,2 pt"},
        ])
    """
    n = n_columns if n_columns is not None else len(cards)
    if n == 0:
        return
    cols = st.columns(n)
    for col, card in zip(cols, cards, strict=False):
        with col:
            kpi_card(
                label=card["label"],
                value=card["value"],
                delta=card.get("delta"),
                help=card.get("help"),
                color=card.get("color", SNCF_RED),
            )
