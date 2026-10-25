"""Tests de l'accès aux données côté backend."""

from types import SimpleNamespace

from railinsight.backend import donnees


def test_charger_donnees_lit_le_chemin_de_la_configuration(monkeypatch):
    lus = []
    cfg = SimpleNamespace(chemins=SimpleNamespace(donnees="x.csv"))
    monkeypatch.setattr(donnees, "charger_config", lambda: cfg)
    monkeypatch.setattr(
        donnees, "lire_donnees", lambda chemin: lus.append(chemin) or "df"
    )

    assert donnees.charger_donnees() == "df"
    assert lus == ["x.csv"]