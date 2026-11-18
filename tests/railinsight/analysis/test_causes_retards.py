"""Tests des fonctions de classement des gares (Q2)."""

import pandas as pd
import pytest

from railinsight.analysis.causes_retards import (
    ajouter_parts_retard,
    annees_completes,
    croiser_classements,
    dresser_portrait_gare,
    evolution_part,
    filtrer_gares_significatives,
    parts_reseau,
    resumer_retards_gares,
)
from railinsight.exceptions import DonneesInvalides, InvalidSelectionError


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


@pytest.fixture
def par_gare():
    """Quatre gares dont les résultats se vérifient à la main (total : 2 300)."""
    table = pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "LILLE", "NICE"],
            "retard_heritees": [100.0, 400.0, 50.0, 0.0],
            "retard_non_heritees": [500.0, 300.0, 100.0, 100.0],
            "retard_externes": [400.0, 300.0, 50.0, 0.0],
        }
    )
    return ajouter_parts_retard(table)


def test_resume_chiffres_cles(par_gare):
    resume = resumer_retards_gares(par_gare, minimum=1000)

    assert resume.nombre_gares == 4
    assert resume.total_retards == 2300
    assert resume.part_propres == pytest.approx(1000 / 2300)
    assert resume.part_heritees == pytest.approx(550 / 2300)
    assert resume.part_externes == pytest.approx(750 / 2300)
    assert resume.gare_propres == "PARIS"
    assert resume.volume_propres == 500
    assert resume.part_top3_propres == pytest.approx(900 / 1000)
    assert resume.gare_heritees == "LYON"
    # Seules PARIS et LYON atteignent 1 000 retards ; LYON a 40 % d'importés.
    assert resume.nombre_significatives == 2
    assert resume.gare_part_heritee == "LYON"
    assert resume.part_heritee_max == pytest.approx(0.4)


def test_resume_sans_gare_au_dessus_du_minimum(par_gare):
    resume = resumer_retards_gares(par_gare, minimum=5000)

    assert resume.nombre_significatives == 0
    assert resume.gare_part_heritee is None
    assert resume.part_heritee_max is None


def test_resume_sans_retard_propre():
    table = ajouter_parts_retard(
        pd.DataFrame(
            {
                "gare_depart": ["A"],
                "retard_heritees": [10.0],
                "retard_non_heritees": [0.0],
                "retard_externes": [0.0],
            }
        )
    )

    assert resumer_retards_gares(table).part_top3_propres == 0.0


def test_resume_table_vide(par_gare):
    with pytest.raises(DonneesInvalides):
        resumer_retards_gares(par_gare.iloc[0:0])


def test_parts_reseau_additionne_les_gares():
    par_annee = pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "PARIS"],
            "annee": [2024, 2023, 2023],
            "retard_heritees": [20.0, 30.0, 10.0],
            "retard_non_heritees": [20.0, 0.0, 60.0],
            "retard_externes": [10.0, 0.0, 0.0],
        }
    )

    reseau = parts_reseau(par_annee, "annee")

    assert reseau["annee"].tolist() == [2023, 2024]
    assert reseau["taux_heritees"].tolist() == pytest.approx([0.4, 0.4])
    assert reseau["taux_externes"].tolist() == pytest.approx([0.0, 0.2])


def test_annees_completes():
    par_mois = pd.DataFrame(
        {"date": pd.date_range("2023-01-01", "2024-03-01", freq="MS")}
    )

    assert annees_completes(par_mois) == [2023]


def test_evolution_part_premiere_et_derniere_annee_retenues():
    par_annee = pd.DataFrame(
        {"annee": [2021, 2019, 2020, 2022], "part": [0.3, 0.1, 0.2, 0.9]}
    )

    evolution = evolution_part(par_annee, "part", [2019, 2020, 2021])

    # 2022 n'est pas une année retenue : elle est ignorée.
    assert (evolution.annee_debut, evolution.annee_fin) == (2019, 2021)
    assert evolution.ecart == pytest.approx(0.2)


def test_evolution_part_trop_peu_d_annees():
    par_annee = pd.DataFrame({"annee": [2019, 2020], "part": [0.1, 0.2]})

    assert evolution_part(par_annee, "part", [2019, 2020]) is None


@pytest.fixture
def historique_paris():
    """Trois années complètes pour PARIS, avec un pic en juillet 2021."""
    par_mois = pd.DataFrame(
        {
            "date": pd.date_range("2019-01-01", "2021-12-01", freq="MS"),
            "gare_depart": "PARIS",
            "retard_heritees": 1.0,
            "retard_non_heritees": 1.0,
            "retard_externes": 1.0,
        }
    )
    par_mois.loc[par_mois["date"] == "2021-07-01", "retard_non_heritees"] = 10.0
    par_annee = pd.DataFrame(
        {
            "gare_depart": "PARIS",
            "annee": [2019, 2020, 2021],
            "taux_heritees": [0.10, 0.15, 0.25],
        }
    )
    return par_annee, par_mois


def test_portrait_de_paris(par_gare, historique_paris):
    par_annee, par_mois = historique_paris

    portrait = dresser_portrait_gare("PARIS", par_gare, par_annee, par_mois)

    assert portrait.total_retards == 1000
    assert portrait.part_heritee == pytest.approx(0.1)
    assert portrait.part_heritee_moyenne == pytest.approx(550 / 2300)
    assert portrait.rang_propres == 1
    assert portrait.rang_heritees == 2
    assert portrait.nombre_gares == 4
    assert portrait.evolution.annee_debut == 2019
    assert portrait.evolution.ecart == pytest.approx(0.15)
    assert portrait.mois_pic == pd.Timestamp("2021-07-01")
    assert portrait.volume_pic == 12
    assert portrait.pires_mois_total == 12


def test_portrait_compte_les_pires_mois_en_ete(par_gare):
    par_mois = pd.DataFrame(
        {
            "date": pd.date_range("2023-05-01", "2023-10-01", freq="MS"),
            "gare_depart": "LYON",
            "retard_heritees": 1.0,
            "retard_non_heritees": 1.0,
            "retard_externes": 1.0,
        }
    )
    par_annee = pd.DataFrame(
        {"gare_depart": ["LYON"], "annee": [2023], "taux_heritees": [0.3]}
    )

    portrait = dresser_portrait_gare("LYON", par_gare, par_annee, par_mois)

    # Six mois de mai à octobre : juin, juillet et août sont en été.
    assert portrait.pires_mois_total == 6
    assert portrait.pires_mois_ete == 3
    assert portrait.evolution is None


def test_portrait_gare_inconnue(par_gare, historique_paris):
    par_annee, par_mois = historique_paris

    with pytest.raises(InvalidSelectionError, match="BREST"):
        dresser_portrait_gare("BREST", par_gare, par_annee, par_mois)
