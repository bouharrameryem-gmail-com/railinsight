from railinsight.backend.retards_gares import (
    compute_station_delays,
    load_station_delays,
)


def test_compute_station_delays_levels(raw):
    res = compute_station_delays(raw)

    assert len(res.overall) == 2   # PARIS, LYON
    assert len(res.by_year) == 2   # PARIS 2024, LYON 2024
    assert len(res.by_month) == 3  # PARIS janvier, PARIS février, LYON janvier
    paris = res.overall.set_index("gare_depart").loc["PARIS"]
    assert paris["retard_non_heritees"] == 110


def test_load_station_delays_uses_the_loader(monkeypatch, raw):
    monkeypatch.setattr(
        "railinsight.backend.retards_gares.charger_donnees", lambda: raw
    )

    assert len(load_station_delays().overall) == 2