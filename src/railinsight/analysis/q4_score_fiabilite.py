"""Q4 : score de fiabilité par liaison (annulations et retards moyens)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from railinsight.analysis.nettoyage import (
    filtrer_periode,
    invalider_hors_bornes,
    nettoyer_regularite,
    retirer_sans_train,
    taux,
)

# (nom, seuil minimal de score), du meilleur au pire.
CATEGORIES = (
    ("Très fiable", 85.0),
    ("Fiable", 70.0),
    ("Moyenne", 55.0),
    ("Peu fiable", 40.0),
    ("À risque", float("-inf")),
)
SUM_COLUMNS = ["prevus", "annules", "circules", "circules_mesures", "minutes_retard"]
MIN_PLAUSIBLE_DELAY = -15.0
REFERENCE = "Référence"


def prepare_data(
    raw: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
    min_plausible_delay: float | None = MIN_PLAUSIBLE_DELAY,
) -> pd.DataFrame:
    """Clean the raw table and restrict it to the analysed period.

    A mean delay below `min_plausible_delay` is set to NaN (data error, the
    row is kept). Rows without any planned train are removed.

    Args:
        raw: Output of `lire_donnees`.
        start: First month included (YYYY-MM), None for no lower bound.
        end: Last month included (YYYY-MM), None for no upper bound.
        min_plausible_delay: Lower bound of the mean delay, None to disable.

    Returns:
        A new DataFrame with the columns added by `nettoyer_regularite`.

    Raises:
        DonneesInvalides: If a required column is missing.
    """
    data = raw.copy()
    if "retard_moyen_arrivee" in data.columns:
        data["retard_moyen_arrivee"] = invalider_hors_bornes(
            data["retard_moyen_arrivee"], minimum=min_plausible_delay
        )
    data = retirer_sans_train(nettoyer_regularite(data))
    return filtrer_periode(data, start, end)


def aggregate_by_link(table: pd.DataFrame, min_trains: int = 100) -> pd.DataFrame:
    """Sum trains and delay minutes per link, both directions together.

    Args:
        table: Output of `prepare_data`.
        min_trains: Links with fewer planned trains are dropped.

    Returns:
        One row per link with `liaison`, `gare_a`, `gare_b` and SUM_COLUMNS.
    """
    grouped = table.groupby(["liaison", "gare_a", "gare_b"], as_index=False)[
        SUM_COLUMNS
    ].sum()
    return grouped[grouped["prevus"] >= min_trains].reset_index(drop=True)


def categorize(score: pd.Series) -> pd.Series:
    """Map each score to its category name (NaN stays NaN)."""

    def label(value: float) -> str | float:
        if pd.isna(value):
            return np.nan
        return next(name for name, threshold in CATEGORIES if value >= threshold)

    return score.map(label)


def add_score(
    table: pd.DataFrame,
    weight: float = 0.5,
    cap_cancellation: float = 6.0,
    cap_delay: float = 12.0,
) -> pd.DataFrame:
    """Add cancellation rate, mean delay, score (0 to 100) and category.

    Each indicator is scaled between 0 (no problem) and 1 (cap reached or
    exceeded), then score = 100 * (1 - w * cancellations - (1 - w) * delays).

    Args:
        table: Output of `aggregate_by_link` (or a one-row total).
        weight: Weight of cancellations, between 0 and 1.
        cap_cancellation: Cancellation rate (percent) giving the full penalty.
        cap_delay: Mean delay (minutes) giving the full penalty.

    Returns:
        A copy of `table` with `taux_annulation` (percent), `retard_moyen`
        (minutes), `score` and `categorie`. The score is NaN when the mean
        delay is unknown.
    """
    result = table.copy()
    result["taux_annulation"] = taux(result["annules"], result["prevus"])
    measured = result["circules_mesures"].where(result["circules_mesures"] > 0)
    result["retard_moyen"] = result["minutes_retard"] / measured
    penalty_cancel = (result["taux_annulation"] / cap_cancellation).clip(0, 1)
    penalty_delay = (result["retard_moyen"] / cap_delay).clip(0, 1)
    result["score"] = 100 * (1 - weight * penalty_cancel - (1 - weight) * penalty_delay)
    result["categorie"] = categorize(result["score"])
    return result


def network_score(links: pd.DataFrame, **params: float) -> pd.Series:
    """Score of the whole network, computed on the totals of all links."""
    total = links[SUM_COLUMNS].sum().to_frame().T
    return add_score(total, **params).iloc[0]


def default_variants(
    weight: float, cap_cancellation: float, cap_delay: float
) -> dict[str, dict[str, float]]:
    """Parameter sets used to test the robustness of the ranking."""
    base = {
        "weight": weight,
        "cap_cancellation": cap_cancellation,
        "cap_delay": cap_delay,
    }
    return {
        REFERENCE: base,
        "Annulations plus importantes": {**base, "weight": 0.7},
        "Retards plus importants": {**base, "weight": 0.3},
        "Seuils deux fois plus stricts": {
            **base,
            "cap_cancellation": cap_cancellation / 2,
            "cap_delay": cap_delay / 2,
        },
        "Seuils deux fois plus larges": {
            **base,
            "cap_cancellation": cap_cancellation * 2,
            "cap_delay": cap_delay * 2,
        },
    }


def compare_variants(
    links: pd.DataFrame,
    variants: dict[str, dict[str, float]],
    reference: str = REFERENCE,
    top_n: int = 10,
) -> pd.DataFrame:
    """Compare the ranking of each variant with the reference ranking.

    Args:
        links: Output of `aggregate_by_link` (without score).
        variants: Name -> keyword arguments of `add_score`.
        reference: Name of the reference variant (must be in `variants`).
        top_n: Size of the top used for the overlap.

    Returns:
        One row per variant except the reference, with `correlation` (of the
        ranks, 1 = identical) and `top_overlap` (links of the reference top
        that remain in the variant top).
    """
    ranks = pd.DataFrame(
        {
            name: add_score(links, **params)
            .set_index("liaison")["score"]
            .rank(ascending=False)
            for name, params in variants.items()
        }
    )
    top_reference = set(ranks[reference].nsmallest(top_n).index)
    rows = {
        name: {
            "correlation": ranks[reference].corr(ranks[name]),
            "top_overlap": len(top_reference & set(ranks[name].nsmallest(top_n).index)),
        }
        for name in ranks.columns
        if name != reference
    }
    return pd.DataFrame(rows).T
