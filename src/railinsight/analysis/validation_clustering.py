"""Validation du clustering : stabilité, structure réelle et comparaison.
 
Fonctions pures : aucun appel Streamlit, aucune lecture de fichier.
"""
 
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
 
from railinsight.analysis.clustering import GRAINE, Algorithme, fit_clustering
from railinsight.analysis.indicateurs_liaisons import MIN_LIGNES_VALIDES
 
_MIN_LIAISONS_COMMUNES = 2
 
 
def _inertie(x_scaled: np.ndarray, labels: np.ndarray) -> float:
    """Somme des carrés des distances de chaque point au centre de son cluster."""
    total = 0.0
    for etiquette in np.unique(labels):
        groupe = x_scaled[labels == etiquette]
        total += float(np.sum((groupe - groupe.mean(axis=0)) ** 2))
    return total
 
 
def silhouette_curve(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k_range: range = range(2, 9),
    random_state: int = GRAINE,
) -> pd.DataFrame:
    """Calcule silhouette, Davies-Bouldin et inertie pour plusieurs valeurs de k.
 
    L'inertie a un sens pour tous les algorithmes ; le coude est le plus net
    avec K-means.
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle.
        algorithm: Algorithme de clustering.
        k_range: Valeurs de k à évaluer.
        random_state: Graine pour la reproductibilité.
 
    Returns:
        Un DataFrame avec les colonnes : k, silhouette, davies_bouldin,
        min_cluster_size, inertia.
    """
    lignes = []
    for k in k_range:
        labels = fit_clustering(x_scaled, algorithm, k, random_state=random_state)
        lignes.append(
            {
                "k": k,
                "silhouette": float(silhouette_score(x_scaled, labels)),
                "davies_bouldin": float(davies_bouldin_score(x_scaled, labels)),
                "min_cluster_size": int(np.bincount(labels).min()),
                "inertia": _inertie(x_scaled, labels),
            }
        )
    return pd.DataFrame(lignes)
 
 
def compute_ari_seeds(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    n_seeds: int = 20,
) -> pd.Series:
    """Calcule l'ARI entre une solution de référence et d'autres graines.
 
    La graine 0 sert de référence. Un ARI élevé signifie que la solution est
    stable.
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle.
        algorithm: Algorithme de clustering.
        k: Nombre de clusters.
        n_seeds: Nombre de graines alternatives à tester.
 
    Returns:
        Une série de valeurs d'ARI (une par graine).
    """
    ref = fit_clustering(x_scaled, algorithm, k, random_state=0)
    aris = [
        float(
            adjusted_rand_score(
                ref, fit_clustering(x_scaled, algorithm, k, random_state=graine)
            )
        )
        for graine in range(1, n_seeds + 1)
    ]
    return pd.Series(aris, name="ari")
 
 
def compute_ari_bootstrap(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    n_iter: int = 30,
    fraction: float = 0.8,
    random_state: int = GRAINE,
) -> pd.Series:
    """Calcule l'ARI par rééchantillonnage.
 
    À chaque itération, on tire une fraction des liaisons et on compare le
    clustering de cet échantillon à la référence (jeu complet) par l'ARI.
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle.
        algorithm: Algorithme de clustering.
        k: Nombre de clusters.
        n_iter: Nombre d'itérations.
        fraction: Part des liaisons tirée à chaque itération.
        random_state: Graine du tirage.
 
    Returns:
        Une série de valeurs d'ARI (une par itération retenue).
    """
    rng = np.random.default_rng(random_state)
    n = x_scaled.shape[0]
    ref = fit_clustering(x_scaled, algorithm, k, random_state=0)
    aris: list[float] = []
    for _ in range(n_iter):
        idx = rng.choice(n, size=int(n * fraction), replace=False)
        sub = x_scaled[idx]
        if sub.shape[0] < k * 2:
            continue
        graine = int(rng.integers(0, 10_000))
        sub_labels = fit_clustering(sub, algorithm, k, random_state=graine)
        aris.append(float(adjusted_rand_score(ref[idx], sub_labels)))
    return pd.Series(aris, name="ari")
 
 
def permutation_test(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    n_permutations: int = 30,
    random_state: int = GRAINE,
) -> dict[str, float]:
    """Vérifie si la structure en clusters dépasse ce que le hasard produirait.
 
    Mélange chaque colonne séparément (garde les distributions, détruit les
    liens entre indicateurs) et compare la silhouette observée à celles de ces
    jeux « nuls ».
 
    Args:
        x_scaled: Matrice d'indicateurs mise à l'échelle.
        algorithm: Algorithme de clustering.
        k: Nombre de clusters.
        n_permutations: Nombre de jeux nuls à générer.
        random_state: Graine du tirage.
 
    Returns:
        Un dict avec les clés : observed_silhouette, max_null_silhouette, p_value.
    """
    rng = np.random.default_rng(random_state)
    obs_labels = fit_clustering(x_scaled, algorithm, k, random_state=0)
    observed = float(silhouette_score(x_scaled, obs_labels))
 
    null_scores: list[float] = []
    for _ in range(n_permutations):
        x_perm = np.column_stack(
            [rng.permutation(x_scaled[:, c]) for c in range(x_scaled.shape[1])]
        )
        perm_labels = fit_clustering(x_perm, algorithm, k, random_state=0)
        null_scores.append(float(silhouette_score(x_perm, perm_labels)))
 
    null = np.array(null_scores)
    p_value = float((null >= observed).mean()) if null.size > 0 else float("nan")
    return {
        "observed_silhouette": observed,
        "max_null_silhouette": float(null.max()) if null.size > 0 else float("nan"),
        "p_value": p_value,
    }
 
 
def compute_eta2(
    features: pd.DataFrame,
    labels: np.ndarray,
    variables: list[str],
) -> pd.Series:
    """Calcule η² (rapport de corrélation) de chaque variable selon les clusters.
 
    η² = 1 − (variance intra-cluster pondérée) / (variance totale).
    Une valeur proche de 1 signifie que la variable distingue bien les clusters.
 
    Args:
        features: Indicateurs par liaison, dans le même ordre que `labels`.
        labels: Étiquettes entières des clusters (une par ligne de `features`).
        variables: Colonnes de `features` à évaluer.
 
    Returns:
        Une série qui associe chaque variable à son η² (entre 0 et 1).
    """
    result: dict[str, float] = {}
    for var in variables:
        if var not in features.columns:
            continue
        vals = features[var].values.astype(float)
        valid = ~np.isnan(vals)
        if valid.sum() < MIN_LIGNES_VALIDES:
            result[var] = float("nan")
            continue
        v, lbl = vals[valid], labels[valid]
        total_var = float(np.var(v))
        if total_var == 0:
            result[var] = 0.0
            continue
        within = sum(
            float(np.var(v[lbl == c])) * int((lbl == c).sum()) for c in np.unique(lbl)
        )
        result[var] = 1.0 - within / (total_var * int(valid.sum()))
    return pd.Series(result, name="eta2")
 
 
def compare_configurations(
    routes_a: pd.Index,
    labels_a: np.ndarray,
    routes_b: pd.Index,
    labels_b: np.ndarray,
) -> dict[str, object]:
    """Compare deux configurations de clustering sur leurs liaisons communes.
 
    L'ARI ne dépend pas de la numérotation des clusters. Le nombre de liaisons
    qui changent de cluster aligne d'abord les étiquettes par l'algorithme
    hongrois (association qui maximise les liaisons en commun).
 
    Args:
        routes_a: Liaisons de la configuration A.
        labels_a: Étiquettes de la configuration A.
        routes_b: Liaisons de la configuration B.
        labels_b: Étiquettes de la configuration B.
 
    Returns:
        Un dict avec les clés : ari (float), n_common (int), n_changed (int),
        changed_routes (list[str]).
    """
    common = routes_a.intersection(routes_b)
    if len(common) < _MIN_LIAISONS_COMMUNES:
        return {
            "ari": float("nan"),
            "n_common": 0,
            "n_changed": 0,
            "changed_routes": [],
        }
 
    la = pd.Series(labels_a, index=routes_a).loc[common].values
    lb = pd.Series(labels_b, index=routes_b).loc[common].values
    ari = float(adjusted_rand_score(la, lb))
 
    contingency = np.zeros((int(la.max()) + 1, int(lb.max()) + 1), dtype=int)
    np.add.at(contingency, (la, lb), 1)
    lignes, colonnes = linear_sum_assignment(-contingency)
    label_map = {int(b): int(a) for a, b in zip(lignes, colonnes, strict=True)}
    lb_aligned = np.array([label_map.get(int(b), int(b)) for b in lb])
 
    changed_mask = la != lb_aligned
    return {
        "ari": ari,
        "n_common": int(len(common)),
        "n_changed": int(changed_mask.sum()),
        "changed_routes": list(common[changed_mask]),
    }