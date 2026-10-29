"""Logique métier de la Q2 : gares de départ à l'origine ou victimes des retards."""

import pandas as pd

from railinsight.analysis.q2_gares import (
    add_delay_categories,
    add_delay_shares,
    aggregate_by_station,
    filter_scope,
)
from railinsight.backend.donnees import charger_donnees

LEVELS = {"global": None, "annee": "annee", "date": "date"}


def compute_station_delays(
    raw: pd.DataFrame | None = None,
    exclude_2020: bool = True,
) -> dict[str, pd.DataFrame]:
    """Compute the delay tables per departure station at three time levels.

    Args:
        raw: Output of `lire_donnees`. If None, the data are loaded with
            `charger_donnees`.
        exclude_2020: If True, the year 2020 is removed before any computation.

    Returns:
        A dict with the keys `global`, `annee` and `date`. Each value is the
        output of `add_delay_shares`: one row per station (and per year or
        month for the last two), with the three category counts and shares.

    Raises:
        DonneesInvalides: If the data file is missing columns.
    """
    if raw is None:
        raw = charger_donnees()
    table = add_delay_categories(filter_scope(raw, exclude_2020=exclude_2020))
    return {
        name: add_delay_shares(aggregate_by_station(table, level))
        for name, level in LEVELS.items()
    }
