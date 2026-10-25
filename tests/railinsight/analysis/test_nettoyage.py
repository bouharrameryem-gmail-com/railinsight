"""Tests du nettoyage : contrats, cas limites, équivalence avec le notebook."""

import logging

import numpy as np
import pandas as pd
import pytest

from railinsight.analysis.nettoyage import (
    ajouter_liaison,
    ajouter_minutes_retard,
    convertir_mois,
    filtrer_periode,
    invalider_hors_bornes,
    nettoyer_regularite,
    normaliser_nom,
    retirer_doublons,
    retirer_sans_train,
    taux,
)
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def brut():
    """Petit extrait au format de lire_donnees (noms propres, texte et nombres)."""
    return pd.DataFrame(
        {
            "date": ["2024-01", "2024-01", "2024-02", "2024-02", "2024-02"],
            "gare_depart": ["PARIS  lyon", "lyon", "Paris Lyon", "Nantes", "Lille"],
            "gare_arrivee": ["lyon", "paris   LYON", "Marseille", "Paris", "Paris"],
            "prevus": [100.0, 50.0, 0.0, 80.0, np.nan],
            "annules": [5.0, 0.0, 0.0, 8.0, 1.0],
            "retard_moyen_arrivee": [10.0, 4.0, 3.0, 6.0, 2.0],
        }
    )


# ---------- contrats : pure et idempotent ----------


def test_nettoyer_ne_modifie_pas_son_argument(brut):
    copie = brut.copy()
    nettoyer_regularite(brut)
    pd.testing.assert_frame_equal(brut, copie)


def test_nettoyer_est_idempotent(brut):
    une_fois = nettoyer_regularite(brut)
    pd.testing.assert_frame_equal(nettoyer_regularite(une_fois), une_fois)


def test_nettoyer_ne_supprime_aucune_ligne(brut):
    """Retirer des lignes est une décision d'analyse, pas du socle commun."""
    assert len(nettoyer_regularite(brut)) == len(brut)


def test_nettoyer_resultat(brut):
    df = nettoyer_regularite(brut)
    assert df["mois"].tolist() == ["2024-01"] * 2 + ["2024-02"] * 3
    assert df["gare_depart"].tolist() == [
        "PARIS LYON",
        "LYON",
        "PARIS LYON",
        "NANTES",
        "LILLE",
    ]
    # Paris -> Lyon et Lyon -> Paris : même liaison
    assert df["liaison"].tolist()[:2] == ["LYON - PARIS LYON"] * 2
    assert df["circules"].tolist()[:4] == [95.0, 50.0, 0.0, 72.0]
    assert df["minutes_retard"].tolist()[:4] == [950.0, 200.0, 0.0, 432.0]
    assert np.isnan(df["circules_mesures"].iloc[4])  # prevus manquant


def test_nettoyer_nomme_toutes_les_colonnes_manquantes(brut):
    with pytest.raises(DonneesInvalides, match="date, prevus"):
        nettoyer_regularite(brut.drop(columns=["date", "prevus"]))


def test_nettoyer_equivalent_au_notebook_de_reference():
    """Test de caractérisation : même calcul que la cellule 8 du notebook de Meryem."""
    brut = pd.DataFrame(
        {
            "date": ["2024-01", "2024-01", "2024-02", "2024-02"],
            "gare_depart": [" PARIS lyon", "lyon", "Nantes ", "lille"],
            "gare_arrivee": ["lyon", "PARIS LYON", "Paris", "Paris"],
            "prevus": [100.0, 50.0, 80.0, 0.0],
            "annules": [5.0, 0.0, 8.0, 1.0],
            "retard_moyen_arrivee": [10.0, 4.0, 6.0, 2.0],
        }
    )
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(brut["date"]),
            "depart": brut["gare_depart"].str.strip().str.title(),
            "arrivee": brut["gare_arrivee"].str.strip().str.title(),
            "prevus": brut["prevus"],
            "annules": brut["annules"],
            "retard_tous": brut["retard_moyen_arrivee"],
        }
    )
    data = data[data["prevus"] > 0].copy()
    data["circules"] = data["prevus"] - data["annules"]
    data["minutes_retard"] = data["retard_tous"] * data["circules"]
    data["gare_a"] = data[["depart", "arrivee"]].min(axis=1)
    data["gare_b"] = data[["depart", "arrivee"]].max(axis=1)
    data["mois"] = data["date"].dt.to_period("M").astype(str)
    data = data.reset_index(drop=True)

    df = retirer_sans_train(nettoyer_regularite(brut))
    for colonne in ("circules", "minutes_retard", "mois"):
        assert df[colonne].tolist() == data[colonne].tolist(), colonne
    # le notebook affiche en casse « Titre » ; le socle garde les MAJUSCULES du fichier
    for colonne in ("gare_a", "gare_b"):
        assert df[colonne].str.title().tolist() == data[colonne].tolist(), colonne


def test_doublons_signales_mais_conserves(brut, caplog):
    avec_doublon = pd.concat([brut, brut.iloc[[0]]], ignore_index=True)
    with caplog.at_level(logging.WARNING):
        df = nettoyer_regularite(avec_doublon)
    assert len(df) == len(avec_doublon)  # signalés, pas supprimés
    assert "en double" in caplog.text


def test_silence_sans_anomalie(caplog):
    propre = pd.DataFrame(
        {
            "date": ["2024-01"],
            "gare_depart": ["Paris"],
            "gare_arrivee": ["Lyon"],
            "prevus": [10.0],
            "annules": [0.0],
            "retard_moyen_arrivee": [1.0],
        }
    )
    with caplog.at_level(logging.WARNING):
        nettoyer_regularite(propre)
    assert caplog.records == []


# ---------- outils génériques ----------


def test_normaliser_nom_espaces_insecables_et_majuscules():
    serie = pd.Series(["  Lyon\u00a0 part-dieu ", None, "Paris\u202fLyon"])
    resultat = normaliser_nom(serie)
    assert resultat.iloc[0] == "LYON PART-DIEU"
    assert pd.isna(resultat.iloc[1])
    assert resultat.iloc[2] == "PARIS LYON"
    pd.testing.assert_series_equal(normaliser_nom(resultat), resultat)


def test_convertir_mois_valide_illisible_et_idempotent(caplog):
    serie = pd.Series(["2024-01", " 2024-12 ", "2024/03", "abc", None])
    with caplog.at_level(logging.WARNING):
        dates = convertir_mois(serie)
    assert dates.iloc[0] == pd.Timestamp("2024-01-01")
    assert dates.iloc[1] == pd.Timestamp("2024-12-01")
    assert dates.isna().tolist() == [False, False, True, True, True]
    assert "2 mois illisible" in caplog.text
    pd.testing.assert_series_equal(convertir_mois(dates), dates)


def test_taux_gere_la_division_par_zero():
    resultat = taux(pd.Series([5.0, 1.0, 2.0]), pd.Series([100.0, 0.0, np.nan]))
    assert resultat.iloc[0] == 5.0
    assert resultat.iloc[1:].isna().all()
    assert not np.isinf(resultat).any()


def test_invalider_hors_bornes_garde_les_lignes_et_compte(caplog):
    serie = pd.Series([-5.0, 0.0, 10.0, 200.0, np.nan], name="retard")
    with caplog.at_level(logging.WARNING):
        resultat = invalider_hors_bornes(serie, minimum=0, maximum=100)
    assert resultat.isna().tolist() == [True, False, False, True, True]
    assert "retard" in caplog.text
    assert "2 valeur(s)" in caplog.text
    pd.testing.assert_series_equal(
        invalider_hors_bornes(resultat, minimum=0, maximum=100), resultat
    )


def test_invalider_hors_bornes_sans_borne_ne_change_rien():
    serie = pd.Series([-1.0, 1.0])
    pd.testing.assert_series_equal(invalider_hors_bornes(serie), serie)


def test_retirer_doublons_garde_la_derniere(caplog):
    df = pd.DataFrame({"cle": ["a", "b", "a"], "valeur": [1, 2, 3]})
    with caplog.at_level(logging.WARNING):
        resultat = retirer_doublons(df, ["cle"])
    assert resultat["valeur"].tolist() == [2, 3]
    assert "1 ligne(s) en double" in caplog.text
    pd.testing.assert_frame_equal(retirer_doublons(resultat, ["cle"]), resultat)


def test_retirer_sans_train_zero_et_manquant(caplog):
    df = pd.DataFrame({"prevus": [10.0, 0.0, np.nan, 5.0], "x": [1, 2, 3, 4]})
    with caplog.at_level(logging.INFO):
        resultat = retirer_sans_train(df)
    assert resultat["x"].tolist() == [1, 4]
    assert "2 ligne(s) sans train" in caplog.text
    pd.testing.assert_frame_equal(retirer_sans_train(resultat), resultat)


def test_filtrer_periode_bornes_incluses():
    df = pd.DataFrame({"mois": ["2024-01", "2024-02", "2024-03", None]})
    assert len(filtrer_periode(df)) == 4  # sans borne : rien n'est écarté
    assert filtrer_periode(df, debut="2024-02")["mois"].tolist() == [
        "2024-02",
        "2024-03",
    ]
    assert filtrer_periode(df, fin="2024-02")["mois"].tolist() == [
        "2024-01",
        "2024-02",
    ]
    assert filtrer_periode(df, "2024-02", "2024-02")["mois"].tolist() == ["2024-02"]


def test_ajouter_liaison_ordre_alphabetique():
    df = pd.DataFrame(
        {"gare_depart": ["Paris", "Lyon"], "gare_arrivee": ["Lyon", "Paris"]}
    )
    resultat = ajouter_liaison(df)
    assert resultat["liaison"].tolist() == ["Lyon - Paris", "Lyon - Paris"]
    assert "liaison" not in df.columns


def test_ajouter_minutes_retard_permet_de_sommer_des_moyennes():
    df = pd.DataFrame(
        {
            "prevus": [100.0, 10.0],
            "annules": [0.0, 0.0],
            "retard_moyen_arrivee": [1.0, 11.0],
        }
    )
    resultat = ajouter_minutes_retard(df)
    moyenne_vraie = resultat["minutes_retard"].sum() / resultat["circules"].sum()
    assert moyenne_vraie == pytest.approx(210 / 110)
    # la moyenne des moyennes serait fausse : (1 + 11) / 2 = 6
    assert df["retard_moyen_arrivee"].mean() == 6.0


def test_retard_manquant_ne_fausse_pas_la_moyenne():
    df = pd.DataFrame(
        {
            "prevus": [100.0, 50.0],
            "annules": [0.0, 0.0],
            "retard_moyen_arrivee": [10.0, np.nan],
        }
    )
    resultat = ajouter_minutes_retard(df)
    assert resultat["circules_mesures"].tolist()[0] == 100.0
    assert np.isnan(resultat["circules_mesures"].iloc[1])
    juste = resultat["minutes_retard"].sum() / resultat["circules_mesures"].sum()
    faux = resultat["minutes_retard"].sum() / resultat["circules"].sum()
    assert juste == pytest.approx(10.0)
    assert faux == pytest.approx(1000 / 150)
