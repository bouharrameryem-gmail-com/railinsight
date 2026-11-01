"""Tests des fonctions de classement des gares (Q2)."""

import pandas as pd
import pytest

from railinsight.analysis.causes_retards import (
    croiser_classements,
    filtrer_gares_significatives,
)

@pytest.fixture
def gares():
    return pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "LILLE"],
            "retard_heritees": [60.0, 40.0, 0.0],
            "retard_non_heritees": [30.0, 30.0, 0.0],
            "retard_externes": [10.0, 10.0, 0.0],
        }
    )


def test_filtrer_garde_les_gares_au_dessus_du_minimum(gares):
    copie = gares.copy()

    resultat = filtrer_gares_significatives(gares, 100)

    # PARIS vaut exactement 100 : le minimum est inclus.
    assert resultat["gare_depart"].tolist() == ["PARIS"]
    pd.testing.assert_frame_equal(gares, copie)  # entrée inchangée


def test_filtrer_minimum_zero_garde_tout(gares):
    assert len(filtrer_gares_significatives(gares, 0)) == 3


def test_filtrer_minimum_negatif_leve_une_erreur(gares):
    with pytest.raises(ValueError, match="minimum"):
        filtrer_gares_significatives(gares, -1)

@pytest.fixture
def deux_classements():
    return pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "LILLE", "NICE"],
            "retard_non_heritees": [4.0, 3.0, 2.0, 1.0],
            "retard_heritees": [2.0, 4.0, 1.0, 3.0],
        }
    )


def test_croiser_garde_les_gares_des_deux_hauts_de_classement(deux_classements):
    resultat = croiser_classements(
        deux_classements, "retard_non_heritees", "retard_heritees", n=2
    )

    # Haut de classement des propres : PARIS, LYON. Des hérités : LYON, NICE.
    assert resultat["gare_depart"].tolist() == ["LYON"]
    assert resultat.loc[0, "rang_retard_non_heritees"] == 2
    assert resultat.loc[0, "rang_retard_heritees"] == 1


def test_croiser_sans_gare_commune_renvoie_un_tableau_vide(deux_classements):
    resultat = croiser_classements(
        deux_classements, "retard_non_heritees", "retard_heritees", n=1
    )

    assert resultat.empty
    assert "rang_retard_heritees" in resultat.columns


def test_croiser_ignore_les_valeurs_manquantes(deux_classements):
    deux_classements.loc[1, "retard_heritees"] = float("nan")

    resultat = croiser_classements(
        deux_classements, "retard_non_heritees", "retard_heritees", n=4
    )

    assert "LYON" not in resultat["gare_depart"].tolist()


def test_croiser_trie_selon_le_premier_classement(deux_classements):
    resultat = croiser_classements(
        deux_classements, "retard_non_heritees", "retard_heritees", n=4
    )

    assert resultat["gare_depart"].tolist() == ["PARIS", "LYON", "LILLE", "NICE"]