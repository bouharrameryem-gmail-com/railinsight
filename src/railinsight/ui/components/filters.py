"""Standardized filter widgets used across all pages.

Each filter is a standalone function that renders a widget and returns its value.
Always pass key_prefix=self._state.page_key to isolate widget keys per page.

Usage:
    from railinsight.ui.components.filters import (
        period_filter, route_filter, exclusion_filter,
        min_months_filter, duration_adjust_toggle,
    )
    start, end = period_filter(available_periods, key_prefix="q3_lab")
    route = route_filter(routes, key_prefix="q3_lab")
    exclusion = exclusion_filter(key_prefix="q3_lab")
    min_months = min_months_filter(key_prefix="q3_lab")
    adjusted = duration_adjust_toggle(key_prefix="q3_lab")
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import streamlit as st

from railinsight.config import DEFAULT_EXCLUSION, DEFAULT_MIN_MONTHS


def period_filter(
    available_periods: list[pd.Period],
    key_prefix: str,
    label: str = "Période",
) -> tuple[pd.Period, pd.Period]:
    """Render a period range selector (start → end).

    Args:
        available_periods: All periods present in the data (sorted).
        key_prefix: Page key prefix for widget isolation (from PageState).
        label: Label displayed above the filter.

    Returns:
        A (start, end) tuple of pd.Period objects.
    """
    options = [str(p) for p in available_periods]
    start_key = f"{key_prefix}__period_start"
    end_key = f"{key_prefix}__period_end"

    col1, col2 = st.columns(2)
    with col1:
        start_str = st.selectbox(
            f"{label} — début",
            options=options,
            index=0,
            key=start_key,
        )
    with col2:
        end_str = st.selectbox(
            f"{label} — fin",
            options=options,
            index=len(options) - 1,
            key=end_key,
        )

    start = pd.Period(start_str, freq="M")
    end = pd.Period(end_str, freq="M")

    if start > end:
        st.warning("La date de début est postérieure à la date de fin.")
        end = start

    return start, end


def route_filter(
    routes: list[str],
    key_prefix: str,
    label: str = "Liaison",
    multi: bool = False,
) -> str | list[str]:
    """Render a route selector (single or multi-select).

    Args:
        routes: List of route strings (e.g., "PARIS LYON → MARSEILLE").
        key_prefix: Page key prefix for widget isolation.
        label: Label displayed above the selector.
        multi: If True, uses st.multiselect. Otherwise st.selectbox.

    Returns:
        Selected route string, or list of strings when multi=True.
    """
    key = f"{key_prefix}__route"
    if multi:
        return st.multiselect(label, options=routes, key=key)
    return st.selectbox(label, options=routes, key=key)


def exclusion_filter(
    key_prefix: str,
    label: str = "Exclusion des mois exceptionnels",
) -> Literal["none", "known", "data"]:
    """Render the month exclusion rule selector.

    The three options correspond to the exclusion parameter of
    compute_route_features() (see WIKI §4.5).

    Args:
        key_prefix: Page key prefix for widget isolation.
        label: Label displayed above the selector.

    Returns:
        One of "none", "known", "data".
    """
    options: list[Literal["none", "known", "data"]] = ["none", "known", "data"]
    labels_map = {
        "none": "Aucune — tous les mois conservés",
        "known": "Événements documentés (grèves, Covid) — recommandé",
        "data": "Détection automatique par les données",
    }
    default_idx = options.index(DEFAULT_EXCLUSION)  # type: ignore[arg-type]

    chosen_label = st.selectbox(
        label,
        options=[labels_map[o] for o in options],
        index=default_idx,
        key=f"{key_prefix}__exclusion",
        help=(
            "Les mois exceptionnels (grèves, Covid) tirent les indicateurs vers le bas."
            " Les exclure donne une image de la régularité 'normale' de la liaison."
        ),
    )
    # Reverse lookup from display label to option key
    label_to_option = {v: k for k, v in labels_map.items()}
    return label_to_option[chosen_label]  # type: ignore[return-value]


def min_months_filter(
    key_prefix: str,
    label: str = "Mois minimum par liaison",
    default: int = DEFAULT_MIN_MONTHS,
    min_value: int = 6,
    max_value: int = 60,
) -> int:
    """Render a slider for the minimum number of months threshold.

    Routes with fewer valid months than this threshold are excluded from
    the analysis (compute_route_features min_months parameter).

    Args:
        key_prefix: Page key prefix for widget isolation.
        label: Label displayed above the slider.
        default: Default value. Defaults to DEFAULT_MIN_MONTHS (24).
        min_value: Minimum selectable value.
        max_value: Maximum selectable value.

    Returns:
        Selected integer threshold.
    """
    return st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=default,
        step=6,
        key=f"{key_prefix}__min_months",
        help=(
            "Une liaison avec peu de mois observés produit des indicateurs instables. "
            "Augmenter ce seuil sélectionne uniquement les liaisons bien documentées."
        ),
    )


def duration_adjust_toggle(
    key_prefix: str,
    label: str = "Lecture",
) -> bool:
    """Render the duration-adjustment toggle (raw vs. duration-adjusted).

    Long-distance routes naturally have more delays than short ones.
    The adjustment removes this mechanical effect for fairer comparison.

    Args:
        key_prefix: Page key prefix for widget isolation.
        label: Label displayed above the toggle.

    Returns:
        True if duration-adjusted reading is selected, False for raw.
    """
    options = [
        "Expérience voyageur (brut)",
        "À durée égale (ajusté)",
    ]
    choice = st.radio(
        label,
        options=options,
        index=0,
        key=f"{key_prefix}__duration_adjust",
        horizontal=True,
        help=(
            "**Brut** : l'indicateur tel que le vit le voyageur. "
            "**Ajusté** : l'indicateur corrigé de la durée du trajet, "
            "pour comparer une courte liaison parisienne avec un Paris-Nice."
        ),
    )
    return choice == options[1]
