"""Tests for FakeDataProvider — validates the synthetic data contract."""

import pandas as pd
import pytest

from railinsight.adapters.fake_data_provider import FakeDataProvider


@pytest.fixture(scope="module")
def provider() -> FakeDataProvider:
    return FakeDataProvider(seed=0)


class TestLoadCleanMonthly:
    def test_returns_dataframe(self, provider):
        df = provider.load_clean_monthly()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, provider):
        df = provider.load_clean_monthly()
        required = {
            "date",
            "route",
            "departure",
            "arrival",
            "trains_planned",
            "trains_cancelled",
            "trains_run",
            "late15_trains",
            "late30_trains",
            "late60_trains",
            "late_arrival_trains",
            "trip_duration_min",
            "is_exceptional",
            "event_type",
            "mean_delay_when_late",
        }
        assert required.issubset(df.columns)

    def test_no_negative_counts(self, provider):
        df = provider.load_clean_monthly()
        for col in [
            "trains_planned",
            "trains_cancelled",
            "trains_run",
            "late15_trains",
            "late30_trains",
            "late60_trains",
        ]:
            assert (df[col] >= 0).all(), f"Negative values in {col}"

    def test_cancelled_le_planned(self, provider):
        df = provider.load_clean_monthly()
        assert (df["trains_cancelled"] <= df["trains_planned"]).all()

    def test_trains_run_equals_planned_minus_cancelled(self, provider):
        df = provider.load_clean_monthly()
        assert (df["trains_run"] == df["trains_planned"] - df["trains_cancelled"]).all()

    def test_date_column_is_period(self, provider):
        df = provider.load_clean_monthly()
        assert hasattr(df["date"].dtype, "freq")

    def test_cached_call_returns_same_object(self, provider):
        df1 = provider.load_clean_monthly()
        df2 = provider.load_clean_monthly()
        assert df1 is df2


class TestLoadNetworkMonthly:
    def test_has_rate_columns(self, provider):
        df = provider.load_network_monthly()
        expected = ["cancellation_rate", "late15_rate", "late30_rate", "is_exceptional"]
        for col in expected:
            assert col in df.columns

    def test_rates_between_0_and_1(self, provider):
        df = provider.load_network_monthly()
        for col in ["cancellation_rate", "late15_rate", "late30_rate", "late60_rate"]:
            assert (df[col] >= 0).all() and (df[col] <= 1).all()


class TestLoadQualityReport:
    def test_returns_dict(self, provider):
        report = provider.load_quality_report()
        assert isinstance(report, dict)

    def test_has_expected_keys(self, provider):
        report = provider.load_quality_report()
        for key in ["pipeline_version", "total_rows_raw", "rows_clean"]:
            assert key in report


class TestComputeRouteFeatures:
    def test_returns_dataframe(self, provider):
        df = provider.compute_route_features(
            provider.load_clean_monthly(), min_months=1
        )
        assert isinstance(df, pd.DataFrame)

    def test_has_indicator_columns(self, provider):
        df = provider.compute_route_features(
            provider.load_clean_monthly(), min_months=1
        )
        for col in ["late15_rate", "severe_share", "volatility", "cancellation_rate"]:
            assert col in df.columns

    def test_min_months_filter(self, provider):
        df_strict = provider.compute_route_features(
            provider.load_clean_monthly(), min_months=90
        )
        df_loose = provider.compute_route_features(
            provider.load_clean_monthly(), min_months=1
        )
        assert len(df_strict) <= len(df_loose)

    def test_adjust_duration_adds_adj_columns(self, provider):
        df = provider.compute_route_features(
            provider.load_clean_monthly(),
            min_months=1,
            adjust_duration=True,
        )
        assert "late15_rate_adj" in df.columns

    def test_exclusion_known_reduces_rows_used(self, provider):
        df_none = provider.compute_route_features(
            provider.load_clean_monthly(),
            exclusion="none",
            min_months=1,
        )
        df_known = provider.compute_route_features(
            provider.load_clean_monthly(),
            exclusion="known",
            min_months=1,
        )
        # With known exclusion, n_months per route should be lower
        assert df_known["n_months"].mean() <= df_none["n_months"].mean()
