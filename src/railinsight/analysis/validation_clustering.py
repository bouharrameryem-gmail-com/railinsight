"""Validation du clustering : stabilité, qualité et comparaison des configurations."""

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score

from railinsight.analysis.clustering import GRAINE, Algorithme, entrainer_clustering
from railinsight.analysis.indicateurs_liaisons import MIN_LIGNES_VALIDES

_MIN_LIAISONS_COMMUNES = 2


def _inertie(x_scaled: np.ndarray, labels: np.ndarray) -> float:
    """Calcule la somme des carrés des distances aux centres des clusters."""
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
    """Calcule les scores de silhouette,
    Davies-Bouldin et l'inertie pour plusieurs k."""
    lignes = []
    for k in k_range:
        labels = entrainer_clustering(x_scaled, algorithm, k, random_state=random_state)
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
    """Évalue la stabilité du clustering selon différentes graines aléatoires.

    La solution obtenue avec la graine 0 sert de référence.
    """
    ref = entrainer_clustering(x_scaled, algorithm, k, random_state=0)
    aris = [
        float(
            adjusted_rand_score(
                ref, entrainer_clustering(x_scaled, algorithm, k, random_state=graine)
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
    """Évalue la stabilité du clustering par rééchantillonnage.

    Chaque échantillon est comparé à la solution obtenue sur le jeu complet
    à l'aide de l'ARI.
    """
    rng = np.random.default_rng(random_state)
    n = x_scaled.shape[0]
    ref = entrainer_clustering(x_scaled, algorithm, k, random_state=0)
    aris: list[float] = []
    for _ in range(n_iter):
        idx = rng.choice(n, size=int(n * fraction), replace=False)
        sub = x_scaled[idx]
        if sub.shape[0] < k * 2:
            continue
        graine = int(rng.integers(0, 10_000))
        sub_labels = entrainer_clustering(sub, algorithm, k, random_state=graine)
        aris.append(float(adjusted_rand_score(ref[idx], sub_labels)))
    return pd.Series(aris, name="ari")


def permutation_test(
    x_scaled: np.ndarray,
    algorithm: Algorithme,
    k: int,
    n_permutations: int = 30,
    random_state: int = GRAINE,
) -> dict[str, float]:
    """Compare la silhouette observée à celles obtenues sur des données permutées.

    Chaque colonne est mélangée indépendamment afin de conserver sa distribution
    tout en détruisant les relations entre variables.
    """
    rng = np.random.default_rng(random_state)
    obs_labels = entrainer_clustering(x_scaled, algorithm, k, random_state=0)
    observed = float(silhouette_score(x_scaled, obs_labels))

    null_scores: list[float] = []
    for _ in range(n_permutations):
        x_perm = np.column_stack(
            [rng.permutation(x_scaled[:, c]) for c in range(x_scaled.shape[1])]
        )
        perm_labels = entrainer_clustering(x_perm, algorithm, k, random_state=0)
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
    """Calcule le rapport de corrélation η² de chaque variable selon les clusters.

    η² mesure la part de variance expliquée par les clusters. Une valeur proche
    de 1 indique une forte différenciation entre clusters.
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
    """Compare deux clusterings sur leurs liaisons communes.

    Les étiquettes sont alignées par l'algorithme hongrois pour compter les
    changements d'affectation. L'ARI est calculé indépendamment de cet alignement.
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
