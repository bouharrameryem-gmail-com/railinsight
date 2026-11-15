"""Classement et tendance de fiabilité des liaisons TGV (Q1)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from railinsight.exceptions import DonneesInvalides

MOIS_DOCUMENTES: frozenset[str] = frozenset(
    {
        "2018-04",
        "2018-05",
        "2018-06",
        "2019-12",
        "2020-01",
        "2020-03",
        "2020-04",
        "2020-05",
        "2020-06",
        "2020-11",
        "2020-12",
        "2021-04",
        "2021-05",
        "2022-12",
        "2023-01",
        "2023-02",
        "2023-03",
        "2024-02",
        "2026-06",
    }
)

REGLES_TENDANCE = {
    "fenetre_covid": "Fenêtre COVID",
    "mois_documentes": "Grèves et confinements documentés",
    "aucune_exclusion": "Aucun mois exclu",
}

_COLONNES_REQUISES = {
    "date",
    "gare_depart",
    "gare_arrivee",
    "prevus",
    "annules",
    "circules",
    "retards_sup_15min",
    "duree_moyenne",
}


@dataclass(frozen=True, eq=False)
class AnalyseLiaisonsFiabilite:
    """Tables agrégées pour la page Q1."""

    classement: pd.DataFrame
    classement_duree: pd.DataFrame
    mensuel: pd.DataFrame
    tendances: pd.DataFrame
    tendance_reseau: pd.DataFrame
    periode_debut: str
    periode_fin: str
    covid_debut: str
    covid_fin: str
    correlation_duree: float


def calculer_analyse_liaisons_fiabilite(
    donnees: pd.DataFrame,
    covid_debut: str,
    covid_fin: str,
) -> AnalyseLiaisonsFiabilite:
    """Calcule les classements, les tendances et la sensibilité de la Q1.

    Les lignes de services différents sont conservées et additionnées après
    agrégation par liaison et par mois, comme dans le notebook Q1.
    """
    manquantes = sorted(_COLONNES_REQUISES - set(donnees.columns))
    if manquantes:
        raise DonneesInvalides(
            "colonnes manquantes pour l'analyse Q1 : " + ", ".join(manquantes)
        )
    if donnees.empty:
        raise DonneesInvalides("aucune donnée disponible pour l'analyse Q1.")

    travail = pd.DataFrame(
        {
            "liaison": donnees["gare_depart"].astype("string")
            + " → "
            + donnees["gare_arrivee"].astype("string"),
            "mois": pd.to_datetime(donnees["date"], errors="coerce")
            .dt.to_period("M")
            .dt.to_timestamp(),
            "prevus": donnees["prevus"],
            "incidents": donnees["annules"] + donnees["retards_sup_15min"],
            "duree": donnees["duree_moyenne"],
            "circules": donnees["circules"],
            "retards_sup_15min": donnees["retards_sup_15min"],
        }
    )
    impossibles = travail["retards_sup_15min"] > travail["circules"]
    travail.loc[impossibles, "incidents"] = np.nan
    travail = travail.loc[
        travail["prevus"].gt(0) & travail["incidents"].notna() & travail["mois"].notna()
    ].copy()
    if travail.empty:
        raise DonneesInvalides(
            "aucune ligne valide ne permet de calculer les taux d'incidents."
        )

    classement = (
        travail.groupby("liaison")
        .agg(
            prevus=("prevus", "sum"),
            incidents=("incidents", "sum"),
            duree_mediane=("duree", lambda s: s[s > 0].median()),
        )
        .assign(taux_incidents=lambda table: table["incidents"] / table["prevus"])
        .sort_values("taux_incidents", ascending=False, kind="stable")
    )

    mensuel = (
        travail.groupby(["liaison", "mois"], as_index=False)
        .agg(prevus=("prevus", "sum"), incidents=("incidents", "sum"))
        .assign(taux_incidents=lambda table: table["incidents"] / table["prevus"])
        .sort_values(["liaison", "mois"])
    )
    covid = {str(mois) for mois in pd.period_range(covid_debut, covid_fin, freq="M")}
    exclusions = {
        "fenetre_covid": covid,
        "mois_documentes": MOIS_DOCUMENTES,
        "aucune_exclusion": frozenset(),
    }
    tendances = pd.DataFrame(
        {
            nom: _calculer_pentes(mensuel, mois_exclus)
            for nom, mois_exclus in exclusions.items()
        }
    ).reindex(classement.index)

    reseau_mensuel = (
        mensuel.groupby("mois")
        .agg(prevus=("prevus", "sum"), incidents=("incidents", "sum"))
        .assign(taux_incidents=lambda table: table["incidents"] / table["prevus"])
        .reset_index()
    )
    tendance_reseau = pd.DataFrame(
        {
            nom: [_calculer_pente(reseau_mensuel, mois_exclus)]
            for nom, mois_exclus in exclusions.items()
        },
        index=["reseau"],
    )

    classement_duree, correlation = _corriger_effet_duree(classement)
    return AnalyseLiaisonsFiabilite(
        classement=classement,
        classement_duree=classement_duree,
        mensuel=mensuel,
        tendances=tendances,
        tendance_reseau=tendance_reseau,
        periode_debut=travail["mois"].min().strftime("%Y-%m"),
        periode_fin=travail["mois"].max().strftime("%Y-%m"),
        covid_debut=covid_debut,
        covid_fin=covid_fin,
        correlation_duree=correlation,
    )


def _calculer_pentes(
    mensuel: pd.DataFrame, mois_exclus: frozenset[str] | set[str]
) -> pd.Series:
    """Calcule une pente annuelle par liaison, en points de pourcentage."""
    resultat: dict[str, float] = {}
    for liaison, groupe in mensuel.groupby("liaison"):
        valide = groupe.loc[~groupe["mois"].dt.strftime("%Y-%m").isin(mois_exclus)]
        resultat[liaison] = _calculer_pente(valide, frozenset())
    return pd.Series(resultat, dtype="float64")


def _calculer_pente(
    mensuel: pd.DataFrame, mois_exclus: frozenset[str] | set[str]
) -> float:
    """Calcule une régression linéaire en points de pourcentage par an."""
    if mensuel.empty:
        return float("nan")
    valide = mensuel.loc[~mensuel["mois"].dt.strftime("%Y-%m").isin(mois_exclus)]
    if valide["mois"].nunique() < 2:
        return float("nan")
    temps = (valide["mois"].dt.year * 12 + valide["mois"].dt.month).to_numpy(
        dtype="float64"
    )
    taux = valide["taux_incidents"].to_numpy(dtype="float64")
    return float(np.polyfit(temps, taux, 1)[0] * 1200)


def _corriger_effet_duree(
    classement: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    """Classe les liaisons à durée égale et renvoie la corrélation de Spearman."""
    resultat = classement.copy()
    durees_valides = resultat["duree_mediane"].gt(0) & resultat["duree_mediane"].notna()
    log_duree = np.log(resultat.loc[durees_valides, "duree_mediane"])
    taux = resultat.loc[durees_valides, "taux_incidents"]
    correlation = float("nan")
    pente = 0.0
    if len(log_duree) >= 2 and log_duree.nunique() > 1:
        if taux.nunique() > 1:
            correlation = float(spearmanr(log_duree, taux).statistic)
        pente = float(np.polyfit(log_duree, taux, 1)[0])
    resultat["taux_ajuste"] = np.nan
    resultat.loc[durees_valides, "taux_ajuste"] = taux - pente * (
        log_duree - log_duree.mean()
    )
    return (
        resultat.sort_values("taux_ajuste", ascending=False, na_position="last"),
        correlation,
    )
