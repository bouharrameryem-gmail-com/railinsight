"""Tests des filtres partagés : filtrer_service et retirer_mois."""
 
import pandas as pd
import pytest
 
from railinsight.analysis.nettoyage import filtrer_service, retirer_mois
from railinsight.exceptions import DonneesInvalides
 
 
@pytest.fixture
def table():
    return pd.DataFrame(
        {
            "service": ["National", "International", "National"],
            "mois": ["2024-01", "2024-01", "2024-02"],
            "prevus": [1, 2, 3],
        }
    )
 
 
def test_filtrer_service_garde_un_seul_service(table):
    copie = table.copy()
 
    resultat = filtrer_service(table)
 
    assert resultat["prevus"].tolist() == [1, 3]
    pd.testing.assert_frame_equal(table, copie)  # entrée inchangée
 
 
def test_filtrer_service_inconnu_donne_une_erreur_claire(table):
    with pytest.raises(DonneesInvalides, match="International"):
        filtrer_service(table, "Autre")
 
 
def test_retirer_mois_retire_les_mois_indiques(table):
    resultat = retirer_mois(table, ["2024-01"])
 
    assert resultat["mois"].tolist() == ["2024-02"]
 
 
def test_retirer_mois_est_idempotent(table):
    une_fois = retirer_mois(table, ["2024-01"])
 
    pd.testing.assert_frame_equal(retirer_mois(une_fois, ["2024-01"]), une_fois)