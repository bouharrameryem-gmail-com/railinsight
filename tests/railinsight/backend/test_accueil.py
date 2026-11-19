"""Tests du chargement des données de la page d'accueil."""

import json

import pytest

from railinsight.backend import accueil
from railinsight.exceptions import DonneesInvalides


def test_calculer_donnees_accueil(brut_reseau, coordonnees_reseau, caplog):
    donnees = accueil.calculer_donnees_accueil(brut_reseau, coordonnees_reseau)

    assert donnees.premier_mois == "2023-01"
    assert donnees.periode.fin == "2024-12"
    assert donnees.precedent is not None
    assert donnees.courant.taux_retard > donnees.precedent.taux_retard
    assert len(donnees.par_mois) == 24
    assert set(donnees.gares["gare"]) == {"PARIS LYON", "LYON PART DIEU"}
    assert donnees.gares_absentes == ("GARE INCONNUE",)
    assert "GARE INCONNUE" in caplog.text


def test_charger_donnees_accueil(monkeypatch, brut_reseau, coordonnees_reseau):
    monkeypatch.setattr(accueil, "charger_donnees", lambda: brut_reseau)
    monkeypatch.setattr(accueil, "charger_coordonnees", lambda: coordonnees_reseau)

    assert accueil.charger_donnees_accueil().courant.liaisons == 3


def test_charger_coordonnees(tmp_path):
    fichier = tmp_path / "gares.csv"
    fichier.write_text(
        "gare;latitude;longitude;region\n paris lyon ;48.8;2.3;IDF\n", encoding="utf-8"
    )

    table = accueil.charger_coordonnees(fichier)

    assert list(table.columns) == ["gare", "latitude", "longitude"]
    assert table.loc[0, "gare"] == "PARIS LYON"


def test_coordonnees_du_depot_lisibles():
    table = accueil.charger_coordonnees()
    assert len(table) > 40
    assert table["gare"].is_unique
    assert table["latitude"].between(41, 52).all()
    assert table["longitude"].between(-5.5, 9.6).all()


def test_coordonnees_absentes_ou_incompletes(tmp_path):
    with pytest.raises(DonneesInvalides, match="introuvables"):
        accueil.charger_coordonnees(tmp_path / "absent.csv")

    fichier = tmp_path / "gares.csv"
    fichier.write_text("gare;latitude\nPARIS;48\n", encoding="utf-8")
    with pytest.raises(DonneesInvalides, match="longitude"):
        accueil.charger_coordonnees(fichier)


def test_reseau_lgv(tmp_path):
    assert accueil.charger_reseau_lgv(tmp_path / "absent.geojson") is None

    fichier = tmp_path / "reseau.geojson"
    fichier.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[2.0, 48.0], [3.0, 47.0]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert accueil.charger_reseau_lgv(fichier) == [[(2.0, 48.0), (3.0, 47.0)]]

    fichier.write_text("{pas du json", encoding="utf-8")
    with pytest.raises(DonneesInvalides, match="illisible"):
        accueil.charger_reseau_lgv(fichier)