from dataclasses import dataclass

import pandas as pd

from railinsight.analysis.q2_gares import (
    add_delay_categories,
    add_delay_shares,
    aggregate_by_station,
    filter_scope,
)
from railinsight.backend.donnees import charger_donnees

@dataclass(frozen=True, eq=False)
class StationDelays:
    """Tables de retards par gare de départ, à trois niveaux de temps.

    Chaque table contient les effectifs des trois catégories de causes et leurs
    parts dans le total des trains en retard.

    Attributes:
        overall: Une ligne par gare, sur toute la période.
        by_year: Une ligne par gare et par année.
        by_month: Une ligne par gare et par mois.
    """

    overall: pd.DataFrame
    by_year: pd.DataFrame
    by_month: pd.DataFrame


def compute_station_delays(
    raw: pd.DataFrame, exclude_2020: bool = True
) -> StationDelays:
    """Calcule les tables de retards par gare de départ.

    Args:
        raw: Résultat de `lire_donnees`.
        exclude_2020: Si True, l'année 2020 est retirée avant tout calcul.

    Returns:
        Un `StationDelays` contenant les tables aux trois niveaux de temps.
    """
    table = add_delay_categories(filter_scope(raw, exclude_2020=exclude_2020))
    return StationDelays(
        overall=_delays_at(table, None),
        by_year=_delays_at(table, "annee"),
        by_month=_delays_at(table, "date"),
    )


def load_station_delays(exclude_2020: bool = True) -> StationDelays:
    """Charge les données SNCF puis calcule les tables de retards par gare.

    Args:
        exclude_2020: Si True, l'année 2020 est retirée avant tout calcul.

    Returns:
        Un `StationDelays` contenant les tables aux trois niveaux de temps.

    Raises:
        ConfigInvalide: la configuration est invalide.
        FileNotFoundError: le CSV n'existe pas à l'emplacement configuré.
        DonneesInvalides: le CSV est vide, illisible ou incomplet.
    """
    return compute_station_delays(charger_donnees(), exclude_2020)


def _delays_at(table: pd.DataFrame, level: str | None) -> pd.DataFrame:
    """Agrège par gare à un niveau de temps, puis ajoute les parts par catégorie.

    Args:
        table: Résultat de `add_delay_categories`.
        level: None pour toute la période, ou `annee` / `date`.
    """
    return add_delay_shares(aggregate_by_station(table, level))
