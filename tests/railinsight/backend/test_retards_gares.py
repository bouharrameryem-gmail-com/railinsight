from railinsight.backend.retards_gares import (
    calculer_retards_par_gare,
    charger_retards_par_gare,
)


def test_calculer_retards_par_gare(raw):
    res = calculer_retards_par_gare(raw)

    assert len(res.overall) == 2  # PARIS, LYON
    assert len(res.by_year) == 2  # PARIS 2024, LYON 2024
    assert len(res.by_month) == 3  # PARIS janvier, PARIS février, LYON janvier
    paris = res.overall.set_index("gare_depart").loc["PARIS"]
    assert paris["retard_non_heritees"] == 110


def test_charger_retards_par_gare_uses_the_loader(monkeypatch, raw):
    monkeypatch.setattr(
        "railinsight.backend.retards_gares.charger_donnees", lambda: raw
    )

    assert len(charger_retards_par_gare().overall) == 2
