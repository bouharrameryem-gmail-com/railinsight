"""Score de fiabilité des liaisons : annulations et retards résumés en une note sur 100.

Fonctions pures : aucun appel Streamlit, aucune lecture de fichier.
"""

import logging
from dataclasses import dataclass
from math import isfinite

import pandas as pd

from railinsight.analysis.nettoyage import (
    ajouter_minutes_retard,
    invalider_hors_bornes,
    retirer_sans_train,
    taux,
)

COLONNES_TOTAUX = ["prevus", "annules", "circules_mesures", "minutes_retard"]
logger = logging.getLogger(__name__)

# En dessous, le retard moyen est une erreur de saisie (voir le notebook Q3, règle D8)
RETARD_MOYEN_MINIMUM = -15.0

CATEGORIES = (
    ("Très fiable", 85),
    ("Fiable", 70),
    ("Moyenne", 55),
    ("Peu fiable", 40),
    ("À risque", float("-inf")),
)
NOMS_CATEGORIES = [nom for nom, _ in CATEGORIES]


@dataclass(frozen=True)
class ParametresScore:
    """Poids des annulations et plafonds donnant zéro sur chaque critère.

    Le poids et le taux d'annulation sont entre 0 et 1 ; le retard est en minutes.
    """

    poids_annulations: float = 0.5
    plafond_annulation: float = 0.06
    plafond_retard: float = 12.0

    def __post_init__(self) -> None:
        if not isfinite(self.poids_annulations) or not 0 <= self.poids_annulations <= 1:
            raise ValueError("poids_annulations doit être compris entre 0 et 1")
        if any(
            not isfinite(plafond) or plafond <= 0
            for plafond in (self.plafond_annulation, self.plafond_retard)
        ):
            raise ValueError("les plafonds doivent être strictement positifs")


def preparer_table_score(table: pd.DataFrame) -> pd.DataFrame:
    """Prépare la table nettoyée et écarte les lignes inutilisables.

    Un retard sous -15 min devient manquant : les annulations restent comptées,
    mais les trains concernés ne servent pas au calcul du retard moyen.
    """
    table = retirer_sans_train(table)
    valides = table["annules"].between(0, table["prevus"]) & table[
        ["mois", "gare_a", "gare_b"]
    ].notna().all(axis=1)
    valides &= table["gare_a"].ne("") & table["gare_b"].ne("")
    if not valides.all():
        logger.warning(
            "%d ligne(s) sans mois, gare ou nombre d'annulations valide retirée(s)",
            int((~valides).sum()),
        )
    table = table[valides].copy()
    table["retard_moyen_arrivee"] = invalider_hors_bornes(
        table["retard_moyen_arrivee"], minimum=RETARD_MOYEN_MINIMUM
    )
    return ajouter_minutes_retard(table)


def categoriser(notes: pd.Series) -> pd.Series:
    """Associe chaque note à sa catégorie (« Très fiable » à « À risque »)."""
    croissant = sorted(CATEGORIES, key=lambda categorie: categorie[1])
    bornes = [seuil for _, seuil in croissant] + [float("inf")]
    noms = [nom for nom, _ in croissant]
    return pd.cut(notes, bins=bornes, labels=noms, right=False).astype("object")


def calculer_score(totaux: pd.DataFrame, parametres: ParametresScore) -> pd.DataFrame:
    """Ajoute les indicateurs, la note et la catégorie aux totaux de chaque groupe.

    Le taux d'annulation est entre 0 et 1, le retard moyen en minutes.
    Sans retard mesuré, la note est manquante.
    """
    resultat = totaux.copy()
    resultat["taux_annulation"] = taux(
        resultat["annules"], resultat["prevus"], pour=1.0
    )
    resultat["retard_moyen"] = taux(
        resultat["minutes_retard"], resultat["circules_mesures"], pour=1.0
    )
    penalite_annulations = (
        resultat["taux_annulation"] / parametres.plafond_annulation
    ).clip(0, 1)
    penalite_retards = (resultat["retard_moyen"] / parametres.plafond_retard).clip(0, 1)
    poids = parametres.poids_annulations
    resultat["note"] = 100 * (
        1 - poids * penalite_annulations - (1 - poids) * penalite_retards
    )
    resultat["categorie"] = categoriser(resultat["note"])
    return resultat


def scores_par_liaison(
    table: pd.DataFrame, parametres: ParametresScore, min_trains: int = 100
) -> pd.DataFrame:
    """Classe les liaisons de la table préparée, les deux sens regroupés.

    Écarte celles avec moins de `min_trains` trains ou sans retard mesuré.
    """
    totaux = table.groupby(["liaison", "gare_a", "gare_b"], as_index=False)[
        COLONNES_TOTAUX
    ].sum()
    liaisons = calculer_score(totaux[totaux["prevus"] >= min_trains], parametres)
    liaisons = liaisons.dropna(subset=["note"])
    return liaisons.sort_values("note", ascending=False).reset_index(drop=True)


def scores_par_mois(table: pd.DataFrame, parametres: ParametresScore) -> pd.DataFrame:
    """Note de l'ensemble des lignes de `table`, mois par mois."""
    totaux = table.groupby("mois", as_index=False)[COLONNES_TOTAUX].sum()
    return calculer_score(totaux, parametres)


def resume_reseau(liaisons: pd.DataFrame, parametres: ParametresScore) -> pd.Series:
    """Taux d'annulation, retard moyen et note de l'ensemble des liaisons.

    Calculé sur les totaux : une liaison très desservie pèse plus qu'une liaison
    peu desservie. Ce n'est donc pas la moyenne des notes.
    """
    totaux = liaisons[COLONNES_TOTAUX].sum().to_frame().T
    return calculer_score(totaux, parametres).iloc[0]
