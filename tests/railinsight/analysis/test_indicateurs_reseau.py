"""Tests des indicateurs du réseau affichés sur la page d'accueil."""

import pandas as pd
import pytest

from railinsight.analysis.indicateurs_reseau import (
    Fenetre,
    ecart_en_points,
    fenetres_annuelles,
    gares_les_plus_touchees,
    mois_le_plus_difficile,
    placer_gares,
    preparer_donnees,
    regrouper_gares_proches,
    taux_par_gare,
    taux_par_mois,
    taux_sur_fenetre,
    un_sur,
)
from railinsight.analysis.nettoyage import filtrer_service, nettoyer_regularite
from railinsight.exceptions import DonneesInvalides

ANNEE_2023 = Fenetre("2023-01", "2023-12")
ANNEE_2024 = Fenetre("2024-01", "2024-12")
# Par mois : 99 + 100 + 60 + 10 retards pour 990 + 500 + 200 + 100 trains,
# et 100 retards de plus en juillet 2024.
RETARDS_2024 = 269 * 12 + 100
TRAINS_2024 = 1790 * 12


@pytest.fixture
def donnees(brut_reseau):
    return preparer_donnees(filtrer_service(nettoyer_regularite(brut_reseau)))


def test_preparer_retire_doublons_et_lignes_sans_train(donnees):
    assert len(donnees) == 4 * 24
    assert not (donnees["prevus"] <= 0).any()


def test_preparer_exige_les_colonnes():
    with pytest.raises(DonneesInvalides, match="retards_sup_15min"):
        preparer_donnees(pd.DataFrame(columns=["date", "mois"]))


def test_fenetres_annuelles(donnees):
    assert fenetres_annuelles(donnees["mois"]) == (ANNEE_2024, ANNEE_2023)


def test_fenetre_precedente_absente_si_historique_trop_court():
    mois = pd.Series(["2024-03", "2024-12"])
    assert fenetres_annuelles(mois) == (Fenetre("2024-01", "2024-12"), None)


def test_fenetres_sans_mois():
    with pytest.raises(DonneesInvalides):
        fenetres_annuelles(pd.Series([None], dtype="object"))


def test_taux_sur_fenetre(donnees):
    taux = taux_sur_fenetre(donnees, ANNEE_2024)

    assert taux.taux_retard == pytest.approx(RETARDS_2024 / TRAINS_2024)
    assert taux.taux_annulation == pytest.approx(120 / (1800 * 12))
    assert taux.liaisons == 3
    assert taux.trains == TRAINS_2024


def test_taux_ignore_les_retards_inconnus(donnees):
    inconnus = donnees.assign(retards_sup_15min=float("nan"))
    melange = pd.concat([donnees, inconnus.head(1).assign(mois="2024-01")])

    taux = taux_sur_fenetre(melange, ANNEE_2024)

    assert taux.taux_retard == pytest.approx(RETARDS_2024 / TRAINS_2024)


def test_taux_sur_fenetre_vide(donnees):
    with pytest.raises(DonneesInvalides, match="aucun train"):
        taux_sur_fenetre(donnees, Fenetre("2030-01", "2030-12"))


@pytest.mark.parametrize(
    ("taux", "attendu"), [(0.11, 9), (0.154935, 6), (0.5, 2), (1.0, 1)]
)
def test_un_sur(taux, attendu):
    assert un_sur(taux) == attendu


@pytest.mark.parametrize("taux", [0.0, -0.1, 1.5])
def test_un_sur_refuse_un_taux_impossible(taux):
    with pytest.raises(ValueError, match="taux"):
        un_sur(taux)


def test_ecart_en_points():
    assert ecart_en_points(0.15, 0.12) == pytest.approx(3.0)


def test_taux_par_mois_et_pire_mois(donnees):
    par_mois = taux_par_mois(donnees)

    assert len(par_mois) == 24
    assert set(par_mois.columns) == {"annee", "mois_numero", "taux_retard"}
    mois, taux = mois_le_plus_difficile(par_mois)
    assert mois == pd.Period("2024-07", freq="M")
    assert taux == pytest.approx(369 / 1790)


def test_pire_mois_sans_donnees():
    with pytest.raises(DonneesInvalides):
        mois_le_plus_difficile(
            pd.DataFrame(columns=["annee", "mois_numero", "taux_retard"])
        )


def test_taux_par_gare(donnees):
    gares = taux_par_gare(donnees, ANNEE_2024).set_index("gare")

    assert set(gares.index) == {"PARIS LYON", "LYON PART DIEU", "GARE INCONNUE"}
    assert gares.loc["PARIS LYON", "trains"] == 1190 * 12
    assert gares.loc["PARIS LYON", "taux_retard"] == pytest.approx(159 / 1190)
    destinations = gares.loc["PARIS LYON", "destinations"]
    assert [arrivee for arrivee, _ in destinations] == [
        "MARSEILLE ST CHARLES",
        "LYON PART DIEU",
    ]
    assert destinations[0][1] == pytest.approx(0.3)


def test_taux_par_gare_ignore_les_petites_liaisons(donnees):
    gares = taux_par_gare(donnees, ANNEE_2024, minimum_trains=10**6)

    assert all(destinations == () for destinations in gares["destinations"])


def test_placer_gares(donnees, coordonnees_reseau):
    placees, absentes = placer_gares(
        taux_par_gare(donnees, ANNEE_2024), coordonnees_reseau
    )

    assert set(placees["gare"]) == {"PARIS LYON", "LYON PART DIEU"}
    assert {"latitude", "longitude"} <= set(placees.columns)
    assert absentes == ("GARE INCONNUE",)


def test_gares_les_plus_touchees(donnees):
    gares = taux_par_gare(donnees, ANNEE_2024)

    pires = gares_les_plus_touchees(gares, 2)
    assert list(pires["gare"]) == ["LYON PART DIEU", "PARIS LYON"]
    assert list(gares_les_plus_touchees(gares, 5, minimum_trains=10_000)["gare"]) == [
        "PARIS LYON"
    ]


def test_regrouper_gares_proches():
    gares = pd.DataFrame(
        {
            "gare": ["PARIS NORD", "PARIS LYON", "LILLE"],
            "latitude": [48.88, 48.84, 50.64],
            "longitude": [2.36, 2.37, 3.07],
            "trains": [3000, 1000, 2000],
            "taux_retard": [0.10, 0.30, 0.20],
            "destinations": [(("LILLE", 0.1),), (), (("PARIS NORD", 0.2),)],
        }
    )

    bulles = regrouper_gares_proches(gares).set_index("gare")

    assert list(bulles.index) == ["PARIS", "LILLE"]
    assert bulles.loc["PARIS", "trains"] == 4000
    assert bulles.loc["PARIS", "taux_retard"] == pytest.approx(0.15)
    assert bulles.loc["PARIS", "latitude"] == pytest.approx(48.87)
    assert bulles.loc["PARIS", "membres"] == (
        ("PARIS NORD", 0.10),
        ("PARIS LYON", 0.30),
    )
    assert bulles.loc["PARIS", "destinations"] == ()
    assert bulles.loc["LILLE", "membres"] == ()
    assert bulles.loc["LILLE", "destinations"] == (("PARIS NORD", 0.2),)


def test_groupe_sans_mot_commun_prend_le_nom_de_la_plus_grande():
    gares = pd.DataFrame(
        {
            "gare": ["LILLE", "TOURCOING"],
            "latitude": [50.64, 50.72],
            "longitude": [3.07, 3.17],
            "trains": [5000, 0],
            "taux_retard": [0.1, 0.3],
            "destinations": [(), ()],
        }
    )

    bulles = regrouper_gares_proches(gares)

    assert list(bulles["gare"]) == ["LILLE"]
    assert bulles.loc[0, "taux_retard"] == pytest.approx(0.1)


def test_groupe_sans_trafic():
    gares = pd.DataFrame(
        {
            "gare": ["PARIS NORD", "PARIS EST"],
            "latitude": [48.88, 48.88],
            "longitude": [2.36, 2.36],
            "trains": [0, 0],
            "taux_retard": [0.1, 0.3],
            "destinations": [(), ()],
        }
    )

    assert regrouper_gares_proches(gares).loc[0, "taux_retard"] == pytest.approx(0.2)
