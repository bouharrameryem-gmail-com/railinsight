"""Production backend adapter.

Each method must eventually be wired to a real backend function.
Until then, raise NotImplementedError — pages catch these via try/except.
The pages never import this file directly: they use providers.get_provider().
"""

from __future__ import annotations

from typing import Literal

import pandas as pd


class BackendAdapter:
    """Bridges the DataProvider interface to the real backend."""

    def load_clean_monthly(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_network_monthly(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_quality_report(self) -> dict:
        raise NotImplementedError

    def load_known_events(self) -> pd.DataFrame:
        raise NotImplementedError

    def compute_route_features(
        self,
        data: pd.DataFrame,
        exclusion: Literal["none", "known", "data"] = "known",
        min_months: int = 24,
        adjust_duration: bool = False,
    ) -> pd.DataFrame:
        raise NotImplementedError
