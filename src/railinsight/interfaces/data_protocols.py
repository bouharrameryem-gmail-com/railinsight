"""Typing protocols defining the data contract between frontend and backend.

The frontend depends only on these interfaces, never on concrete implementations.
To swap the backend, provide a new class that satisfies these protocols.

Protocol = structural subtyping: any class that has the right methods qualifies,
even without explicit inheritance. This is Python's equivalent of interfaces.
"""

from __future__ import annotations

from typing import Literal, Protocol

import pandas as pd


class CleanMonthlyLoader(Protocol):
    """Loads the cleaned monthly dataset."""

    def load_clean_monthly(self) -> pd.DataFrame:
        """Return cleaned monthly data (one row = month × route × service)."""
        ...


class NetworkMonthlyLoader(Protocol):
    """Loads monthly network-level aggregates."""

    def load_network_monthly(self) -> pd.DataFrame:
        """Return monthly network indicators (cancellation rate, late15_rate…)."""
        ...


class QualityReportLoader(Protocol):
    """Loads the pipeline quality report."""

    def load_quality_report(self) -> dict:
        """Return the quality report produced by the data pipeline."""
        ...


class KnownEventsLoader(Protocol):
    """Loads the list of documented exceptional months."""

    def load_known_events(self) -> pd.DataFrame:
        """Return documented exceptional months (strikes, Covid…)."""
        ...


class RouteFeaturesComputer(Protocol):
    """Computes per-route aggregate punctuality indicators."""

    def compute_route_features(
        self,
        data: pd.DataFrame,
        exclusion: Literal["none", "known", "data"] = "known",
        min_months: int = 24,
        adjust_duration: bool = False,
    ) -> pd.DataFrame:
        """Return one row per eligible route with aggregate indicators.

        Args:
            data: The cleaned monthly DataFrame (output of load_clean_monthly).
            exclusion: Which months to exclude before aggregating.
                "none"  — keep all months.
                "known" — exclude documented exceptional months (default).
                "data"  — exclude months flagged as statistical outliers.
            min_months: Minimum number of valid months for a route to be included.
            adjust_duration: If True, add _adj columns corrected for trip duration.

        Returns:
            DataFrame with one row per route and columns defined in WIKI §5.2.
        """
        ...


class DataProvider(
    CleanMonthlyLoader,
    NetworkMonthlyLoader,
    QualityReportLoader,
    KnownEventsLoader,
    RouteFeaturesComputer,
    Protocol,
):
    """Combined interface: every data need of the frontend in one object."""
