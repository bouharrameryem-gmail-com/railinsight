"""Tests des fonctions de classement des gares (Q2)."""

import pandas as pd
import pytest

from railinsight.analysis.causes_retards import filtrer_gares_significatives


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