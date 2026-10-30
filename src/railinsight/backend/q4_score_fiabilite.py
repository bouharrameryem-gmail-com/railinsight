"""Logique métier de la Q4 : score de fiabilité des liaisons."""

import pandas as pd

from railinsight.analysis.q4_score_fiabilite import (
    add_score,
    aggregate_by_link,
    compare_variants,
    default_variants,
    network_score,
    prepare_data,
)
from railinsight.backend.donnees import charger_donnees
from railinsight.config import ScoreFiabilite, charger_config


def compute_reliability(
    raw: pd.DataFrame | None = None,
    params: ScoreFiabilite | None = None,
) -> dict[str, object]:
    """Compute the reliability score of every link.

    Args:
        raw: Output of `lire_donnees`. If None, loaded with `charger_donnees`.
        params: Analysis parameters. If None, taken from the configuration.
            A page can change one value with `dataclasses.replace`.

    Returns:
        A dict with `links` (one row per link, best score first), `network`
        (a Series with the score of the whole network) and `robustness`
        (output of `compare_variants`).

    Raises:
        DonneesInvalides: If the data file is missing columns.
    """
    if raw is None:
        raw = charger_donnees()
    if params is None:
        params = charger_config().score_fiabilite

    table = prepare_data(raw, params.periode_debut, params.periode_fin)
    totals = aggregate_by_link(table, params.min_trains)
    scoring = {
        "weight": params.poids,
        "cap_cancellation": params.cap_annulation,
        "cap_delay": params.cap_retard,
    }
    links = add_score(totals, **scoring)
    links = links.sort_values("score", ascending=False).reset_index(drop=True)
    return {
        "links": links,
        "network": network_score(totals, **scoring),
        "robustness": compare_variants(
            totals, default_variants(**scoring), top_n=params.top_n
        ),
    }
