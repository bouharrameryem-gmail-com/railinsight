"""Tests du chargement et du filtrage de la Q4."""

import pytest

from railinsight.backend import fiabilite
from railinsight.exceptions import DonneesInvalides


def test_chargement_conserve_tous_les_services(monkeypatch, donnees_fiabilite):
    monkeypatch.setattr(fiabilite, "charger_donnees", lambda: donnees_fiabilite)
    table = fiabilite.charger_table_score()
    assert set(table["service"]) == {"National", "International"}
    janvier = fiabilite.analyser_fiabilite(table, "2024-01", "2024-01")
    fevrier = fiabilite.analyser_fiabilite(table, "2024-02", "2024-02")
    assert len(janvier) == 2
    assert len(fevrier) == 1
    assert fevrier.iloc[0]["prevus"] == 1000
    assert set(fiabilite.positions_reseau(table)) == {
        "PARIS",
        "LYON",
        "BRUXELLES",
        "LILLE",
    }


@pytest.mark.parametrize(
    "debut,fin,minimum",
    [
        ("2025-01", "2025-02", 100),
        ("2024-02", "2024-01", 100),
        ("2024-01", "2024-02", -1),
        ("2024-01", "2024-02", 10000),
    ],
)
def test_periode_ou_seuil_inutilisable(
    monkeypatch, donnees_fiabilite, debut, fin, minimum
):
    monkeypatch.setattr(fiabilite, "charger_donnees", lambda: donnees_fiabilite)
    with pytest.raises(DonneesInvalides):
        fiabilite.analyser_fiabilite(
            fiabilite.charger_table_score(), debut, fin, min_trains=minimum
        )


def test_aucune_donnee_utilisable(monkeypatch, donnees_fiabilite):
    donnees_fiabilite["prevus"] = 0
    monkeypatch.setattr(fiabilite, "charger_donnees", lambda: donnees_fiabilite)
    with pytest.raises(DonneesInvalides, match="Aucune donnée utilisable"):
        fiabilite.charger_table_score()
