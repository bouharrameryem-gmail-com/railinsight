"""Tests des indicateurs de ponctualité par liaison (Q3).
 
La table de test est assez petite pour vérifier chaque résultat à la main :
deux liaisons, deux mois.
"""
 
import numpy as np
import pandas as pd
import pytest
 
from railinsight.analysis.indicateurs_liaisons import (
    MOIS_EXCEPTIONNELS,
    adjust_for_duration,
    build_q3_features,
    detect_redundancy,
    mois_a_exclure,
    taux_reseau_mensuel,
)
from railinsight.exceptions import InsufficientDataError
 
COLONNES = [
    "mois",
    "liaison",
    "prevus",
    "annules",
    "circules",
    "retards_sup_15min",
    "retards_sup_30min",
    "retards_sup_60min",
    "retards_arrivee",
    "duree_moyenne",
    "retard_moyen_retardes_arrivee",
]
 
 
@pytest.fixture
def table():
    lignes = [
        ("2024-01", "A - B", 100, 10, 90, 9, 3, 0, 18, 100, 10),
        ("2024-02", "A - B", 100, 0, 100, 20, 2, 1, 25, 100, 20),
        ("2024-01", "C - D", 50, 0, 50, 4, 0, 0, 10, 60, 5),
        ("2024-02", "C - D", 50, 0, 50, 5, 0, 0, 10, 60, 5),
    ]
    return pd.DataFrame(lignes, columns=COLONNES)
 
 
def test_taux_reseau_mensuel(table):
    reseau = taux_reseau_mensuel(table)
 
    assert reseau["2024-01"] == pytest.approx(13 / 140)
    assert reseau["2024-02"] == pytest.approx(25 / 150)
 
 
def test_indicateurs_de_la_liaison_a_b(table):
    copie = table.copy()
 
    f = build_q3_features(table, exclusion="none", min_months=2).loc["A - B"]
 
    pd.testing.assert_frame_equal(table, copie)  # entrée inchangée
    assert f["n_months"] == 2
    assert f["trip_duration_min"] == 100
    assert f["cancellation_rate"] == pytest.approx(10 / 200)
    assert f["late15_rate"] == pytest.approx(29 / 190)
    assert f["late30_rate"] == pytest.approx(5 / 190)
    assert f["late60_rate"] == pytest.approx(1 / 190)
    assert f["severe_share"] == pytest.approx(5 / 29)
    assert f["extreme_share"] == pytest.approx(1 / 29)
    assert f["late_arrival_rate"] == pytest.approx(43 / 190)
    assert f["mean_delay_when_late"] == pytest.approx((10 * 18 + 20 * 25) / 43)
    assert f["severe_ratio"] == pytest.approx(5 / 43)
    # taux mensuels de A - B : 0,1 puis 0,2 ; écart type avec n - 1 au dénominateur
    assert f["volatility"] == pytest.approx(np.std([0.1, 0.2], ddof=1))
    assert f["volatility_cv"] == pytest.approx(np.std([0.1, 0.2], ddof=1) / 0.15)
    assert f["irregularity"] == pytest.approx(np.std([0.2, 0.25], ddof=1))
    assert f["chronicity"] == 1.0  # plus en retard que le réseau les deux mois
 
 
def test_indicateurs_de_la_liaison_c_d(table):
    f = build_q3_features(table, exclusion="none", min_months=2).loc["C - D"]
 
    assert f["cancellation_rate"] == 0.0
    assert f["late15_rate"] == pytest.approx(9 / 100)
    assert f["severe_share"] == 0.0
    assert f["mean_delay_when_late"] == pytest.approx(5.0)
    assert f["irregularity"] == 0.0
    assert f["chronicity"] == 0.0  # moins en retard que le réseau les deux mois
 
 
def test_l_index_s_appelle_route(table):
    f = build_q3_features(table, exclusion="none", min_months=2)
 
    assert f.index.name == "route"
 
 
def test_trop_peu_de_liaisons_leve_une_erreur(table):
    with pytest.raises(InsufficientDataError):
        build_q3_features(table, exclusion="none", min_months=3)
 
 
def test_mois_a_exclure_selon_la_regle():
    reseau = pd.Series(
        [0.1] * 10 + [0.9], index=[f"2024-{mois:02d}" for mois in range(1, 12)]
    )
 
    assert mois_a_exclure(reseau, "none") == frozenset()
    assert mois_a_exclure(reseau, "known") == MOIS_EXCEPTIONNELS
    assert mois_a_exclure(reseau, "data") == frozenset({"2024-11"})
 
 
def test_les_mois_exclus_ne_comptent_pas(table):
    # 2024-02 est exclu : il reste un seul mois par liaison, sous le minimum de 2
    avec_exclusion = table.assign(mois=table["mois"].replace("2024-02", "2020-03"))
 
    with pytest.raises(InsufficientDataError):
        build_q3_features(avec_exclusion, exclusion="known", min_months=2)
 
 
def test_detect_redundancy_repere_les_paires_trop_correlees():
    features = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5, 6],
            "b": [2, 4, 6, 8, 10, 12],  # a x 2 : corrélation parfaite
            "c": [3, 1, 2, 6, 5, 4],  # corrélation de 0,6 avec a
        }
    )
 
    paires = detect_redundancy(features, ["a", "b", "c"], threshold=0.85)
 
    assert [(a, b) for a, b, _ in paires] == [("a", "b")]
    assert paires[0][2] == pytest.approx(1.0)
 
 
def test_adjust_for_duration_corrige_seulement_les_colonnes_liees_a_la_duree():
    duree = np.array([60, 90, 120, 180, 240, 300, 360, 420])
    features = pd.DataFrame(
        {
            "trip_duration_min": duree,
            "liee": 0.01 * np.log(duree),
            "libre": [3, 1, 3, 1, 3, 1, 3, 1],
        }
    )
 
    resultat, pentes = adjust_for_duration(features, ["liee", "libre"])
 
    assert "liee_adj" in resultat.columns
    assert "libre_adj" not in resultat.columns
    assert pentes["liee"] == pytest.approx(0.01)