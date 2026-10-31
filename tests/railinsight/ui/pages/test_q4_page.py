"""Tests de la page Q4 : graphique, filtres et erreurs visibles."""

import json
import runpy
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.analysis.score_fiabilite import ParametresScore
from railinsight.backend import fiabilite
from railinsight.utils.formatting import fmt_number

PAGE = (
    Path(__file__).parents[4]
    / "src"
    / "railinsight"
    / "ui"
    / "pages"
    / "q4_score_fiabilite.py"
)


@pytest.fixture
def page_q4(monkeypatch, donnees_fiabilite):
    """Affiche la page avec des données locales contrôlées."""
    st.cache_data.clear()
    monkeypatch.setattr(fiabilite, "charger_donnees", lambda: donnees_fiabilite)
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def test_page_affiche_reseau_classements_et_match(page_q4):
    page_q4.run()
    assert not page_q4.exception
    assert not page_q4.error
    assert not page_q4.warning
    assert page_q4.title[0].value == "Q4: score de fiabilité"
    assert any(texte.value == "Analyse : Meryem" for texte in page_q4.caption)
    assert len(page_q4.get("plotly_chart")) == 3
    assert [onglet.label for onglet in page_q4.tabs] == [
        "Le réseau",
        "Le classement",
        "Le match des trajets",
    ]
    assert len(page_q4.select_slider) == 2
    assert len(page_q4.selectbox) == 2
    assert len(page_q4.metric) == 7
    assert not page_q4.toggle[0].value
    assert len(page_q4.multiselect) == 1
    assert any(
        volet.label == "Code source simplifié" and not volet.proto.expanded
        for volet in page_q4.expander
    )


@pytest.mark.parametrize(
    "categories",
    [["Très fiable"], ["Fiable"], ["Très fiable", "Fiable"]],
)
def test_filtre_categories_ne_change_que_le_reseau(page_q4, categories):
    page_q4.run()
    classements = [
        graphique.proto.spec for graphique in page_q4.get("plotly_chart")[1:]
    ]
    mesures = [mesure.value for mesure in page_q4.metric]
    page_q4.multiselect[0].set_value(categories).run()
    assert not page_q4.error
    assert not page_q4.exception
    figure = json.loads(page_q4.get("plotly_chart")[0].proto.spec)
    assert {trace["name"] for trace in figure["data"][:-1] if "name" in trace} == set(
        categories
    )
    assert [
        graphique.proto.spec for graphique in page_q4.get("plotly_chart")[1:]
    ] == classements
    assert [mesure.value for mesure in page_q4.metric] == mesures


@pytest.mark.parametrize(
    "categories,message",
    [([], "Choisissez au moins une catégorie"), (["À risque"], "Aucune liaison")],
)
def test_filtre_vide_ou_sans_resultat(page_q4, categories, message):
    page_q4.run()
    page_q4.multiselect[0].set_value(categories).run()
    assert not page_q4.exception
    assert not page_q4.error
    assert any(message in info.value for info in page_q4.info)
    assert len(page_q4.get("plotly_chart")) == 2
    assert page_q4.code[0].value
    page_q4.multiselect[0].set_value(["Très fiable", "Fiable"]).run()
    assert len(page_q4.get("plotly_chart")) == 3
    assert not page_q4.error


def test_filtre_rouge_et_bleu(page_q4, donnees_fiabilite):
    donnees_fiabilite["annules"] = donnees_fiabilite["prevus"] * 0.1
    donnees_fiabilite["retard_moyen_arrivee"] = 20
    page_q4.run()
    page_q4.multiselect[0].set_value(["À risque"]).run()
    figure = json.loads(page_q4.get("plotly_chart")[0].proto.spec)
    assert figure["data"][0]["line"]["color"] == "#b2182b"
    assert figure["data"][0]["name"] == "À risque"
    page_q4.multiselect[0].set_value(["Fiable"]).run()
    assert any("Aucune liaison" in info.value for info in page_q4.info)
    assert not page_q4.error


def test_filtre_conserve_l_etat_entre_periodes(page_q4):
    page_q4.run()
    page_q4.multiselect[0].set_value(["Très fiable"]).run()
    page_q4.select_slider[0].set_value(("2024-02", "2024-02")).run()
    assert page_q4.multiselect[0].value == ["Très fiable"]
    assert not page_q4.error
    assert len(page_q4.get("plotly_chart")) == 3


def test_code_simplifie_executable(page_q4, tmp_path, monkeypatch):
    page_q4.run()
    source = tmp_path / "exemple_reseau.py"
    source.write_text(page_q4.code[0].value, encoding="utf-8")
    figures = []
    monkeypatch.setattr(
        st, "plotly_chart", lambda figure, **kwargs: figures.append(figure)
    )
    table = fiabilite.charger_table_score()
    notes = fiabilite.analyser_fiabilite(table, "2024-01", "2024-02")
    runpy.run_path(
        str(source),
        init_globals={"table": table, "liaisons": notes, "categories": ["Fiable"]},
    )
    assert len(figures) == 1
    assert figures[0].data[0].name == "Fiable"
    assert len(figures[0].data[-1].x) == 2


def test_periode_avec_une_seule_liaison(page_q4):
    page_q4.run()
    figure = json.loads(page_q4.get("plotly_chart")[0].proto.spec)
    assert len(figure["data"][-1]["x"]) == 3
    page_q4.select_slider[0].set_value(("2024-02", "2024-02")).run()
    assert not page_q4.error
    assert not page_q4.exception
    figure = json.loads(page_q4.get("plotly_chart")[0].proto.spec)
    assert len(figure["data"][-1]["x"]) == 2
    assert "au moins deux liaisons" in page_q4.info[0].value
    assert not page_q4.selectbox
    assert len(page_q4.get("plotly_chart")) == 3


@pytest.mark.parametrize(
    "priorite,poids",
    [
        ("Éviter les annulations", 0.75),
        ("Éviter les retards", 0.25),
        ("Équilibrer les deux", 0.5),
    ],
)
def test_priorite_recalcule_les_notes(page_q4, priorite, poids):
    page_q4.run()
    page_q4.radio[0].set_value(priorite).run()
    attendu = fiabilite.analyser_fiabilite(
        fiabilite.charger_table_score(),
        "2024-01",
        "2024-02",
        ParametresScore(poids_annulations=poids),
    )
    assert not page_q4.error
    assert not page_q4.exception
    assert page_q4.metric[2].value == fmt_number(attendu.iloc[-1]["note"], 1)
    assert len(page_q4.get("plotly_chart")) == 3


def test_match_revele_les_notes_et_empeche_les_doublons(page_q4):
    page_q4.run()
    assert page_q4.selectbox[0].value != page_q4.selectbox[1].value
    page_q4.selectbox[0].set_value("LYON - PARIS").run()
    assert page_q4.selectbox[1].value == "BRUXELLES - PARIS"
    page_q4.toggle[0].set_value(True).run()
    assert not page_q4.error
    assert not page_q4.exception
    assert len(page_q4.metric) == 9
    assert len(page_q4.get("progress")) == 2
    assert "BRUXELLES - PARIS" in page_q4.success[0].value
    page_q4.toggle[0].set_value(False).run()
    assert not page_q4.success
    assert len(page_q4.metric) == 7


def test_match_egalite(page_q4, donnees_fiabilite):
    donnees_fiabilite["annules"] = 0
    donnees_fiabilite["retard_moyen_arrivee"] = 0
    page_q4.run()
    page_q4.toggle[0].set_value(True).run()
    assert not page_q4.error
    assert "Égalité" in page_q4.info[0].value
    assert not page_q4.success


def test_taille_classements(page_q4, donnees_fiabilite):
    lignes = donnees_fiabilite.iloc[[0]].copy()
    for i in range(20):
        donnees_fiabilite.loc[len(donnees_fiabilite)] = lignes.iloc[0]
        donnees_fiabilite.loc[len(donnees_fiabilite) - 1, "gare_arrivee"] = f"GARE {i}"
    page_q4.run()
    for nombre in (10, 5, 15):
        page_q4.select_slider[1].set_value(nombre).run()
        assert not page_q4.error
        for graphique in page_q4.get("plotly_chart")[1:]:
            figure = json.loads(graphique.proto.spec)
            assert sum(len(trace["y"]) for trace in figure["data"]) == nombre


def test_absence_de_liaison_affiche_un_message(page_q4, donnees_fiabilite):
    donnees_fiabilite["prevus"] = 1
    donnees_fiabilite["annules"] = 0
    page_q4.run()
    assert not page_q4.exception
    assert not page_q4.error
    assert "Élargissez la période" in page_q4.warning[0].value
    assert not page_q4.get("plotly_chart")


def test_erreur_inattendue_journalisee(page_q4, monkeypatch, caplog):
    def echouer():
        raise RuntimeError("Erreur de test Q4")

    monkeypatch.setattr(fiabilite, "charger_donnees", echouer)
    page_q4.run()
    assert not page_q4.exception
    assert page_q4.error[0].value == (
        "Une erreur inattendue s'est produite. L’équipe technique a été notifiée."
    )
    assert "Erreur de test Q4" in caplog.text
