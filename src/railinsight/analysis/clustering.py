"""Clustering des liaisons : mise à l'échelle, algorithmes et choix de k."""

from typing import Literal

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import PowerTransformer, StandardScaler

Algorithme = Literal["kmeans", "ward", "gmm"]

GRAINE = 42


def mettre_a_echelle(
    indicateurs: pd.DataFrame,
    type_normalisation: Literal["power", "standard"] = "power",
) -> tuple[np.ndarray, PowerTransformer | StandardScaler]:
    """Met à l'échelle les indicateurs avant le clustering."""
    normaliseur: PowerTransformer | StandardScaler
    if type_normalisation == "power":
        normaliseur = PowerTransformer(method="yeo-johnson", standardize=True)
    else:
        normaliseur = StandardScaler()
    return normaliseur.fit_transform(indicateurs.values), normaliseur


def entrainer_clustering(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    *,
    n_init: int = 50,
    covariance_type: Literal["full", "tied", "diag", "spherical"] = "full",
    random_state: int = GRAINE,
) -> np.ndarray:
    """Entraîne un modèle de clustering et renvoie les étiquettes des clusters."""
    if algorithm == "kmeans":
        return KMeans(
            n_clusters=k, n_init=n_init, random_state=random_state
        ).fit_predict(x_scaled)
    if algorithm == "ward":
        return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(
            x_scaled
        )
    if algorithm == "gmm":
        gmm = GaussianMixture(
            n_components=k,
            covariance_type=covariance_type,
            n_init=5,
            random_state=random_state,
        )
        gmm.fit(x_scaled)
        return gmm.predict(x_scaled)
    raise ValueError(
        f"Algorithme inconnu : {algorithm!r}. Choisir 'kmeans', 'ward' ou 'gmm'."
    )


def auto_select_k(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k_range: range = range(2, 9),
    min_cluster_size: int = 3,
    random_state: int = GRAINE,
) -> int:
    """Choisit k selon la silhouette, sous contrainte de taille minimale."""
    best_k = k_range.start
    best_sil = -1.0
    for k in k_range:
        labels = entrainer_clustering(x_scaled, algorithm, k, random_state=random_state)
        if np.bincount(labels).min() < min_cluster_size:
            continue
        sil = float(silhouette_score(x_scaled, labels))
        if sil > best_sil:
            best_sil = sil
            best_k = k
    return best_k
