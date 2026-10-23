"""Production backend adapter.

PROVISIONAL: delegates every call to FakeDataProvider until the real backend
(src/railinsight/backend/ and src/railinsight/analysis/) is implemented.

How to replace this with the real backend:
  1. Implement the functions in src/railinsight/backend/.
  2. Replace each method body with the real call, e.g.:
       from railinsight.backend.loaders import load_clean_monthly as _load
       def load_clean_monthly(self) -> pd.DataFrame:
           return _load()
  3. Remove the FakeDataProvider import once all methods are wired.

The pages never import this file directly: they go through providers.get_provider(),
which returns a DataProvider. So swapping the backend is a one-file change.
"""

from __future__ import annotations

import logging
from typing import Literal

import pandas as pd

from railinsight.adapters.fake_data_provider import FakeDataProvider

logger = logging.getLogger(__name__)

_fake = FakeDataProvider()


class BackendAdapter:
    """Bridges the DataProvider interface to the backend implementation.

    PROVISIONAL: all methods currently delegate to FakeDataProvider.
    """

    def load_clean_monthly(self) -> pd.DataFrame:
        """Load cleaned monthly data."""
        logger.warning("BackendAdapter: using fake data — load_clean_monthly")
        return _fake.load_clean_monthly()

    def load_network_monthly(self) -> pd.DataFrame:
        """Load monthly network-level aggregates."""
        logger.warning("BackendAdapter: using fake data — load_network_monthly")
        return _fake.load_network_monthly()

    def load_quality_report(self) -> dict:
        """Load the pipeline quality report."""
        logger.warning("BackendAdapter: using fake data — load_quality_report")
        return _fake.load_quality_report()

    def load_known_events(self) -> pd.DataFrame:
        """Load documented exceptional months."""
        logger.warning("BackendAdapter: using fake data — load_known_events")
        return _fake.load_known_events()

    def compute_route_features(
        self,
        data: pd.DataFrame,
        exclusion: Literal["none", "known", "data"] = "known",
        min_months: int = 24,
        adjust_duration: bool = False,
    ) -> pd.DataFrame:
        """Compute per-route aggregate indicators."""
        logger.warning("BackendAdapter: using fake data — compute_route_features")
        return _fake.compute_route_features(
            data=data,
            exclusion=exclusion,
            min_months=min_months,
            adjust_duration=adjust_duration,
        )
