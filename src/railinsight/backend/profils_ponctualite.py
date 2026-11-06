"""Données et clustering pour la page des profils de ponctualité."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from railinsight.analysis.clustering import (
    auto_select_k,
    entrainer_clustering,
    mettre_a_echelle,
)
from railinsight.analysis.indicateurs_liaisons import (
    FEATURE_SETS,
    construire_indicateurs_liaison,
    detect_redundancy,
)
from railinsight.analysis.nettoyage import (
    filtrer_periode,
    filtrer_service,
    nettoyer_regularite,
)
from railinsight.backend.dataloader import charger_donnees
from railinsight.exceptions import DonneesInvalides

_JEU_PAR_DEFAUT = "v3"
_K_MIN = 2
_MIN_LIAISONS = 4

# Noms des clusters ordonnés du plus régulier au moins régulier pour chaque k.
_NOMS_PAR_RANG: dict[int, list[str]] = {
    2: ["Régulières", "Peu fiables"],
    3: ["Régulières", "Intermédiaires", "Peu fiables"],
    4: ["Très régulières", "Assez régulières", "Peu fiables", "Très peu fiables"],
    5: [
        "Très régulières",
        "Assez régulières",
        "Moyennes",
        "Peu fiables",
        "Très peu fiables",
    ],
}


@dataclass(frozen=True)
class ResultatClustering:
    """Résultat du clustering : indicateurs, étiquettes, métriques et alertes."""

    indicateurs: pd.DataFrame
    etiquettes: np.ndarray
    k: int
    silhouette: float
    noms_clusters: dict[int, str]
    pca_coordonnees: np.ndarray
    redondances: list[tuple[str, str, float]]


def charger_donnees_clean() -> pd.DataFrame:
    """Charge et nettoie les données SNCF (service national uniquement)."""
    return filtrer_service(nettoyer_regularite(charger_donnees()))


def construire_indicateurs(
    donnees: pd.DataFrame,
    debut: str | None = None,
    fin: str | None = None,
    exclusion: Literal["none", "known", "data"] = "known",
    min_mois: int = 24,
) -> pd.DataFrame:
    """Calcule les indicateurs de ponctualité par liaison sur la période choisie.

    Args:
        donnees: Données nettoyées (depuis charger_donnees_clean).
        debut: Premier mois inclus au format "AAAA-MM", ou None = depuis le début.
        fin: Dernier mois inclus au format "AAAA-MM", ou None = jusqu'à la fin.
        exclusion: Règle d'exclusion des mois exceptionnels.
        min_mois: Nombre minimum de mois valides pour inclure une liaison.

    Returns:
        DataFrame avec une ligne par liaison et les colonnes d'indicateurs.

    Raises:
        DonneesInvalides: Données manquantes ou insuffisantes.
    """
    if debut or fin:
        donnees = filtrer_periode(donnees, debut, fin)
    return construire_indicateurs_liaison(
        donnees, exclusion=exclusion, min_months=min_mois
    )


def clusteriser(
    indicateurs: pd.DataFrame,
    k: int | None = None,
    jeu_variables: str = _JEU_PAR_DEFAUT,
) -> ResultatClustering:
    """Regroupe les liaisons en profils de ponctualité par K-means.

    Args:
        indicateurs: Résultat de `construire_indicateurs`.
        k: Nombre de clusters. Si None, sélectionné automatiquement par silhouette.
        jeu_variables: Clé dans FEATURE_SETS (par défaut "v3").

    Returns:
        Un `ResultatClustering` avec étiquettes, métriques et alertes de corrélation.

    Raises:
        DonneesInvalides: Pas assez de liaisons pour le clustering.
    """
    colonnes = FEATURE_SETS.get(jeu_variables, FEATURE_SETS[_JEU_PAR_DEFAUT])
    disponibles = [c for c in colonnes if c in indicateurs.columns]
    x_df = indicateurs[disponibles].dropna()

    if len(x_df) < _MIN_LIAISONS:
        raise DonneesInvalides(
            f"Seulement {len(x_df)} liaison(s) disponible(s). "
            "Réduisez le seuil minimum ou changez la règle d'exclusion."
        )

    x_scaled, _ = mettre_a_echelle(x_df)
    k_effectif = max(k if k is not None else auto_select_k(x_scaled, "kmeans"), _K_MIN)
    etiquettes = entrainer_clustering(x_scaled, "kmeans", k_effectif)
    sil = float(silhouette_score(x_scaled, etiquettes))

    pca = PCA(n_components=2, random_state=42).fit(x_scaled)
    coordonnees = pca.transform(x_scaled)
    noms = _nommer_clusters(x_df, etiquettes, k_effectif)
    redondances = detect_redundancy(indicateurs, disponibles)

    return ResultatClustering(
        indicateurs=indicateurs.loc[x_df.index],
        etiquettes=etiquettes,
        k=k_effectif,
        silhouette=sil,
        noms_clusters=noms,
        pca_coordonnees=coordonnees,
        redondances=redondances,
    )


def _nommer_clusters(
    x_df: pd.DataFrame, etiquettes: np.ndarray, k: int
) -> dict[int, str]:
    """Nomme chaque cluster selon son rang de ponctualité (rang 1 = plus régulier)."""
    noms_rang = _NOMS_PAR_RANG.get(k)
    if "late15_rate" not in x_df.columns:
        return {c: f"Profil {c + 1}" for c in range(k)}

    moyennes = x_df.assign(_lbl=etiquettes).groupby("_lbl")["late15_rate"].mean()
    rangs = moyennes.rank(ascending=True).astype(int)

    if noms_rang is None:
        return {c: f"Profil {int(rangs[c])}" for c in range(k)}

    return {c: noms_rang[int(rangs[c]) - 1] for c in range(k)}
