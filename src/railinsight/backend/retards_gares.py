from dataclasses import dataclass

import pandas as pd

from railinsight.analysis.causes_retards import (
    agreger_par_gare,
    ajouter_categories_retard,
    ajouter_parts_retard,
    filtrer_perimetre_national,
)
from railinsight.backend.dataloader import charger_donnees


@dataclass(frozen=True, eq=False)
class RetardsParGare:
    """Regroupe les retards par gare, à différentes échelles temporelles."""

    overall: pd.DataFrame
    by_year: pd.DataFrame
    by_month: pd.DataFrame


def calculer_retards_par_gare(
    raw: pd.DataFrame, exclude_2020: bool = True
) -> RetardsParGare:
    """Calcule les tables de retards par gare de départ.

    Args:
        raw: Résultat de `lire_donnees`.
        exclude_2020: Si True, l'année 2020 est retirée avant tout calcul.

    Returns:
        Un `RetardsParGare` contenant les tables aux trois niveaux de temps.
    """
    table = ajouter_categories_retard(
        filtrer_perimetre_national(raw, exclude_2020=exclude_2020)
    )
    return RetardsParGare(
        overall=calculer_retards_par_periode(table, None),
        by_year=calculer_retards_par_periode(table, "annee"),
        by_month=calculer_retards_par_periode(table, "date"),
    )


def charger_retards_par_gare(exclude_2020: bool = True) -> RetardsParGare:
    """Charge les données SNCF et calcule les retards par gare."""
    return calculer_retards_par_gare(charger_donnees(), exclude_2020)


def calculer_retards_par_periode(
    table: pd.DataFrame, niveau: str | None
) -> pd.DataFrame:
    """Agrège les retards par gare et calcule les parts par catégorie."""
    return ajouter_parts_retard(agreger_par_gare(table, niveau))
