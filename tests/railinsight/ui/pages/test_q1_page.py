"""Tests de la page Streamlit Q1."""

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.analysis.liaisons_fiabilite import (
    calculer_analyse_liaisons_fiabilite,
)
from railinsight.analysis.prevision_fiabilite import prevoir_fiabilite
from railinsight.utils.formatting import fmt_pct

PAGE = (
    Path(__file__).parents[4]
    / "src"
    / "railinsight"
    / "ui"
    / "pages"
    / "q1_liaisons_fiabilite.py"
)


def ouvrir_onglet(page, nom):
    page.session_state["q1_liaisons_fiabilite__onglet"] = nom
    page.run()


@pytest.fixture
def page_q1(monkeypatch, request):
    """Affiche Q1 avec des données locales contrôlées."""
    donnees = pd.DataFrame(
        [
            ("2024-01", "PARIS", "LYON", 100, 0, 10, 60),
            ("2024-02", "PARIS", "LYON", 100, 0, 20, 60),
            ("2024-01", "LYON", "LILLE", 100, 0, 30, 120),
            ("2024-02", "LYON", "LILLE", 100, 0, 20, 120),
        ],
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
    if getattr(request, "param", False):
        donnees = pd.concat(
            [
                donnees.loc[donnees["date"].eq("2024-01-01")].assign(date=mois)
                for mois in pd.date_range("2019-01", periods=72, freq="MS")
            ],
            ignore_index=True,
        )
    donnees["circules"] = donnees["prevus"] - donnees["annules"]
    analyse = calculer_analyse_liaisons_fiabilite(
        donnees, covid_debut="2020-03", covid_fin="2021-06"
    )
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.liaisons_fiabilite.charger_analyse_liaisons_fiabilite",
        lambda: analyse,
    )
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def test_page_affiche_classement_tendances_et_methodologie(page_q1):
    page_q1.run()

    assert not page_q1.exception
    assert not page_q1.error
    assert not page_q1.warning
    assert [onglet.label for onglet in page_q1.tabs] == [
        "Classement",
        "Évolution et tendances",
        "À durée égale",
        "Prévision à 3 mois",
    ]
    assert len(page_q1.get("plotly_chart")) == 1
    assert not page_q1.multiselect
    assert [widget.label for widget in page_q1.selectbox] == ["Votre liaison"]
    assert any(volet.label == "Méthode et limites" for volet in page_q1.expander)


def test_nombre_de_liaisons_est_interactif(page_q1):
    page_q1.run()
    page_q1.number_input[0].set_value(1).run()

    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("plotly_chart")) == 1
    classement = json.loads(page_q1.get("plotly_chart")[0].proto.spec)
    assert len(classement["data"][0]["y"]) == 1


def test_comparer_plusieurs_liaisons_et_choisir_la_granularite(page_q1):
    page_q1.run()
    ouvrir_onglet(page_q1, "Évolution et tendances")

    page_q1.multiselect[0].set_value(["PARIS → LYON", "LYON → LILLE"]).run()
    page_q1.segmented_control[1].set_value("Annuel").run()

    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("plotly_chart")) == 1
    comparaison = json.loads(page_q1.get("plotly_chart")[0].proto.spec)
    assert [trace["name"] for trace in comparaison["data"][:2]] == [
        "PARIS → LYON",
        "LYON → LILLE",
    ]


def test_comparaison_vide_et_export_donnees(page_q1):
    page_q1.run()
    ouvrir_onglet(page_q1, "Évolution et tendances")
    page_q1.multiselect[0].set_value([]).run()

    assert not page_q1.exception
    assert any("Choisissez au moins une liaison" in info.value for info in page_q1.info)

    page_q1.multiselect[0].set_value(["PARIS → LYON"]).run()

    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("download_button")) == 1


def test_prevision_historique_insuffisant_affiche_un_message(page_q1):
    page_q1.run()
    ouvrir_onglet(page_q1, "Prévision à 3 mois")

    assert not page_q1.exception
    assert not page_q1.error
    assert any("48 mois valides consécutifs" in info.value for info in page_q1.info)
    assert not page_q1.get("plotly_chart")
    assert not page_q1.number_input


@pytest.mark.parametrize("page_q1", [True], indirect=True)
def test_prevision_interactive_et_export_sur_historique_long(page_q1):
    page_q1.run()
    assert len(page_q1.get("plotly_chart")) == 1
    ouvrir_onglet(page_q1, "Prévision à 3 mois")

    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("plotly_chart")) == 1
    assert len(page_q1.get("download_button")) == 1
    assert any("Prévision exploratoire" in alerte.value for alerte in page_q1.warning)
    tableau = next(
        table.value
        for table in page_q1.dataframe
        if "Fiabilité prévue (%)" in table.value.columns
        and "Mois" in table.value.columns
    )
    assert tableau["Mois"].tolist() == ["2025-01", "2025-02", "2025-03"]
    assert tableau["Fiabilité prévue (%)"].tolist() == [70, 70, 70]
    choix = next(
        widget for widget in page_q1.selectbox if widget.label == "Votre liaison"
    )
    choix.set_value("PARIS → LYON").run()
    assert not page_q1.exception
    tableau = next(
        table.value
        for table in page_q1.dataframe
        if "Mois" in table.value.columns
        and "Fiabilité prévue (%)" in table.value.columns
    )
    assert tableau["Fiabilité prévue (%)"].tolist() == [90, 90, 90]
    cartes = [
        metric
        for metric in page_q1.metric
        if metric.label in ("01/2025", "02/2025", "03/2025")
    ]
    assert len(cartes) == 3
    assert [carte.value for carte in cartes] == [fmt_pct(0.9)] * 3
    assert all(carte.delta == "+0.0 pt" for carte in cartes)
    assert not page_q1.number_input
    assert len(page_q1.selectbox) == 1
    assert any(
        volet.label == "Comprendre la méthode de prévision"
        for volet in page_q1.expander
    )


@pytest.mark.parametrize("page_q1", [True], indirect=True)
def test_prevision_signale_un_modele_moins_bon_que_la_reference(page_q1, monkeypatch):
    def prevision_moins_bonne(mensuel, liaison):
        return replace(
            prevoir_fiabilite(mensuel, liaison), mae_test=5.0, mae_reference=2.0
        )

    monkeypatch.setattr(
        "railinsight.analysis.prevision_fiabilite.prevoir_fiabilite",
        prevision_moins_bonne,
    )
    page_q1.run()
    ouvrir_onglet(page_q1, "Prévision à 3 mois")

    assert not page_q1.exception
    assert not page_q1.error
    assert any("fait moins bien" in alerte.value for alerte in page_q1.warning)


@pytest.mark.parametrize("page_q1", [True], indirect=True)
def test_prevision_fenetres_historique_et_reference(page_q1):
    page_q1.run()
    ouvrir_onglet(page_q1, "Prévision à 3 mois")
    avant = json.loads(page_q1.get("plotly_chart")[0].proto.spec)["data"][1]
    for periode, nombre in [("12 mois", 12), ("Tout", 48), ("24 mois", 24)]:
        page_q1.segmented_control[0].set_value(periode).run()
        figure = json.loads(page_q1.get("plotly_chart")[0].proto.spec)
        assert len(figure["data"][0]["x"]) == nombre
        assert len(figure["data"][1]["x"]) == 3
        assert figure["data"][1] == avant
    page_q1.toggle[0].set_value(False).run()
    figure = json.loads(page_q1.get("plotly_chart")[0].proto.spec)
    assert figure["data"][2]["visible"] is False
    assert len(figure["data"][1]["x"]) == 3
    assert figure["data"][1] == avant


def test_la_prevision_ne_se_calcule_pas_dans_un_onglet_masque(page_q1, monkeypatch):
    def interdit(*args):
        pytest.fail("La prévision ne doit pas être calculée dans un autre onglet.")

    monkeypatch.setattr(
        "railinsight.analysis.prevision_fiabilite.prevoir_fiabilite", interdit
    )
    page_q1.run()
    ouvrir_onglet(page_q1, "À durée égale")
    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("plotly_chart")) == 1


@pytest.mark.parametrize("page_q1", [True], indirect=True)
def test_liaison_conservee_entre_evolution_et_prevision(page_q1):
    page_q1.run()
    page_q1.selectbox[0].set_value("PARIS → LYON").run()
    ouvrir_onglet(page_q1, "Évolution et tendances")
    assert page_q1.multiselect[0].value == ["PARIS → LYON"]
    assert not page_q1.number_input
    for periode, nombre in [("12 mois", 12), ("24 mois", 24), ("Tout", 72)]:
        page_q1.segmented_control[0].set_value(periode).run()
        figure = json.loads(page_q1.get("plotly_chart")[0].proto.spec)
        assert len(figure["data"][0]["x"]) == nombre
    ouvrir_onglet(page_q1, "Prévision à 3 mois")
    assert page_q1.selectbox[0].value == "PARIS → LYON"
    assert len(page_q1.selectbox) == 1
    assert not page_q1.exception


def test_changer_liaison_met_a_jour_la_comparaison_sans_avertissement(page_q1):
    page_q1.run()
    ouvrir_onglet(page_q1, "Évolution et tendances")
    page_q1.selectbox[0].set_value("PARIS → LYON").run()
    assert page_q1.multiselect[0].value == ["PARIS → LYON"]
    assert not page_q1.exception
    assert not page_q1.warning
    assert any(
        metric.label == "Fiabilité observée" and metric.value == fmt_pct(0.85)
        for metric in page_q1.metric
    )
