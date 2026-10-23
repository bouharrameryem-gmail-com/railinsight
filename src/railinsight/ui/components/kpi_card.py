"""KPI metric cards for displaying key figures.

Usage:
    kpi_card("Retards > 15 min", "27,3 %", delta="-1,2 pt")
    kpi_row([{"label": "...", "value": "..."}, ...])
"""

from __future__ import annotations

import streamlit as st


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    help: str | None = None,
) -> None:
    """Render a single KPI metric card using st.metric.

    Args:
        label: Short description of the indicator (e.g., "Retards > 15 min").
        value: Formatted value string (e.g., "27,3 %"). Use fmt_pct / fmt_number.
        delta: Optional change indicator (e.g., "+1,2 pt", "-3 %").
            Positive strings are shown in green, negative in red by default.
        help: Optional tooltip text explaining the indicator.
    """
    st.metric(label=label, value=value, delta=delta, help=help)


def kpi_row(
    cards: list[dict],
    n_columns: int | None = None,
) -> None:
    """Render multiple KPI cards side by side in a row.

    Args:
        cards: List of dicts with keys "label" (required), "value" (required),
            "delta" (optional), "help" (optional).
        n_columns: Number of columns. Defaults to len(cards) (all in one row).

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
            )
