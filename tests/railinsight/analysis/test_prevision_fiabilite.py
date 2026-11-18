"""Tests de prévision Q1, dont la séparation chronologique sans fuite."""

import numpy as np
import pandas as pd
import pytest

from railinsight.analysis.prevision_fiabilite import (
    MODELES,
    _predire,
    prevoir_fiabilite,
)
from railinsight.exceptions import DonneesInvalides, InsufficientDataError


@pytest.fixture
def mensuel():
    mois = pd.date_range("2020-01-01", periods=72, freq="MS")
    taux = 0.1 + 0.05 * np.sin(2 * np.pi * mois.month / 12)
    return pd.DataFrame(
        {
            "liaison": "A → B",
            "mois": mois,
            "prevus": 1000.0,
            "incidents": np.asarray(taux) * 1000,
        }
    )


def test_reference_saisonniere_prevoit_exactement_trois_mois(mensuel):
    resultat = prevoir_fiabilite(mensuel.sample(frac=1, random_state=0), "A → B")

    assert resultat.modele == "saisonnier"
    assert len(resultat.historique) == 48
    assert list(resultat.previsions.columns) == ["mois", "fiabilite", "reference"]
    assert list(resultat.previsions["mois"]) == list(
        pd.date_range("2026-01-01", periods=3, freq="MS")
    )
    attendue = (
        1
        - mensuel.set_index("mois").loc[
            pd.date_range("2025-01-01", periods=3, freq="MS"), "incidents"
        ]
        / 1000
    )
    assert resultat.previsions["fiabilite"].tolist() == pytest.approx(attendue)
    assert resultat.mae_test == pytest.approx(0)
    assert resultat.mae_reference == pytest.approx(0)
    assert len(resultat.validation) == 12
    assert len(resultat.test) == 3
    assert resultat.validation["origine"].nunique() == 4
    assert resultat.validation["mois"].max() < resultat.test["mois"].min()
    assert (resultat.validation["origine"] < resultat.validation["mois"]).all()
    assert set(resultat.scores_validation.index) == set(MODELES)


def test_tendance_reguliere_favorise_ridge(mensuel):
    mensuel["incidents"] = np.linspace(80, 450, len(mensuel))
    resultat = prevoir_fiabilite(mensuel, "A → B")

    assert resultat.modele == "ridge"
    assert resultat.mae_test < resultat.mae_reference
    assert resultat.previsions["fiabilite"].between(0, 1).all()


def test_test_final_ne_participe_pas_au_choix_du_modele(mensuel):
    avant = prevoir_fiabilite(mensuel, "A → B")
    mensuel.loc[mensuel.index[-3:], "incidents"] = [900, 0, 500]
    apres = prevoir_fiabilite(mensuel, "A → B")

    assert avant.modele == apres.modele
    pd.testing.assert_frame_equal(avant.validation, apres.validation)
    pd.testing.assert_frame_equal(avant.scores_validation, apres.scores_validation)
    assert avant.mae_test != apres.mae_test


def test_chaque_apprentissage_precede_les_mois_prevus(mensuel, monkeypatch):
    appels = []
    predire = _predire

    def espion(apprentissage, mois, modele):
        assert apprentissage["mois"].max() < mois.min()
        assert len(mois) == 3
        appels.append((modele, apprentissage["mois"].max(), mois.min()))
        return predire(apprentissage, mois, modele)

    monkeypatch.setattr("railinsight.analysis.prevision_fiabilite._predire", espion)
    prevoir_fiabilite(mensuel, "A → B")

    assert len(appels) == 12


def test_taux_recalcule_depuis_les_comptages_sans_moyenne_de_taux(mensuel):
    mensuel["taux_incidents"] = 0.99
    mensuel["prevus"] *= 2
    resultat = prevoir_fiabilite(mensuel, "A → B")
    attendu = 1 - mensuel.tail(48)["incidents"] / mensuel.tail(48)["prevus"]
    assert resultat.historique["fiabilite"].tolist() == pytest.approx(attendu)


@pytest.mark.parametrize("incidents", [0.0, 1000.0])
def test_zero_incident_et_tout_annule_sont_valides(mensuel, incidents):
    mensuel["incidents"] = incidents
    resultat = prevoir_fiabilite(mensuel, "A → B")
    assert resultat.previsions["fiabilite"].tolist() == pytest.approx(
        [1 - incidents / 1000] * 3
    )


def test_ridge_ne_sort_pas_des_bornes():
    mois = pd.date_range("2020-01", periods=36, freq="MS")
    apprentissage = pd.DataFrame(
        {"mois": mois, "prevus": 100, "fiabilite": np.linspace(0.1, 1, 36)}
    )
    predictions = _predire(
        apprentissage, pd.date_range("2023-01", periods=3, freq="MS"), "ridge"
    )
    assert np.isfinite(predictions).all()
    assert ((predictions >= 0) & (predictions <= 1)).all()


@pytest.mark.parametrize(
    ("colonne", "valeur"),
    [
        ("prevus", 0),
        ("prevus", -1),
        ("incidents", -1),
        ("incidents", 1001),
        ("incidents", np.nan),
        ("prevus", np.inf),
        ("prevus", "invalide"),
    ],
)
def test_comptages_invalides_refuses(mensuel, colonne, valeur):
    mensuel[colonne] = mensuel[colonne].astype(object)
    mensuel.loc[0, colonne] = valeur
    with pytest.raises(DonneesInvalides, match="comptages"):
        prevoir_fiabilite(mensuel, "A → B")


def test_dates_invalides_refusees(mensuel):
    mensuel.loc[0, "mois"] = pd.NaT
    with pytest.raises(DonneesInvalides, match="dates"):
        prevoir_fiabilite(mensuel, "A → B")


def test_doublons_mensuels_refuses(mensuel):
    with pytest.raises(DonneesInvalides, match="agrégez les services"):
        prevoir_fiabilite(pd.concat([mensuel, mensuel.iloc[:1]]), "A → B")


def test_liaison_inconnue_refusee(mensuel):
    with pytest.raises(DonneesInvalides, match="inconnue"):
        prevoir_fiabilite(mensuel, "B → A")


def test_colonnes_absentes_refusees(mensuel):
    with pytest.raises(DonneesInvalides, match="colonnes manquantes"):
        prevoir_fiabilite(mensuel.drop(columns="prevus"), "A → B")


def test_donnees_vides_refusees(mensuel):
    with pytest.raises(DonneesInvalides, match="dates"):
        prevoir_fiabilite(mensuel.iloc[:0], "A → B")


@pytest.mark.parametrize("retirer", [range(47), [40], [-1]])
def test_historique_court_troue_ou_perime_non_impute(mensuel, retirer):
    index = mensuel.index[list(retirer)]
    incomplet = mensuel.drop(index=index)
    if list(retirer) == [-1]:
        autre = mensuel.tail(1).assign(liaison="C → D")
        incomplet = pd.concat([incomplet, autre], ignore_index=True)
    with pytest.raises(InsufficientDataError, match="48 mois valides consécutifs"):
        prevoir_fiabilite(incomplet, "A → B")


def test_48_mois_suffisent_exactement(mensuel):
    assert len(prevoir_fiabilite(mensuel.tail(48), "A → B").previsions) == 3
