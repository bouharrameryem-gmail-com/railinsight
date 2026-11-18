"""Indicateurs de l'accueil sur des fenêtres calendaires et des comptes appariés."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from railinsight.analysis.nettoyage import retirer_doublons
from railinsight.exceptions import DonneesInvalides

logger = logging.getLogger(__name__)
_CLE = ["mois", "gare_depart", "gare_arrivee"]


def _paires_valides(
    table: pd.DataFrame, numerateur: str, denominateur: str
) -> pd.DataFrame:
    """Retient ensemble le numérateur et son dénominateur cohérent."""
    comptes = table[["prevus", "annules", numerateur, denominateur]]
    valides = (
        comptes.notna().all(axis=1)
        & np.isfinite(comptes).all(axis=1)
        & table["prevus"].gt(0)
        & table["annules"].between(0, table["prevus"])
        & table[denominateur].gt(0)
        & table[numerateur].between(0, table[denominateur])
    )
    return table.loc[valides]


@dataclass(frozen=True)
class TauxAccueil:
    """Taux pondéré, écart en points et nombre de lignes non mesurables."""

    valeur: float | None
    evolution_points: float | None
    lignes_ecartees: int


@dataclass(frozen=True)
class BilanAccueil:
    """Bilan des douze derniers mois disponibles du service national."""

    debut: str
    fin: str
    debut_precedent: str
    fin_precedent: str
    n_mois: int
    n_liaisons: int
    retards: TauxAccueil
    annulations: TauxAccueil


def _mesurer(
    actuel: pd.DataFrame, precedent: pd.DataFrame, numerateur: str, denominateur: str
) -> TauxAccueil:
    """Compare uniquement des mesures valides sur des périmètres identiques."""

    def taux(table: pd.DataFrame) -> float | None:
        """Pondère par le volume sans inventer de taux pour un jeu vide."""
        if table.empty:
            return None
        return float(table[numerateur].sum() / table[denominateur].sum())

    def couverture(table: pd.DataFrame) -> set[tuple[str, str, str]]:
        """Identifie les mesures par mois de l'année et liaison orientée."""
        return set(
            table.assign(mois=table["mois"].str[-2:])[_CLE].itertuples(
                index=False, name=None
            )
        )

    mesures = _paires_valides(actuel, numerateur, denominateur)
    mesures_precedentes = _paires_valides(precedent, numerateur, denominateur)
    valeur, ancienne = taux(mesures), taux(mesures_precedentes)
    ecart = None
    if (
        valeur is not None
        and ancienne is not None
        and mesures["mois"].nunique() == 12
        and mesures_precedentes["mois"].nunique() == 12
        and couverture(mesures) == couverture(mesures_precedentes)
    ):
        ecart = (valeur - ancienne) * 100
    exclues = len(actuel) - len(mesures)
    if exclues:
        logger.warning(
            "Accueil, %s : %d ligne(s) sans comptes appariés valides écartée(s)",
            numerateur,
            exclues,
        )
    return TauxAccueil(valeur, ecart, exclues)


def calculer_bilan_accueil(donnees: pd.DataFrame) -> BilanAccueil:
    """Agrège le service national nettoyé, sans modifier les données d'entrée.

    Les liaisons comptées regroupent les deux sens et ont du trafic dans la
    fenêtre courante. Chaque taux est un ratio de sommes sur les seules lignes
    où numérateur et dénominateur sont valides. Une évolution n'est disponible
    que si les deux fenêtres de douze mois ont la même couverture de mesures
    (mois de l'année et gares orientées), sans extrapoler les mois absents.
    """
    requises = {*_CLE, "liaison", "prevus", "annules", "circules", "retards_sup_15min"}
    manquantes = requises - set(donnees.columns)
    if manquantes:
        raise DonneesInvalides(
            "Accueil : colonnes manquantes : " + ", ".join(sorted(manquantes))
        )
    if donnees.empty:
        raise DonneesInvalides("Accueil : aucune donnée nationale disponible.")
    dates = pd.to_datetime(donnees["mois"], format="%Y-%m", errors="coerce")
    if dates.isna().any() or donnees[[*_CLE, "liaison"]].isna().any().any():
        raise DonneesInvalides("Accueil : mois ou gares manquants ou invalides.")
    table = retirer_doublons(donnees, _CLE)
    fin = pd.Period(dates.max(), freq="M")
    debut = fin - 11
    precedent_fin = debut - 1
    precedent_debut = debut - 12
    actuel = table[table["mois"].between(str(debut), str(fin))]
    precedent = table[table["mois"].between(str(precedent_debut), str(precedent_fin))]
    return BilanAccueil(
        str(debut),
        str(fin),
        str(precedent_debut),
        str(precedent_fin),
        int(actuel["mois"].nunique()),
        int(actuel.loc[actuel["prevus"].gt(0), "liaison"].nunique()),
        _mesurer(actuel, precedent, "retards_sup_15min", "circules"),
        _mesurer(actuel, precedent, "annules", "prevus"),
    )


def calculer_liaisons_accueil(
    donnees: pd.DataFrame, bilan: BilanAccueil
) -> pd.DataFrame:
    """Agrège la carte sur la fenêtre du bilan, deux sens regroupés.

    L'incident désigne une annulation ou un retard à l'arrivée > 15 min.
    Les comptes sont appariés et validés avant agrégation. Une liaison sans
    mesure valide n'est pas notée ; les exclusions sont journalisées.
    """
    table = retirer_doublons(donnees, _CLE)
    table = table[table["mois"].between(bilan.debut, bilan.fin)]
    valides = _paires_valides(table, "retards_sup_15min", "circules")
    # Une liaison intégralement annulée reste mesurable pour les incidents.
    tout_annule = table[
        table["prevus"].gt(0)
        & np.isfinite(table["prevus"])
        & table["annules"].eq(table["prevus"])
        & table["circules"].eq(0)
        & table["retards_sup_15min"].eq(0)
    ]
    valides = pd.concat([valides, tout_annule]).copy()
    exclues = len(table) - len(valides)
    if exclues:
        logger.warning(
            "Carte accueil : %d ligne(s) sans mesure valide exclue(s)", exclues
        )
    ordre = valides["gare_depart"] <= valides["gare_arrivee"]
    valides["gare_a"] = valides["gare_depart"].where(ordre, valides["gare_arrivee"])
    valides["gare_b"] = valides["gare_arrivee"].where(ordre, valides["gare_depart"])
    valides["incidents"] = valides["annules"] + valides["retards_sup_15min"]
    resultat = valides.groupby(["gare_a", "gare_b"], as_index=False).agg(
        prevus=("prevus", "sum"),
        incidents=("incidents", "sum"),
        n_mois=("mois", "nunique"),
    )
    resultat["taux_incidents"] = resultat["incidents"] / resultat["prevus"]
    resultat["liaison"] = resultat["gare_a"] + " ↔ " + resultat["gare_b"]
    return resultat.sort_values("taux_incidents", ascending=False).reset_index(
        drop=True
    )
