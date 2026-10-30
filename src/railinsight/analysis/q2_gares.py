import pandas as pd

CAUSES_NON_HERITEES = [
    "prct_cause_infrastructure",
    "prct_cause_trafic",
    "prct_cause_materiel",
]
CAUSES_HERITEES = ["prct_cause_gare", "prct_cause_voyageurs"]
CAUSES_EXTERNES = ["prct_cause_externe"]

DELAY_COLUMNS = ["retard_heritees", "retard_non_heritees", "retard_externes"]
LEVELS = {None, "annee", "date"}


def filter_scope(table: pd.DataFrame, exclude_2020: bool = True) -> pd.DataFrame:
    """Keep the national service, convert the date and add the year column.

    Args:
        table: Output of `lire_donnees`. Must contain `service` and `date`
            (text, format YYYY-MM).
        exclude_2020: If True, rows of year 2020 are removed.

    Returns:
        A new DataFrame with `date` as a datetime and a new `annee` column.
        The input is not modified.
    """
    retour = table[table["service"] == "National"].copy()
    retour["date"] = pd.to_datetime(retour["date"], format="%Y-%m")
    retour["annee"] = retour["date"].dt.year
    if exclude_2020:
        retour = retour[retour["annee"] != 2020]
    return retour.reset_index(drop=True)


def add_delay_categories(table: pd.DataFrame) -> pd.DataFrame:
    """Add the number of late trains per cause category.

    Each count is the number of trains late at arrival multiplied by the sum
    of the matching cause percentages divided by 100. A missing percentage
    counts as 0.

    Args:
        table: One row per (month, route). Must contain `retards_arrivee` and
            every column listed in CAUSES_HERITEES, CAUSES_NON_HERITEES and
            CAUSES_EXTERNES.

    Returns:
        A copy of `table` with three more columns: `retard_heritees`,
        `retard_non_heritees` and `retard_externes`.
    """
    retour = table.copy()
    toutes = CAUSES_HERITEES + CAUSES_NON_HERITEES + CAUSES_EXTERNES
    masque = retour[toutes].isna().all(axis=1)
    retour = retour[~masque].copy()
    retour["retard_heritees"] = retour["retards_arrivee"] * (
        retour[CAUSES_HERITEES].sum(axis=1) / 100
    )
    retour["retard_non_heritees"] = retour["retards_arrivee"] * (
        retour[CAUSES_NON_HERITEES].sum(axis=1) / 100
    )
    retour["retard_externes"] = retour["retards_arrivee"] * (
        retour[CAUSES_EXTERNES].sum(axis=1) / 100
    )
    return retour


def aggregate_by_station(table: pd.DataFrame, level: str | None = None) -> pd.DataFrame:
    """Sum the late trains per category for each departure station.

    Args:
        table: Output of `add_delay_categories` (and of `filter_scope` if
            `level` is `annee`, which creates that column).
        level: None for one row per station over the whole period, or
            `annee` / `date` for one row per station and period.

    Returns:
        A new DataFrame with the grouping keys as columns, then the three
        category columns.

    Raises:
        ValueError: If `level` is not None, `annee` or `date`.
    """
    if level not in LEVELS:
        raise ValueError(
            f"level must be one of {sorted(map(str, LEVELS))}, got {level!r}"
        )
    keys = ["gare_depart"] if level is None else ["gare_depart", level]
    return table.groupby(keys)[DELAY_COLUMNS].sum().reset_index()


def add_delay_shares(table: pd.DataFrame) -> pd.DataFrame:
    """Add the share of each category in the total of late trains.

    Args:
        table: Output of `aggregate_by_station`.

    Returns:
        A copy of `table` with `taux_heritees`, `taux_non_heritees` and
        `taux_externes` (values between 0 and 1). A row with no late train
        gets NaN.
    """
    retour = table.copy()
    total = retour[DELAY_COLUMNS].sum(axis=1).where(lambda s: s != 0)
    retour["taux_heritees"] = retour["retard_heritees"] / total
    retour["taux_non_heritees"] = retour["retard_non_heritees"] / total
    retour["taux_externes"] = retour["retard_externes"] / total
    return retour


def rank_stations(table: pd.DataFrame, column: str, n: int = 15) -> pd.DataFrame:
    """Return the n stations with the highest value in `column`.

    Args:
        table: Output of `aggregate_by_station` or `add_delay_shares`.
        column: Column used for the ranking.
        n: Number of rows to keep.

    Returns:
        The n rows with the largest values, sorted in descending order.
        Rows where `column` is missing are ignored.
    """
    return table.nlargest(n, column)
