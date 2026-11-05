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
)
from railinsight.analysis.nettoyage import filtrer_service, nettoyer_regularite
from railinsight.backend.dataloader import charger_donnees
from railinsight.exceptions import DonneesInvalides

_JEU_PAR_DEFAUT = "v3"
_K_MIN = 2
_MIN_LIAISONS = 4


@dataclass(frozen=True)
class ResultatClustering:
    """Résultat du clustering : indicateurs, étiquettes et coordonnées PCA."""

    indicateurs: pd.DataFrame
    etiquettes: np.ndarray
    k: int
    silhouette: float
    noms_clusters: dict[int, str]
    pca_coordonnees: np.ndarray


def charger_indicateurs(
    exclusion: Literal["none", "known", "data"] = "known",
    min_mois: int = 24,
) -> pd.DataFrame:
    """Charge les données SNCF et calcule les indicateurs de ponctualité par liaison.

    Args:
        exclusion: Règle d'exclusion des mois exceptionnels.
        min_mois: Nombre minimum de mois valides pour inclure une liaison.

    Returns:
        Un DataFrame avec une ligne par liaison et les colonnes d'indicateurs.

    Raises:
        DonneesInvalides: Données manquantes ou insuffisantes.
    """
    donnees = filtrer_service(nettoyer_regularite(charger_donnees()))
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
        indicateurs: Résultat de `charger_indicateurs`.
        k: Nombre de clusters. Si None, sélectionné automatiquement par silhouette.
        jeu_variables: Clé dans FEATURE_SETS (par défaut "v3").

    Returns:
        Un `ResultatClustering` avec étiquettes, métriques et coordonnées PCA.

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

    return ResultatClustering(
        indicateurs=indicateurs.loc[x_df.index],
        etiquettes=etiquettes,
        k=k_effectif,
        silhouette=sil,
        noms_clusters=noms,
        pca_coordonnees=coordonnees,
    )


def _nommer_clusters(
    x_df: pd.DataFrame, etiquettes: np.ndarray, k: int
) -> dict[int, str]:
    """Nomme chaque cluster selon son niveau moyen de retards > 15 min."""
    if "late15_rate" not in x_df.columns:
        return {c: f"Profil {c + 1}" for c in range(k)}

    moyennes = x_df.assign(_lbl=etiquettes).groupby("_lbl")["late15_rate"].mean()
    rangs = moyennes.rank(ascending=True)

    noms: dict[int, str] = {}
    for c in range(k):
        rang = int(rangs[c])
        if k == 2:  # noqa: PLR2004
            noms[c] = "Liaisons régulières" if rang == 1 else "Liaisons peu fiables"
        elif rang == 1:
            noms[c] = "Très régulières"
        elif rang == k:
            noms[c] = "Peu fiables"
        else:
            noms[c] = f"Profil intermédiaire {rang - 1}"
    return noms
