"""Vérification des fenêtres, des ratios pondérés et des comparaisons d'accueil."""

import numpy as np
import pandas as pd
import pytest

from railinsight.analysis.accueil import (
    calculer_bilan_accueil,
    calculer_liaisons_accueil,
)
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def donnees():
    mois = pd.period_range("2024-10", "2026-09", freq="M").astype(str)
    return pd.DataFrame(
        {
            "mois": mois,
            "gare_depart": "A",
            "gare_arrivee": "B",
            "liaison": "A - B",
            "prevus": 100.0,
            "annules": 10.0,
            "circules": 90.0,
            "retards_sup_15min": 9.0,
        }
    )


def test_fenetre_calendaire_et_evolutions_en_points(donnees):
    avant = donnees.copy(deep=True)
    donnees.loc[12:, "retards_sup_15min"] = 18
    resultat = calculer_bilan_accueil(donnees)
    assert (resultat.debut, resultat.fin) == ("2025-10", "2026-09")
    assert (resultat.debut_precedent, resultat.fin_precedent) == ("2024-10", "2025-09")
    assert resultat.n_mois == 12
    assert resultat.retards.valeur == pytest.approx(0.2)
    assert resultat.retards.evolution_points == pytest.approx(10)
    assert resultat.annulations.evolution_points == pytest.approx(0)
    assert donnees.loc[0, "prevus"] == avant.loc[0, "prevus"]


def test_ratios_de_sommes_pas_moyenne_de_taux(donnees):
    donnees.loc[23, ["prevus", "annules", "circules", "retards_sup_15min"]] = [
        1000,
        0,
        1000,
        0,
    ]
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.retards.valeur == pytest.approx(99 / 1990)
    assert resultat.annulations.valeur == pytest.approx(110 / 2100)
    assert resultat.retards.evolution_points == pytest.approx((99 / 1990 - 0.1) * 100)


def test_compte_liaisons_uniquement_sur_fenetre_recente_et_sans_zero(donnees):
    ancienne = donnees.iloc[[0]].assign(
        gare_depart="C", gare_arrivee="D", liaison="C - D"
    )
    sans_train = donnees.iloc[[23]].assign(
        gare_depart="E",
        gare_arrivee="F",
        liaison="E - F",
        prevus=0,
        annules=0,
        circules=0,
        retards_sup_15min=0,
    )
    resultat = calculer_bilan_accueil(pd.concat([donnees, ancienne, sans_train]))
    assert resultat.n_liaisons == 1
    assert resultat.retards.valeur == pytest.approx(0.1)


def test_mois_absent_ne_remonte_pas_plus_loin_et_pas_de_delta(donnees):
    resultat = calculer_bilan_accueil(donnees.drop(index=20))
    assert resultat.debut == "2025-10"
    assert resultat.n_mois == 11
    assert resultat.retards.evolution_points is None
    assert resultat.retards.valeur == pytest.approx(0.1)


def test_historique_court_pas_de_comparaison(donnees):
    resultat = calculer_bilan_accueil(donnees.tail(3))
    assert resultat.n_mois == 3
    assert resultat.retards.evolution_points is None
    assert resultat.annulations.evolution_points is None


def test_changement_de_perimetre_pas_de_delta(donnees):
    donnees.loc[23, ["gare_depart", "gare_arrivee", "liaison"]] = ["C", "D", "C - D"]
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.n_liaisons == 2
    assert resultat.retards.evolution_points is None


@pytest.mark.parametrize("valeur", [np.nan, np.inf, -1, 200])
def test_numerateur_invalide_exclut_aussi_denominateur(donnees, valeur, caplog):
    donnees.loc[23, "retards_sup_15min"] = valeur
    donnees.loc[23, ["prevus", "circules"]] = [110, 100]
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.retards.valeur == pytest.approx(0.1)
    assert resultat.retards.lignes_ecartees == 1
    assert resultat.retards.evolution_points is None
    assert "sans comptes appariés valides" in caplog.text
    assert resultat.annulations.lignes_ecartees == 0


@pytest.mark.parametrize("colonne,valeur", [("prevus", 0), ("annules", np.nan)])
def test_denominateur_nul_ou_annulations_manquantes(donnees, colonne, valeur):
    donnees.loc[12:, colonne] = valeur
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.retards.valeur is None
    assert resultat.annulations.valeur is None
    assert resultat.retards.evolution_points is None


def test_tous_annules_est_un_taux_valide(donnees):
    donnees.loc[12:, ["annules", "circules", "retards_sup_15min"]] = [100, 0, 0]
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.annulations.valeur == 1
    assert resultat.retards.valeur is None


def test_comptes_nullables_manquants_sont_exclus(donnees):
    donnees["retards_sup_15min"] = donnees["retards_sup_15min"].astype("Float64")
    donnees.loc[23, "retards_sup_15min"] = pd.NA
    resultat = calculer_bilan_accueil(donnees)
    assert resultat.retards.valeur == pytest.approx(0.1)
    assert resultat.retards.lignes_ecartees == 1


def test_ne_modifie_pas_entree_et_dedoublonne(donnees):
    doublon = donnees.iloc[[23]].assign(retards_sup_15min=18)
    entree = pd.concat([donnees, doublon], ignore_index=True)
    avant = entree.copy(deep=True)
    resultat = calculer_bilan_accueil(entree)
    assert resultat.retards.valeur == pytest.approx((11 * 9 + 18) / (12 * 90))
    pd.testing.assert_frame_equal(entree, avant)


def test_erreurs_donnees_explicitement_signalees(donnees):
    with pytest.raises(DonneesInvalides, match="colonnes manquantes"):
        calculer_bilan_accueil(donnees.drop(columns="prevus"))
    with pytest.raises(DonneesInvalides, match="aucune donnée"):
        calculer_bilan_accueil(donnees.iloc[:0])
    donnees.loc[0, "mois"] = "invalide"
    with pytest.raises(DonneesInvalides, match="mois ou gares"):
        calculer_bilan_accueil(donnees)


def test_carte_fenetre_deux_sens_et_ratios_de_sommes(donnees):
    retour = donnees.assign(
        gare_depart="B",
        gare_arrivee="A",
        prevus=200,
        annules=20,
        circules=180,
        retards_sup_15min=0,
    )
    entree = pd.concat([donnees, retour], ignore_index=True)
    avant = entree.copy(deep=True)
    bilan = calculer_bilan_accueil(entree)
    carte = calculer_liaisons_accueil(entree, bilan)
    assert carte["liaison"].tolist() == ["A ↔ B"]
    assert carte["prevus"].tolist() == [3600]
    assert carte["incidents"].tolist() == [468]
    assert carte["taux_incidents"].iloc[0] == pytest.approx(468 / 3600)
    assert carte["n_mois"].tolist() == [12]
    pd.testing.assert_frame_equal(entree, avant)


def test_carte_mesures_incompletes_et_tout_annule(donnees, caplog):
    bilan = calculer_bilan_accueil(donnees)
    donnees.loc[23, "retards_sup_15min"] = np.nan
    carte = calculer_liaisons_accueil(donnees, bilan)
    assert carte["n_mois"].iloc[0] == 11
    assert carte["prevus"].iloc[0] == 1100
    assert "sans mesure valide" in caplog.text
    donnees.loc[:, ["annules", "circules", "retards_sup_15min"]] = [100, 0, 0]
    carte = calculer_liaisons_accueil(donnees, bilan)
    assert carte["taux_incidents"].iloc[0] == 1
    donnees.loc[:, "retards_sup_15min"] = np.nan
    assert calculer_liaisons_accueil(donnees, bilan).empty
