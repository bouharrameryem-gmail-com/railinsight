"""Clustering des liaisons : mise à l'échelle, algorithmes et choix de k.
 
Fonctions pures : aucun appel Streamlit, aucune lecture de fichier.
 
Exemple :
    x_scaled, scaler = scale_features(x)
    k = auto_select_k(x_scaled, "kmeans")
    labels = fit_clustering(x_scaled, "kmeans", k)
"""
 
from typing import Literal
 
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import PowerTransformer, StandardScaler
 
from railinsight.exceptions import InsufficientDataError
 
Algorithme = Literal["kmeans", "ward", "gmm"]
 
GRAINE = 42  # graine par défaut de tous les tirages aléatoires (reproductibilité)
MIN_LIAISONS_CLUSTERING = 4  # en dessous, le clustering n'a pas de sens
_MIN_OBSERVATIONS = 2
 
 
def scale_features(
    features_df: pd.DataFrame,
    scaler_type: Literal["power", "standard"] = "power",
) -> tuple[np.ndarray, PowerTransformer | StandardScaler]:
    """Met à l'échelle la matrice d'indicateurs avant le clustering.
 
    Args:
        features_df: DataFrame d'indicateurs sans NaN (une ligne par liaison).
        scaler_type: "power" applique Yeo-Johnson puis une normalisation z
            (réduit l'asymétrie) ; "standard" applique seulement la normalisation z.
 
    Returns:
        (matrice mise à l'échelle de forme (n_liaisons, n_indicateurs), scaler ajusté).
    """
    scaler: PowerTransformer | StandardScaler
    if scaler_type == "power":
        scaler = PowerTransformer(method="yeo-johnson", standardize=True)
    else:
        scaler = StandardScaler()
    return scaler.fit_transform(features_df.values), scaler
 
 
def fit_clustering(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    *,
    n_init: int = 50,
    covariance_type: Literal["full", "tied", "diag", "spherical"] = "full",
    random_state: int = GRAINE,
) -> np.ndarray:
    """Ajuste un modèle de clustering et renvoie l'étiquette de chaque liaison.
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle, (n_liaisons, n_indicateurs).
        algorithm: "kmeans", "ward" (hiérarchique, lien de Ward) ou "gmm".
        k: Nombre de clusters (ou de composantes pour le GMM).
        n_init: Nombre d'initialisations aléatoires de K-means (ignoré sinon).
        covariance_type: Type de matrice de covariance du GMM (ignoré sinon).
        random_state: Graine pour la reproductibilité.
 
    Returns:
        Un tableau d'entiers de forme (n_liaisons,), étiquettes à partir de 0.
 
    Raises:
        ValueError: algorithme inconnu.
    """
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
    """Choisit le k au meilleur score de silhouette, avec une taille minimale de cluster.
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle.
        algorithm: Algorithme de clustering.
        k_range: Valeurs de k à essayer.
        min_cluster_size: Nombre minimal de liaisons par cluster ; les
            configurations qui ne le respectent pas sont ignorées.
        random_state: Graine pour la reproductibilité.
 
    Returns:
        Le meilleur k (le plus petit de `k_range` si aucune configuration ne
        respecte la contrainte).
    """
    best_k = k_range.start
    best_sil = -1.0
    for k in k_range:
        labels = fit_clustering(x_scaled, algorithm, k, random_state=random_state)
        if np.bincount(labels).min() < min_cluster_size:
            continue
        sil = float(silhouette_score(x_scaled, labels))
        if sil > best_sil:
            best_sil = sil
            best_k = k
    return best_k
 
 
def compute_ward_linkage(x_scaled: np.ndarray) -> np.ndarray:
    """Calcule la matrice de liaison hiérarchique de Ward (pour le dendrogramme).
 
    Args:
        x_scaled: Matrice (n_liaisons, n_indicateurs) déjà mise à l'échelle.
 
    Returns:
        La matrice de liaison (n-1, 4) de scipy.cluster.hierarchy.linkage.
        Chaque ligne : [enfant_a, enfant_b, distance, taille_du_cluster].
 
    Raises:
        InsufficientDataError: moins de deux observations.
    """
    if len(x_scaled) < _MIN_OBSERVATIONS:
        raise InsufficientDataError(
            "Le lien de Ward requiert au moins 2 observations."
        )
    return linkage(x_scaled, method="ward")