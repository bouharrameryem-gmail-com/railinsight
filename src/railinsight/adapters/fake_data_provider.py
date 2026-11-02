"""Synthetic data provider for frontend development and tests.

Generates structurally valid DataFrames that mimic the real backend output.
No external files are read: useful when the backend is not yet implemented,
and as pytest fixtures.

Sizes are intentionally small (20 routes × ~93 months) so tests stay fast.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

# 20 real-sounding routes (subset of the actual dataset)
_ROUTES = [
    ("PARIS LYON", "MARSEILLE ST CHARLES"),
    ("PARIS MONTPARNASSE", "BORDEAUX ST JEAN"),
    ("PARIS GARE DE LYON", "LYON PART DIEU"),
    ("PARIS NORD", "LILLE FLANDRES"),
    ("PARIS EST", "STRASBOURG"),
    ("PARIS MONTPARNASSE", "RENNES"),
    ("PARIS GARE DE LYON", "GENÈVE"),
    ("PARIS EST", "METZ VILLE"),
    ("BORDEAUX ST JEAN", "TOULOUSE MATABIAU"),
    ("LYON PART DIEU", "MARSEILLE ST CHARLES"),
    ("PARIS GARE DE LYON", "AVIGNON TGV"),
    ("PARIS MONTPARNASSE", "NANTES"),
    ("PARIS GARE DE LYON", "MONTPELLIER ST ROCH"),
    ("PARIS EST", "REIMS"),
    ("PARIS GARE DE LYON", "GRENOBLE"),
    ("PARIS MONTPARNASSE", "BREST"),
    ("PARIS GARE DE LYON", "NICE VILLE"),
    ("PARIS MONTPARNASSE", "LE MANS"),
    ("PARIS EST", "NANCY VILLE"),
    ("PARIS GARE DE LYON", "VALENCE TGV"),
]

# Documented exceptional months (source: WIKI §4.4)
_KNOWN_EVENTS = [
    ("2018-04", "grève SNCF printemps 2018", "strike"),
    ("2018-05", "grève SNCF printemps 2018", "strike"),
    ("2019-12", "grève retraites", "strike"),
    ("2020-01", "grève retraites", "strike"),
    ("2020-03", "Covid-19 confinement 1", "covid"),
    ("2020-04", "Covid-19 confinement 1", "covid"),
    ("2020-05", "Covid-19 déconfinement progressif", "covid"),
    ("2020-11", "Covid-19 confinement 2", "covid"),
    ("2021-04", "Covid-19 restrictions", "covid"),
]

_EXCEPTIONAL_MONTHS = {e[0] for e in _KNOWN_EVENTS}
_DATES = pd.period_range("2018-01", "2025-09", freq="M")


class FakeDataProvider:
    """Synthetic data provider satisfying the DataProvider protocol.

    Args:
        seed: Random seed for reproducibility.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._clean_monthly: pd.DataFrame | None = None

    def load_clean_monthly(self) -> pd.DataFrame:
        """Generate a synthetic monthly dataset (one row = month × route)."""
        if self._clean_monthly is not None:
            return self._clean_monthly

        records = []
        for departure, arrival in _ROUTES:
            route = f"{departure} → {arrival}"
            base_late15 = float(self._rng.uniform(0.10, 0.45))
            base_severe = float(self._rng.uniform(0.10, 0.35))
            duration = int(self._rng.integers(30, 200))

            for date in _DATES:
                month_key = str(date)[:7]
                is_exc = month_key in _EXCEPTIONAL_MONTHS
                event_type = next(
                    (e[2] for e in _KNOWN_EVENTS if e[0] == month_key), None
                )

                trains_planned = int(self._rng.integers(20, 120))
                cancel_p = 0.30 if is_exc else 0.05
                trains_cancelled = min(
                    int(self._rng.binomial(trains_planned, cancel_p)),
                    trains_planned,
                )
                trains_run = trains_planned - trains_cancelled

                late15_p = base_late15 * (1.5 if is_exc else 1.0)
                late15 = int(self._rng.binomial(trains_run, min(late15_p, 1.0)))
                late30 = int(self._rng.binomial(late15, base_severe))
                late60 = int(self._rng.binomial(late30, 0.30))
                late_arrival = min(
                    late15 + int(self._rng.binomial(trains_run - late15, 0.05)),
                    trains_run,
                )
                mean_delay = (
                    float(self._rng.uniform(5.0, 30.0)) if late_arrival > 0 else 0.0
                )

                records.append(
                    {
                        "date": date,
                        "route": route,
                        "departure": departure,
                        "arrival": arrival,
                        "trains_planned": trains_planned,
                        "trains_cancelled": trains_cancelled,
                        "trains_run": trains_run,
                        "late15_trains": late15,
                        "late30_trains": late30,
                        "late60_trains": late60,
                        "late_arrival_trains": late_arrival,
                        "trip_duration_min": duration,
                        "is_exceptional": is_exc,
                        "event_type": event_type,
                        "mean_delay_when_late": mean_delay,
                    }
                )

        self._clean_monthly = pd.DataFrame(records)
        return self._clean_monthly

    def load_network_monthly(self) -> pd.DataFrame:
        """Generate synthetic monthly network-level indicators."""
        records = []
        for date in _DATES:
            is_exc = str(date)[:7] in _EXCEPTIONAL_MONTHS
            records.append(
                {
                    "date": date,
                    "cancellation_rate": float(
                        self._rng.uniform(0.02, 0.30 if is_exc else 0.08)
                    ),
                    "late15_rate": float(
                        self._rng.uniform(0.15, 0.65 if is_exc else 0.35)
                    ),
                    "late30_rate": float(
                        self._rng.uniform(0.05, 0.30 if is_exc else 0.15)
                    ),
                    "late60_rate": float(
                        self._rng.uniform(0.01, 0.10 if is_exc else 0.05)
                    ),
                    "is_exceptional": is_exc,
                }
            )
        return pd.DataFrame(records)

    def load_quality_report(self) -> dict:
        """Return a minimal quality report dict (fake values)."""
        return {
            "pipeline_version": "provisional-fake",
            "export_date": "2026-10-22",
            "total_rows_raw": 13247,
            "rows_removed": 73,
            "rows_clean": 13174,
            "violations": {"R01": 73, "R02": 43, "R06": 3, "R07": 354},
            "decisions_applied": {"D2": 73, "D1": 43, "D4bis": 354},
        }

    def load_known_events(self) -> pd.DataFrame:
        """Return the table of documented exceptional months."""
        return pd.DataFrame(_KNOWN_EVENTS, columns=["month", "event", "type"])

    def compute_route_features(
        self,
        data: pd.DataFrame,
        exclusion: Literal["none", "known", "data"] = "known",
        min_months: int = 24,
        adjust_duration: bool = False,
    ) -> pd.DataFrame:
        """Compute per-route aggregate indicators from monthly data.

        Mirrors the logic specified in WIKI §5.2 (ratio-of-sums rule).

        Args:
            data: Cleaned monthly DataFrame (from load_clean_monthly).
            exclusion: Monthly exclusion rule.
            min_months: Minimum months required to include a route.
            adjust_duration: Whether to add duration-adjusted _adj columns.

        Returns:
            One row per eligible route.
        """
        df = data.copy()

        if exclusion == "known":
            df = df[~df["date"].astype(str).str[:7].isin(_EXCEPTIONAL_MONTHS)]

        rows = []
        for route, grp in df.groupby("route"):
            if len(grp) < min_months:
                continue

            total_run = grp["trains_run"].sum()
            total_planned = grp["trains_planned"].sum()
            total_l15 = grp["late15_trains"].sum()
            total_l30 = grp["late30_trains"].sum()
            total_l60 = grp["late60_trains"].sum()
            total_late_arr = grp["late_arrival_trains"].sum()

            monthly_rates = grp["late15_trains"] / grp["trains_run"].clip(lower=1)

            rows.append(
                {
                    "route": route,
                    "departure": grp["departure"].iloc[0],
                    "arrival": grp["arrival"].iloc[0],
                    "n_months": len(grp),
                    "trains_run_total": int(total_run),
                    "trip_duration_min": int(grp["trip_duration_min"].median()),
                    "cancellation_rate": (
                        grp["trains_cancelled"].sum() / total_planned
                        if total_planned > 0
                        else float("nan")
                    ),
                    "late15_rate": (
                        total_l15 / total_run if total_run > 0 else float("nan")
                    ),
                    "late30_rate": (
                        total_l30 / total_run if total_run > 0 else float("nan")
                    ),
                    "late60_rate": (
                        total_l60 / total_run if total_run > 0 else float("nan")
                    ),
                    "severe_share": (
                        total_l30 / total_l15 if total_l15 > 0 else float("nan")
                    ),
                    "extreme_share": (
                        total_l60 / total_l15 if total_l15 > 0 else float("nan")
                    ),
                    "volatility": float(monthly_rates.std()),
                    "volatility_cv": (
                        float(monthly_rates.std() / monthly_rates.mean())
                        if monthly_rates.mean() > 0
                        else float("nan")
                    ),
                    "late_arrival_rate": (
                        total_late_arr / total_run if total_run > 0 else float("nan")
                    ),
                    "mean_delay_when_late": (
                        float(
                            (
                                grp["mean_delay_when_late"] * grp["late_arrival_trains"]
                            ).sum()
                            / total_late_arr
                        )
                        if total_late_arr > 0
                        else 0.0
                    ),
                }
            )

        features = pd.DataFrame(rows)
        if features.empty:
            return features

        if adjust_duration:
            features = corriger_effet_duree(features)

        return features


def corriger_effet_duree(features: pd.DataFrame) -> pd.DataFrame:
    """Add _adj columns correcting each rate for trip duration (WIKI §5.3).

    The adjustment removes the linear trend of each indicator on log(duration),
    re-centering at the network mean duration. Interpretation: 'the rate this
    route would have if it were an average-length route.'
    """
    log_dur = np.log(features["trip_duration_min"].clip(lower=1))
    mean_log_dur = log_dur.mean()

    for col in ["late15_rate", "cancellation_rate", "severe_share", "extreme_share"]:
        if col not in features.columns:
            continue
        valid = features[[col]].join(log_dur.rename("log_dur")).dropna()
        if len(valid) < 3:  # noqa: PLR2004
            continue
        slope = float(np.polyfit(valid["log_dur"], valid[col], 1)[0])
        features[f"{col}_adj"] = features[col] - slope * (log_dur - mean_log_dur)

    return features
