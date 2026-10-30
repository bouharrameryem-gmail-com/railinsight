import pandas as pd
import pytest


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