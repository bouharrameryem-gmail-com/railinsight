"""Tests de l'accès aux données côté backend."""

from types import SimpleNamespace

from railinsight.backend import dataloader


def test_charger_donnees_lit_le_chemin_de_la_configuration(monkeypatch):
    lus = []
    cfg = SimpleNamespace(chemins=SimpleNamespace(donnees="x.csv"))
    monkeypatch.setattr(dataloader, "charger_config", lambda: cfg)
    monkeypatch.setattr(
        dataloader, "lire_donnees", lambda chemin: lus.append(chemin) or "df"
    )

    assert dataloader.charger_donnees() == "df"
    assert lus == ["x.csv"]
