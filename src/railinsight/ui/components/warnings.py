"""Warning banners for data quality issues.

These components surface potential reliability issues to the user.
Always show them close to the affected chart or table, not at the top of the page.

Usage:
    small_sample_warning(n=8)
    missing_data_warning(n_missing=42, total=300, column="late30_rate")
"""

from __future__ import annotations

import streamlit as st

_SMALL_SAMPLE_THRESHOLD = 10


def small_sample_warning(
    n: int,
    threshold: int = _SMALL_SAMPLE_THRESHOLD,
    entity: str = "liaisons",
) -> None:
    """Show a warning when the sample size is too small for reliable conclusions.

    Args:
        n: Actual number of observations (routes, months, etc.).
        threshold: Minimum acceptable count. Defaults to 10.
        entity: Name of the counted entity for the message (e.g., "liaisons").
    """
    if n < threshold:
        st.warning(
            f"⚠️ Seulement {n} {entity} sélectionné(e)s. "
            "Les résultats peuvent être peu représentatifs."
        )


def missing_data_warning(
    n_missing: int,
    total: int,
    column: str | None = None,
) -> None:
    """Show a warning when a significant share of values are missing.

    Only shown when n_missing > 0.

    Args:
        n_missing: Number of missing values.
        total: Total number of values (including missing).
        column: Optional column name to mention in the message.
    """
    if n_missing <= 0:
        return

    pct = n_missing / total * 100 if total > 0 else 0.0
    col_mention = f" dans la colonne « {column} »" if column else ""
    st.warning(
        f"⚠️ {n_missing} valeur(s) manquante(s){col_mention} "
        f"({pct:.1f} % du total). "
        "Ces lignes sont exclues des calculs."
    )
