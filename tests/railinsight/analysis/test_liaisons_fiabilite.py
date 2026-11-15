"""Tests des classements et tendances de fiabilité des liaisons (Q1)."""

import pandas as pd
import pytest

from railinsight.analysis.liaisons_fiabilite import (
    calculer_analyse_liaisons_fiabilite,
)
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def donnees_q1():
    """Petite série permettant de vérifier les sommes et exclusions à la main."""
    lignes = [
        ("2018-01", "PARIS", "LYON", 100, 0, 10, 60),
        ("2018-01", "PARIS", "LYON", 100, 0, 20, 60),
        ("2020-03", "PARIS", "LYON", 100, 0, 80, 60),
        ("2021-06", "PARIS", "LYON", 100, 0, 5, 60),
        ("2022-01", "PARIS", "LYON", 100, 0, 20, 60),
        ("2023-01", "PARIS", "LYON", 100, 0, 101, 60),
        ("2018-01", "LYON", "LILLE", 100, 0, 30, 120),
        ("2020-03", "LYON", "LILLE", 100, 0, 30, 120),
        ("2021-06", "LYON", "LILLE", 100, 0, 30, 120),
        ("2022-01", "LYON", "LILLE", 100, 0, 30, 120),
        ("2018-01", "PARIS", "NICE", 100, 10, 40, 240),
        ("2020-03", "PARIS", "NICE", 100, 0, 50, 240),
        ("2021-06", "PARIS", "NICE", 100, 0, 50, 240),
        ("2022-01", "PARIS", "NICE", 100, 0, 50, 240),
    ]
    donnees = pd.DataFrame(
        lignes,
        columns=[
            "date",
            "gare_depart",
            "gare_arrivee",
            "prevus",
            "annules",
            "retards_sup_15min",
            "duree_moyenne",
        ],
    )
    donnees["date"] = pd.to_datetime(donnees["date"])
    donnees["circules"] = donnees["prevus"] - donnees["annules"]
    return donnees


def test_classement_pondere_et_lignes_impossibles_exclues(donnees_q1):
    resultat = calculer_analyse_liaisons_fiabilite(
        donnees_q1, covid_debut="2020-03", covid_fin="2021-06"
    )

    assert resultat.classement.index[0] == "PARIS → NICE"
    assert resultat.classement.loc["PARIS → LYON", "prevus"] == 500
    assert resultat.classement.loc["PARIS → LYON", "incidents"] == 135
    assert resultat.classement.loc["PARIS → LYON", "taux_incidents"] == pytest.approx(
        135 / 500
    )
    assert resultat.periode_debut == "2018-01"
    assert resultat.periode_fin == "2022-01"


def test_tendances_comparent_les_regles_d_exclusion(donnees_q1):
    resultat = calculer_analyse_liaisons_fiabilite(
        donnees_q1, covid_debut="2020-03", covid_fin="2021-06"
    )

    tendances = resultat.tendances.loc["PARIS → LYON"]
    assert tendances["fenetre_covid"] != pytest.approx(tendances["aucune_exclusion"])
    assert tendances["mois_documentes"] != pytest.approx(tendances["aucune_exclusion"])
    assert resultat.tendance_reseau.loc["reseau", "fenetre_covid"] != pytest.approx(
        resultat.tendance_reseau.loc["reseau", "aucune_exclusion"]
    )


def test_classement_ajuste_a_la_duree(donnees_q1):
    resultat = calculer_analyse_liaisons_fiabilite(
        donnees_q1, covid_debut="2020-03", covid_fin="2021-06"
    )

    assert resultat.classement_duree["taux_ajuste"].notna().all()
    assert resultat.classement_duree.loc["PARIS → LYON", "duree_mediane"] == 60
    assert resultat.classement_duree.loc["PARIS → NICE", "duree_mediane"] == 240
    assert pd.notna(resultat.correlation_duree)


def test_donnees_vides_ou_colonnes_manquantes_sont_signalees(donnees_q1):
    with pytest.raises(DonneesInvalides, match="aucune donnée"):
        calculer_analyse_liaisons_fiabilite(
            donnees_q1.iloc[0:0], covid_debut="2020-03", covid_fin="2021-06"
        )

    with pytest.raises(DonneesInvalides, match="colonnes manquantes"):
        calculer_analyse_liaisons_fiabilite(
            donnees_q1.drop(columns="circules"),
            covid_debut="2020-03",
            covid_fin="2021-06",
        )
