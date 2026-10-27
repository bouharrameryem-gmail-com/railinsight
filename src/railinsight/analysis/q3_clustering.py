"""Q3 punctuality-profile clustering: feature engineering, clustering, validation.

PROVISIONAL: reviewed once the backend pipeline exports processed Parquet files.
All functions are pure — no Streamlit calls, no file I/O.

Usage:
    features = build_q3_features(monthly_df, network_df)
    x_df = features[FEATURE_SETS["v3"]].dropna()
    x_scaled, scaler = scale_features(x_df)
    k = auto_select_k(x_scaled, algorithm="kmeans")
    labels = fit_clustering(x_scaled, algorithm="kmeans", k=k)
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import PowerTransformer, StandardScaler

from railinsight.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_SETS: dict[str, list[str]] = {
    "v3": [
        "cancellation_rate",
        "late15_rate",
        "severe_share",
        "extreme_share",
        "volatility_cv",
    ],
    "fixed": [
        "cancellation_rate",
        "late15_rate",
        "severe_share",
        "volatility",
        "chronicity",
    ],
    "composite": [
        "cancellation_rate",
        "late_arrival_rate",
        "mean_delay_when_late",
        "severe_ratio",
        "irregularity",
    ],
}

ALL_FEATURE_COLS: list[str] = sorted(
    {col for cols in FEATURE_SETS.values() for col in cols}
    | {"late30_rate", "late60_rate"}
)

_KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "2018-04",
        "2018-05",
        "2019-12",
        "2020-01",
        "2020-03",
        "2020-04",
        "2020-05",
        "2020-11",
        "2021-04",
    }
)

_MIN_VALID_ROWS: int = 5
_DURATION_CORR_THRESHOLD: float = 0.3
_REDUNDANCY_THRESHOLD: float = 0.85


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------


def _excluded_months(
    network: pd.DataFrame,
    exclusion: Literal["none", "known", "data"],
) -> frozenset[str]:
    """Return the set of YYYY-MM strings to exclude from monthly aggregation."""
    if exclusion == "none":
        return frozenset()
    if exclusion == "known":
        return _KNOWN_EVENTS
    # "data": detect outlier months via IQR on network late15_rate
    rates = network["late15_rate"]
    q1 = float(rates.quantile(0.25))
    q3 = float(rates.quantile(0.75))
    cutoff = q3 + 1.5 * (q3 - q1)
    month_strs = network["date"].astype(str).str[:7]
    return frozenset(month_strs[rates > cutoff])


def build_q3_features(
    monthly: pd.DataFrame,
    network: pd.DataFrame,
    exclusion: Literal["none", "known", "data"] = "known",
    min_months: int = 24,
) -> pd.DataFrame:
    """Compute the route-level feature matrix for Q3 clustering.

    Args:
        monthly: Clean monthly DataFrame from DataProvider.load_clean_monthly().
            Required columns: date, route, trains_planned, trains_cancelled,
            trains_run, late15_trains, late30_trains, late60_trains,
            late_arrival_trains, trip_duration_min, mean_delay_when_late.
        network: Monthly network DataFrame from DataProvider.load_network_monthly().
            Required columns: date, late15_rate.
        exclusion: Month exclusion rule.
        min_months: Minimum valid months per route to include it.

    Returns:
        DataFrame indexed by route with all Q3 feature columns.

    Raises:
        InsufficientDataError: if fewer than 2 routes pass the min_months filter.
    """
    excluded = _excluded_months(network, exclusion)
    month_strs = monthly["date"].astype(str).str[:7]
    df = monthly[~month_strs.isin(excluded)].copy()

    net_map = (
        network.assign(month_str=network["date"].astype(str).str[:7])
        .set_index("month_str")["late15_rate"]
    )

    rows: list[dict] = []
    for route, grp in df.groupby("route"):
        if len(grp) < min_months:
            continue

        tp = grp["trains_planned"].sum()
        tc = grp["trains_cancelled"].sum()
        tr = grp["trains_run"].sum()
        l15 = grp["late15_trains"].sum()
        l30 = grp["late30_trains"].sum()
        l60 = grp["late60_trains"].sum()
        la = grp["late_arrival_trains"].sum()

        monthly_l15 = grp["late15_trains"] / grp["trains_run"].clip(lower=1)
        monthly_la = grp["late_arrival_trains"] / grp["trains_run"].clip(lower=1)

        grp_month_strs = grp["date"].astype(str).str[:7]
        net_vals = grp_month_strs.map(net_map).values
        chronicity_val = float(np.nanmean(monthly_l15.values > net_vals))

        delay_weighted = (
            float(
                (grp["mean_delay_when_late"] * grp["late_arrival_trains"]).sum() / la
            )
            if la > 0
            else 0.0
        )
        rows.append(
            {
                "route": route,
                "n_months": len(grp),
                "trip_duration_min": int(grp["trip_duration_min"].median()),
                "cancellation_rate": tc / tp if tp > 0 else float("nan"),
                "late15_rate": l15 / tr if tr > 0 else float("nan"),
                "late30_rate": l30 / tr if tr > 0 else float("nan"),
                "late60_rate": l60 / tr if tr > 0 else float("nan"),
                "severe_share": l30 / l15 if l15 > 0 else float("nan"),
                "extreme_share": l60 / l15 if l15 > 0 else float("nan"),
                "late_arrival_rate": la / tr if tr > 0 else float("nan"),
                "mean_delay_when_late": delay_weighted,
                "volatility": float(monthly_l15.std()),
                "volatility_cv": float(monthly_l15.std() / monthly_l15.mean())
                if monthly_l15.mean() > 0
                else float("nan"),
                "severe_ratio": l30 / la if la > 0 else float("nan"),
                "irregularity": float(monthly_la.std()),
                "chronicity": chronicity_val,
            }
        )

    if len(rows) < 2:  # noqa: PLR2004
        raise InsufficientDataError(
            f"Seulement {len(rows)} liaison(s) ont ≥ {min_months} mois valides. "
            "Réduisez le seuil minimum ou changez la règle d'exclusion."
        )
    return pd.DataFrame(rows).set_index("route")


def adjust_for_duration(
    features: pd.DataFrame,
    cols: list[str],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Add duration-adjusted variants of features correlated with trip duration.

    For each column in cols, checks |Spearman ρ| with log(trip_duration_min).
    If ρ > 0.3, adds a {col}_adj column that removes the linear trend on
    log-duration, re-centered at the network mean log-duration.

    Args:
        features: Route-level feature DataFrame (from build_q3_features).
        cols: Feature columns to potentially adjust.

    Returns:
        Tuple of (DataFrame with optional _adj columns, dict slope per adjusted col).
    """
    result = features.copy()
    log_dur = np.log(features["trip_duration_min"].clip(lower=1))
    mean_log_dur = float(log_dur.mean())
    slopes: dict[str, float] = {}

    for col in cols:
        if col not in features.columns:
            continue
        valid = features[col].notna() & log_dur.notna()
        if valid.sum() < _MIN_VALID_ROWS:
            continue
        rho, _ = spearmanr(log_dur[valid], features.loc[valid, col])
        if abs(float(rho)) < _DURATION_CORR_THRESHOLD:
            continue
        slope = float(
            np.polyfit(log_dur[valid], features.loc[valid, col], 1)[0]
        )
        slopes[col] = slope
        result[f"{col}_adj"] = features[col] - slope * (log_dur - mean_log_dur)
        logger.debug(
            "Adjusted %s for duration (ρ=%.2f, slope=%.4f)", col, rho, slope
        )

    return result, slopes


def detect_redundancy(
    features: pd.DataFrame,
    cols: list[str],
    threshold: float = _REDUNDANCY_THRESHOLD,
) -> list[tuple[str, str, float]]:
    """Detect pairs of features with |Spearman ρ| > threshold.

    Args:
        features: Route-level feature DataFrame.
        cols: Feature columns to check pairwise.
        threshold: Correlation threshold above which a pair is flagged.

    Returns:
        List of (col_a, col_b, rho) tuples for redundant pairs.
    """
    available = [c for c in cols if c in features.columns]
    valid = features[available].dropna()
    if len(valid) < _MIN_VALID_ROWS:
        return []
    redundant: list[tuple[str, str, float]] = []
    for i, col_a in enumerate(available):
        for col_b in available[i + 1 :]:
            rho, _ = spearmanr(valid[col_a], valid[col_b])
            if abs(float(rho)) > threshold:
                redundant.append((col_a, col_b, float(rho)))
    return redundant


# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------


def scale_features(
    features_df: pd.DataFrame,
    scaler_type: Literal["power", "standard"] = "power",
) -> tuple[np.ndarray, PowerTransformer | StandardScaler]:
    """Scale the feature matrix for clustering.

    Args:
        features_df: DataFrame of features with no NaN (rows = routes).
        scaler_type: "power" uses Yeo-Johnson + z-score (reduces skew);
            "standard" uses z-score normalization only.

    Returns:
        Tuple of (scaled ndarray shape (n_routes, n_features), fitted scaler).
    """
    scaler: PowerTransformer | StandardScaler
    if scaler_type == "power":
        scaler = PowerTransformer(method="yeo-johnson", standardize=True)
    else:
        scaler = StandardScaler()
    return scaler.fit_transform(features_df.values), scaler


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def fit_clustering(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k: int,
    *,
    n_init: int = 50,
    covariance_type: Literal["full", "tied", "diag", "spherical"] = "full",
    random_state: int = 42,
) -> np.ndarray:
    """Fit a clustering model and return integer cluster labels.

    Args:
        x_scaled: Scaled feature matrix, shape (n_routes, n_features).
        algorithm: "kmeans", "ward" (agglomerative with Ward linkage), or "gmm".
        k: Number of clusters (or GMM components).
        n_init: Number of K-means random initializations (ignored for ward/gmm).
        covariance_type: GMM covariance matrix type (ignored for kmeans/ward).
        random_state: Random seed for reproducibility.

    Returns:
        Integer array of shape (n_routes,) with labels starting at 0.
    """
    if algorithm == "kmeans":
        return KMeans(
            n_clusters=k, n_init=n_init, random_state=random_state
        ).fit_predict(x_scaled)
    if algorithm == "ward":
        return AgglomerativeClustering(
            n_clusters=k, linkage="ward"
        ).fit_predict(x_scaled)
    if algorithm == "gmm":
        gmm = GaussianMixture(
            n_components=k,
            covariance_type=covariance_type,
            n_init=5,
            random_state=random_state,
        )
        gmm.fit(x_scaled)
        return gmm.predict(x_scaled)
    msg = f"Unknown algorithm: {algorithm!r}. Choose 'kmeans', 'ward', or 'gmm'."
    raise ValueError(msg)


def auto_select_k(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k_range: range = range(2, 9),
    min_cluster_size: int = 3,
    random_state: int = 42,
) -> int:
    """Select k with the best silhouette score subject to a minimum cluster size.

    Args:
        x_scaled: Scaled feature matrix.
        algorithm: Clustering algorithm.
        k_range: Range of k values to try.
        min_cluster_size: Minimum routes per cluster; violating configs are skipped.
        random_state: Random seed.

    Returns:
        Optimal k (falls back to k_range.start if all configs violate the constraint).
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


# ---------------------------------------------------------------------------
# Validation metrics
# ---------------------------------------------------------------------------


def silhouette_curve(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k_range: range = range(2, 9),
    random_state: int = 42,
) -> pd.DataFrame:
    """Compute silhouette and Davies-Bouldin scores for a range of k values.

    Args:
        x_scaled: Scaled feature matrix.
        algorithm: Clustering algorithm.
        k_range: Range of k values to evaluate.
        random_state: Random seed.

    Returns:
        DataFrame with columns: k, silhouette, davies_bouldin, min_cluster_size.
    """
    records = []
    for k in k_range:
        labels = fit_clustering(x_scaled, algorithm, k, random_state=random_state)
        records.append(
            {
                "k": k,
                "silhouette": float(silhouette_score(x_scaled, labels)),
                "davies_bouldin": float(davies_bouldin_score(x_scaled, labels)),
                "min_cluster_size": int(np.bincount(labels).min()),
            }
        )
    return pd.DataFrame(records)


def compute_ari_seeds(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k: int,
    n_seeds: int = 20,
) -> pd.Series:
    """Compute ARI distribution across different random seeds.

    Uses seed 0 as reference. High ARI means the solution is stable.

    Args:
        x_scaled: Scaled feature matrix.
        algorithm: Clustering algorithm.
        k: Number of clusters.
        n_seeds: Number of alternative seeds to test.

    Returns:
        Series of ARI values (one per seed).
    """
    ref = fit_clustering(x_scaled, algorithm, k, random_state=0)
    aris = [
        float(
            adjusted_rand_score(
                ref, fit_clustering(x_scaled, algorithm, k, random_state=s)
            )
        )
        for s in range(1, n_seeds + 1)
    ]
    return pd.Series(aris, name="ari")


def compute_ari_bootstrap(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k: int,
    n_iter: int = 30,
    fraction: float = 0.8,
    random_state: int = 42,
) -> pd.Series:
    """Compute ARI distribution via bootstrap resampling.

    Each iteration samples a fraction of routes and compares the sub-clustering
    to the reference (full dataset) via ARI.

    Args:
        x_scaled: Scaled feature matrix.
        algorithm: Clustering algorithm.
        k: Number of clusters.
        n_iter: Number of bootstrap iterations.
        fraction: Fraction of routes per sample.
        random_state: Seed for the bootstrap sampler.

    Returns:
        Series of ARI values across iterations.
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
        seed = int(rng.integers(0, 10_000))
        sub_labels = fit_clustering(sub, algorithm, k, random_state=seed)
        aris.append(float(adjusted_rand_score(ref[idx], sub_labels)))
    return pd.Series(aris, name="ari")


def permutation_test(
    x_scaled: np.ndarray,
    algorithm: Literal["kmeans", "ward", "gmm"],
    k: int,
    n_permutations: int = 30,
    random_state: int = 42,
) -> dict[str, float]:
    """Assess whether clustering structure exceeds chance level.

    Shuffles each column independently (preserves marginal distributions,
    destroys between-variable covariance) and compares the observed silhouette
    to the null distribution.

    Args:
        x_scaled: Scaled feature matrix.
        algorithm: Clustering algorithm.
        k: Number of clusters.
        n_permutations: Number of null datasets to generate.
        random_state: Seed for the permutation sampler.

    Returns:
        Dict with keys: observed_silhouette, max_null_silhouette, p_value.
    """
    rng = np.random.default_rng(random_state)
    obs_labels = fit_clustering(x_scaled, algorithm, k, random_state=0)
    observed = float(silhouette_score(x_scaled, obs_labels))

    null_scores: list[float] = []
    for _ in range(n_permutations):
        x_perm = np.column_stack(  # noqa: N806
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
    """Compute η² (correlation ratio) for each variable given cluster labels.

    η² = 1 − (weighted within-cluster variance) / (total variance).
    A value close to 1 means the variable discriminates clusters well.

    Args:
        features: Route-level feature DataFrame aligned with labels.
        labels: Integer cluster labels (same order as features rows).
        variables: Columns of features to evaluate.

    Returns:
        Series mapping variable name to η² (0 to 1).
    """
    result: dict[str, float] = {}
    for var in variables:
        if var not in features.columns:
            continue
        vals = features[var].values.astype(float)
        valid = ~np.isnan(vals)
        if valid.sum() < _MIN_VALID_ROWS:
            result[var] = float("nan")
            continue
        v, lbl = vals[valid], labels[valid]
        total_var = float(np.var(v))
        if total_var == 0:
            result[var] = 0.0
            continue
        within = sum(
            float(np.var(v[lbl == c])) * int((lbl == c).sum())
            for c in np.unique(lbl)
        )
        result[var] = 1.0 - within / (total_var * int(valid.sum()))
    return pd.Series(result, name="eta2")


def compare_configurations(
    routes_a: pd.Index,
    labels_a: np.ndarray,
    routes_b: pd.Index,
    labels_b: np.ndarray,
) -> dict[str, object]:
    """Compare two clustering configurations on their common routes.

    ARI is label-permutation invariant. The changed-routes count uses a
    majority-vote label alignment via the Hungarian algorithm.

    Args:
        routes_a: Route index for configuration A.
        labels_a: Labels for configuration A.
        routes_b: Route index for configuration B.
        labels_b: Labels for configuration B.

    Returns:
        Dict with keys: ari (float), n_common (int), n_changed (int),
        changed_routes (list[str]).
    """
    common = routes_a.intersection(routes_b)
    if len(common) < 2:  # noqa: PLR2004
        return {
            "ari": float("nan"),
            "n_common": 0,
            "n_changed": 0,
            "changed_routes": [],
        }

    la = pd.Series(labels_a, index=routes_a).loc[common].values
    lb = pd.Series(labels_b, index=routes_b).loc[common].values
    ari = float(adjusted_rand_score(la, lb))

    k_a = int(la.max()) + 1
    k_b = int(lb.max()) + 1
    contingency = np.zeros((k_a, k_b), dtype=int)
    for ai, bi in zip(la, lb, strict=True):
        contingency[int(ai), int(bi)] += 1
    row_ind, col_ind = linear_sum_assignment(-contingency)
    label_map = {int(col_ind[i]): int(row_ind[i]) for i in range(len(row_ind))}
    lb_aligned = np.array([label_map.get(int(b), int(b)) for b in lb])

    changed_mask = la != lb_aligned
    changed_routes = list(common[changed_mask])
    return {
        "ari": ari,
        "n_common": int(len(common)),
        "n_changed": int(changed_mask.sum()),
        "changed_routes": changed_routes,
    }
