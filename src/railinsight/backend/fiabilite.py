"""Préparation des données et des résultats de la page Q4."""

import pandas as pd

from railinsight.analysis.graphe_reseau import positions_gares
from railinsight.analysis.nettoyage import filtrer_periode, nettoyer_regularite
from railinsight.analysis.score_fiabilite import (
    ParametresScore,
    preparer_table_score,
    scores_par_liaison,
)
from railinsight.backend.dataloader import charger_donnees
from railinsight.exceptions import DonneesInvalides

_PARAMETRES_PAR_DEFAUT = ParametresScore()


def charger_table_score() -> pd.DataFrame:
    """Charge et prépare tous les services SNCF, comme dans le notebook."""
    table = preparer_table_score(nettoyer_regularite(charger_donnees()))
    if table.empty:
        raise DonneesInvalides("Aucune donnée utilisable pour le score de fiabilité.")
    return table


def analyser_fiabilite(
    table: pd.DataFrame,
    debut: str,
    fin: str,
    parametres: ParametresScore = _PARAMETRES_PAR_DEFAUT,
    min_trains: int = 100,
) -> pd.DataFrame:
    """Calcule les notes des liaisons sur la période choisie."""
    if debut > fin:
        raise DonneesInvalides("Le début de la période doit précéder la fin.")
    if min_trains < 0:
        raise DonneesInvalides("Le nombre minimum de trains doit être positif ou nul.")
    liaisons = scores_par_liaison(
        filtrer_periode(table, debut, fin), parametres, min_trains
    )
    if liaisons.empty:
        raise DonneesInvalides(
            "Aucune liaison avec au moins "
            f"{min_trains} trains et un retard mesuré. Élargissez la période."
        )
    return liaisons


def positions_reseau(table: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """Fixe le dessin sur toutes les liaisons, indépendamment des filtres."""
    return positions_gares(zip(table["gare_a"], table["gare_b"], strict=True))
