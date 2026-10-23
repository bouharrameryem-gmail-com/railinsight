"""Shared pytest fixtures for RailInsight tests."""

import pytest

from railinsight.adapters.fake_data_provider import FakeDataProvider


@pytest.fixture(scope="session")
def fake_provider() -> FakeDataProvider:
    """A FakeDataProvider instance shared across the test session (fast)."""
    return FakeDataProvider(seed=42)


@pytest.fixture(scope="session")
def clean_monthly_df(fake_provider: FakeDataProvider):
    """The full synthetic monthly DataFrame."""
    return fake_provider.load_clean_monthly()


@pytest.fixture(scope="session")
def route_features_df(fake_provider: FakeDataProvider):
    """Per-route features computed from the synthetic monthly data."""
    return fake_provider.compute_route_features(
        fake_provider.load_clean_monthly(),
        exclusion="known",
        min_months=12,
    )
