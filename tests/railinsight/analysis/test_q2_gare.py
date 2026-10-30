import pandas as pd
import pytest

from railinsight.analysis.q2_gares import (
    add_delay_categories,
    add_delay_shares,
    aggregate_by_station,
    filter_scope,
    rank_stations,
)
from railinsight.backend.retards_gares import compute_station_delays


@pytest.fixture
def raw():
    cols = [
        "prct_cause_infrastructure",
        "prct_cause_trafic",
        "prct_cause_materiel",
        "prct_cause_gare",
        "prct_cause_voyageurs",
        "prct_cause_externe",
    ]
    rows = [
        ("2024-01", "National", "PARIS", 100, [30, 10, 20, 10, 20, 10]),
        ("2024-02", "National", "PARIS", 50, [100, 0, 0, 0, 0, 0]),
        ("2024-01", "National", "LYON", 10, [0, 0, 0, 0, 0, 100]),
        ("2020-03", "National", "PARIS", 999, [100, 0, 0, 0, 0, 0]),
        ("2024-01", "International", "PARIS", 999, [100, 0, 0, 0, 0, 0]),
    ]
    return pd.DataFrame(
        [
            {
                "date": d,
                "service": s,
                "gare_depart": g,
                "retards_arrivee": r,
                **dict(zip(cols, p, strict=True)),
            }
            for d, s, g, r, p in rows
        ]
    )


def test_chain(raw):
    copie = raw.copy()
    table = add_delay_categories(filter_scope(raw))
    agg = aggregate_by_station(table)
    res = add_delay_shares(agg).set_index("gare_depart")

    pd.testing.assert_frame_equal(raw, copie)  # entrée inchangée
    assert res.loc["PARIS", "retard_heritees"] == 30
    assert res.loc["PARIS", "retard_non_heritees"] == 110
    assert res.loc["PARIS", "retard_externes"] == 10
    assert res.loc["PARIS", "taux_heritees"] == pytest.approx(0.2)
    assert res.loc["LYON", "taux_externes"] == 1.0
    assert rank_stations(res.reset_index(), "retard_non_heritees", 1)[
        "gare_depart"
    ].tolist() == ["PARIS"]


def test_invalid_level(raw):
    with pytest.raises(ValueError):
        aggregate_by_station(add_delay_categories(filter_scope(raw)), "mois")