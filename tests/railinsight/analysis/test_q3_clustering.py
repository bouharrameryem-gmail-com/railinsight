"""Tests for Q3 clustering analysis functions."""

import numpy as np
import pandas as pd
import pytest

from railinsight.adapters.fake_data_provider import FakeDataProvider
from railinsight.analysis.q3_clustering import (
    ALL_FEATURE_COLS,
    FEATURE_SETS,
    adjust_for_duration,
    auto_select_k,
    build_q3_features,
    compare_configurations,
    compute_eta2,
    detect_redundancy,
    fit_clustering,
    permutation_test,
    scale_features,
    silhouette_curve,
)
from railinsight.exceptions import InsufficientDataError

_provider = FakeDataProvider(seed=42)


@pytest.fixture(scope="module")
def monthly():
    return _provider.load_clean_monthly()


@pytest.fixture(scope="module")
def network():
    return _provider.load_network_monthly()


@pytest.fixture(scope="module")
def features(monthly, network):
    return build_q3_features(monthly, network, exclusion="known", min_months=1)


# ---------------------------------------------------------------------------
# build_q3_features
# ---------------------------------------------------------------------------


class TestBuildQ3Features:
    def test_returns_dataframe(self, monthly, network):
        df = build_q3_features(monthly, network, exclusion="none", min_months=1)
        assert isinstance(df, pd.DataFrame)

    def test_index_is_route(self, features):
        assert features.index.name == "route"

    def test_all_feature_cols_present(self, features):
        for col in ALL_FEATURE_COLS:
            assert col in features.columns, f"Missing column: {col}"

    def test_exclusion_known_reduces_months(self, monthly, network):
        df_none = build_q3_features(monthly, network, exclusion="none", min_months=1)
        df_known = build_q3_features(monthly, network, exclusion="known", min_months=1)
        # known exclusion may reduce some months, but structure is preserved
        assert len(df_none) >= len(df_known) or len(df_none) == len(df_known)

    def test_min_months_filters_routes(self, monthly, network):
        df_low = build_q3_features(monthly, network, exclusion="none", min_months=1)
        df_high = build_q3_features(monthly, network, exclusion="none", min_months=50)
        assert len(df_high) <= len(df_low)

    def test_raises_insufficient_data(self, monthly, network):
        with pytest.raises(InsufficientDataError):
            build_q3_features(monthly, network, exclusion="none", min_months=9999)

    def test_rates_in_valid_range(self, features):
        for col in ["cancellation_rate", "late15_rate", "severe_share"]:
            valid = features[col].dropna()
            assert (valid >= 0).all(), f"{col} has negative values"
            assert (valid <= 1.01).all(), f"{col} has values > 1"


# ---------------------------------------------------------------------------
# adjust_for_duration
# ---------------------------------------------------------------------------


class TestAdjustForDuration:
    def test_adds_adj_columns(self, features):
        adjusted, slopes = adjust_for_duration(features, FEATURE_SETS["v3"])
        # At least some columns should have been adjusted (depends on data)
        adj_cols = [c for c in adjusted.columns if c.endswith("_adj")]
        assert isinstance(slopes, dict)
        assert len(adj_cols) == len(slopes)

    def test_original_cols_unchanged(self, features):
        adjusted, _ = adjust_for_duration(features, FEATURE_SETS["v3"])
        for col in FEATURE_SETS["v3"]:
            if col in features.columns:
                pd.testing.assert_series_equal(adjusted[col], features[col])

    def test_missing_col_skipped(self, features):
        # Should not raise if a column is not in features
        adjusted, slopes = adjust_for_duration(features, ["nonexistent_col"])
        assert "nonexistent_col_adj" not in adjusted.columns
        assert len(slopes) == 0


# ---------------------------------------------------------------------------
# detect_redundancy
# ---------------------------------------------------------------------------


class TestDetectRedundancy:
    def test_returns_list(self, features):
        result = detect_redundancy(features, FEATURE_SETS["v3"])
        assert isinstance(result, list)

    def test_each_entry_is_triple(self, features):
        result = detect_redundancy(features, ALL_FEATURE_COLS)
        for item in result:
            assert len(item) == 3
            col_a, col_b, rho = item
            assert isinstance(col_a, str)
            assert isinstance(col_b, str)
            assert -1.0 <= rho <= 1.0

    def test_threshold_respected(self, features):
        threshold = 0.85
        result = detect_redundancy(features, ALL_FEATURE_COLS, threshold=threshold)
        for _, _, rho in result:
            assert abs(rho) > threshold


# ---------------------------------------------------------------------------
# scale_features
# ---------------------------------------------------------------------------


class TestScaleFeatures:
    def test_power_scaler(self, features):
        x_df = features[FEATURE_SETS["v3"]].dropna()
        x_scaled, scaler = scale_features(x_df, "power")
        assert x_scaled.shape == (len(x_df), len(FEATURE_SETS["v3"]))
        assert abs(x_scaled.mean()) < 0.5  # roughly centered

    def test_standard_scaler(self, features):
        x_df = features[FEATURE_SETS["v3"]].dropna()
        x_scaled, _ = scale_features(x_df, "standard")
        assert x_scaled.shape[1] == len(FEATURE_SETS["v3"])

    def test_inverse_transform(self, features):
        x_df = features[FEATURE_SETS["v3"]].dropna()
        x_scaled, scaler = scale_features(x_df, "power")
        reconstructed = scaler.inverse_transform(x_scaled)
        assert reconstructed.shape == x_scaled.shape


# ---------------------------------------------------------------------------
# fit_clustering
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def x_scaled(features):
    x_df = features[FEATURE_SETS["v3"]].dropna()
    x, _ = scale_features(x_df)
    return x


class TestFitClustering:
    def test_kmeans_returns_labels(self, x_scaled):
        labels = fit_clustering(x_scaled, "kmeans", k=2)
        assert len(labels) == x_scaled.shape[0]
        assert set(labels).issubset({0, 1})

    def test_ward_returns_labels(self, x_scaled):
        labels = fit_clustering(x_scaled, "ward", k=3)
        assert len(set(labels)) == 3

    def test_gmm_returns_labels(self, x_scaled):
        labels = fit_clustering(x_scaled, "gmm", k=2)
        assert len(labels) == x_scaled.shape[0]

    def test_invalid_algorithm_raises(self, x_scaled):
        with pytest.raises(ValueError, match="Unknown algorithm"):
            fit_clustering(x_scaled, "invalid", k=2)  # type: ignore[arg-type]

    def test_reproducible_with_same_seed(self, x_scaled):
        a = fit_clustering(x_scaled, "kmeans", k=2, random_state=0)
        b = fit_clustering(x_scaled, "kmeans", k=2, random_state=0)
        np.testing.assert_array_equal(a, b)


# ---------------------------------------------------------------------------
# auto_select_k
# ---------------------------------------------------------------------------


class TestAutoSelectK:
    def test_returns_int_in_range(self, x_scaled):
        k = auto_select_k(x_scaled, "kmeans", k_range=range(2, 5))
        assert 2 <= k <= 4

    def test_min_cluster_size_respected(self, x_scaled):
        k = auto_select_k(x_scaled, "kmeans", k_range=range(2, 5), min_cluster_size=2)
        labels = fit_clustering(x_scaled, "kmeans", k=k)
        assert np.bincount(labels).min() >= 2


# ---------------------------------------------------------------------------
# silhouette_curve
# ---------------------------------------------------------------------------


class TestSilhouetteCurve:
    def test_shape(self, x_scaled):
        curve = silhouette_curve(x_scaled, "kmeans", k_range=range(2, 5))
        assert len(curve) == 3
        assert "silhouette" in curve.columns
        assert "davies_bouldin" in curve.columns
        assert "min_cluster_size" in curve.columns


# ---------------------------------------------------------------------------
# compute_eta2
# ---------------------------------------------------------------------------


class TestComputeEta2:
    def test_values_in_range(self, features, x_scaled):
        labels = fit_clustering(x_scaled, "kmeans", k=2)
        x_df = features[FEATURE_SETS["v3"]].dropna()
        aligned = features.loc[x_df.index]
        eta2 = compute_eta2(aligned, labels, FEATURE_SETS["v3"])
        valid = eta2.dropna()
        assert (valid >= 0).all()
        assert (valid <= 1.01).all()


# ---------------------------------------------------------------------------
# compare_configurations
# ---------------------------------------------------------------------------


class TestCompareConfigurations:
    def test_same_config_ari_is_one(self, x_scaled):
        labels = fit_clustering(x_scaled, "kmeans", k=2)
        routes = pd.Index([f"r{i}" for i in range(len(labels))])
        result = compare_configurations(routes, labels, routes, labels)
        assert abs(result["ari"] - 1.0) < 1e-6
        assert result["n_changed"] == 0

    def test_no_common_routes(self):
        routes_a = pd.Index(["A", "B"])
        routes_b = pd.Index(["C", "D"])
        result = compare_configurations(
            routes_a, np.array([0, 1]), routes_b, np.array([0, 1])
        )
        assert result["n_common"] == 0
        assert np.isnan(result["ari"])


# ---------------------------------------------------------------------------
# permutation_test
# ---------------------------------------------------------------------------


class TestPermutationTest:
    def test_returns_expected_keys(self, x_scaled):
        result = permutation_test(x_scaled, "kmeans", k=2, n_permutations=3)
        assert "observed_silhouette" in result
        assert "max_null_silhouette" in result
        assert "p_value" in result

    def test_p_value_in_range(self, x_scaled):
        result = permutation_test(x_scaled, "kmeans", k=2, n_permutations=3)
        assert 0.0 <= result["p_value"] <= 1.0
